# ----------------------------------------------------------------------
# auth.py - Sign-up, log-in, log-out, and current-user actions
# ----------------------------------------------------------------------

from datetime import datetime, timedelta
import secrets

import bcrypt
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.db import database


# A router keeps all login-related endpoints together in this one file.
router = APIRouter(prefix="/api/auth")

# This tells FastAPI that protected endpoints use the Bearer token format.
# It also gives the /docs page one clear Authorize button for the token.
token_scheme = HTTPBearer(auto_error=False)

# Allow only a few wrong password attempts before making somebody wait.
# MongoDB keeps this information, so it is not forgotten when the backend restarts.
MAX_FAILED_LOGIN_ATTEMPTS = 5
LOGIN_ATTEMPT_WINDOW_MINUTES = 15


def get_login_attempt_key(request: Request, email: str) -> str:
    """Make one safe key for failed attempts from this browser and email."""
    # Nginx sends the original browser address in X-Real-IP before it forwards /api.
    # Without this header, FastAPI would only see Nginx's own Docker address.
    client_host = "unknown"
    forwarded_client_host = request.headers.get("x-real-ip")
    if forwarded_client_host is not None:
        client_host = forwarded_client_host
    elif request.client is not None:
        # This fallback helps when we test directly through localhost:8000/docs.
        client_host = request.client.host

    # Keeping both values together stops one browser from endlessly guessing one account.
    return f"{client_host}:{email}"


def block_login_if_too_many_attempts(attempt_key: str):
    """Stop a login when its temporary failed-attempt limit is reached."""
    # Remove records whose 15-minute waiting window has already finished.
    database.login_attempts.delete_many({"expires_at": {"$lt": datetime.utcnow()}})

    # Look for the current browser-and-email attempt record.
    attempt_record = database.login_attempts.find_one({"attempt_key": attempt_key})

    # A record below the limit means this login may continue normally.
    if attempt_record is None or attempt_record["failed_count"] < MAX_FAILED_LOGIN_ATTEMPTS:
        return

    # Do not say whether the email exists; that information is private too.
    raise HTTPException(
        # 429 specifically means "too many requests".
        status_code=429,
        detail="Too many login attempts. Please try again after 15 minutes",
    )


def record_failed_login(attempt_key: str):
    """Add one failed password attempt to MongoDB."""
    # Set the same 15-minute expiry when this browser makes its first wrong attempt.
    database.login_attempts.update_one(
        {"attempt_key": attempt_key},
        {
            "$inc": {"failed_count": 1},
            "$setOnInsert": {
                "created_at": datetime.utcnow(),
                "expires_at": datetime.utcnow() + timedelta(minutes=LOGIN_ATTEMPT_WINDOW_MINUTES),
            },
        },
        upsert=True,
    )


def clear_failed_logins(attempt_key: str):
    """Forget failed attempts once the person logs in correctly."""
    # A correct password proves this person should not stay locked out.
    database.login_attempts.delete_one({"attempt_key": attempt_key})


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(token_scheme),
):
    """Find the logged-in user from the token sent in the request header."""
    # A header is extra information sent along with a browser request.
    # FastAPI reads: Authorization: Bearer long-random-token for us.
    if credentials is None:
        raise HTTPException(status_code=401, detail="Please log in first")

    # Keep only the actual token after FastAPI checks the Bearer format.
    token = credentials.credentials

    # Find this token inside the sessions collection.
    session = database.sessions.find_one({"token": token})

    # Reject a missing session or a session whose seven days have finished.
    if session is None or session["expires_at"] < datetime.utcnow():
        raise HTTPException(status_code=401, detail="Your login session has expired")

    # Find the user who owns this session.
    current_user = database.users.find_one({"_id": session["user_id"]})

    # This should not normally happen, but it keeps the check safe.
    if current_user is None:
        raise HTTPException(status_code=401, detail="Please log in first")

    return current_user


@router.post("/signup")
def sign_up(payload: dict):
    """Create one new SimpleDrive account."""
    # Read the email and password sent by the user.
    email = payload.get("email", "").strip().lower()
    password = payload.get("password", "")

    # Stop early when either required value is missing.
    if email == "" or password == "":
        raise HTTPException(status_code=400, detail="Email and password are required")

    # Use a simple minimum length rule for the learning project.
    if len(password) < 8:
        raise HTTPException(status_code=400, detail="Password must have at least 8 characters")

    # Do not allow two accounts with the same email address.
    existing_user = database.users.find_one({"email": email})
    if existing_user is not None:
        raise HTTPException(status_code=400, detail="An account with this email already exists")

    # Turn the normal password into a one-way hash before saving it.
    password_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())

    # Store only the needed account details in MongoDB.
    database.users.insert_one({
        "email": email,
        "password_hash": password_hash.decode("utf-8"),
        "storage_used": 0,
        "created_at": datetime.utcnow(),
    })

    return {"message": "Account created successfully"}


@router.post("/login")
def log_in(payload: dict, request: Request):
    """Check a password and create a seven-day login session."""
    # Read the email and password the person typed on the login screen.
    email = payload.get("email", "").strip().lower()
    password = payload.get("password", "")

    # Make the key before checking the password, so unknown emails are protected too.
    login_attempt_key = get_login_attempt_key(request, email)

    # Reject this request early if there have already been too many wrong tries.
    block_login_if_too_many_attempts(login_attempt_key)

    # Find the matching user account.
    user = database.users.find_one({"email": email})

    # Reject a missing user without telling strangers which emails exist.
    if user is None:
        # Count this too, otherwise somebody can test unlimited email-password pairs.
        record_failed_login(login_attempt_key)
        raise HTTPException(status_code=401, detail="Email or password is incorrect")

    # Compare the typed password with the saved one-way password hash.
    password_matches = bcrypt.checkpw(
        password.encode("utf-8"),
        user["password_hash"].encode("utf-8"),
    )

    if not password_matches:
        # Remember the wrong attempt before sending the same safe error message.
        record_failed_login(login_attempt_key)
        raise HTTPException(status_code=401, detail="Email or password is incorrect")

    # A correct password clears previous mistakes from this browser and email.
    clear_failed_logins(login_attempt_key)

    # Make a long random token which works like a temporary entry pass.
    token = secrets.token_urlsafe(32)

    # Store the token and its expiry time in MongoDB.
    database.sessions.insert_one({
        "token": token,
        "user_id": user["_id"],
        "created_at": datetime.utcnow(),
        "expires_at": datetime.utcnow() + timedelta(days=7),
    })

    return {"token": token}


@router.post("/logout")
def log_out(credentials: HTTPAuthorizationCredentials = Depends(token_scheme)):
    """Delete the current login session so its token stops working."""
    # Reuse the same token check before allowing log-out.
    get_current_user(credentials)

    # Remove only this one token from the sessions collection.
    token = credentials.credentials
    database.sessions.delete_one({"token": token})

    return {"message": "Logged out successfully"}


@router.get("/me")
def get_my_details(current_user: dict = Depends(get_current_user)):
    """Return the email and storage use of the logged-in user."""
    # FastAPI has already checked the token and found the current user.

    # Do not return the password hash or any private database details.
    return {
        "email": current_user["email"],
        "storage_used": current_user["storage_used"],
    }
