# ----------------------------------------------------------------------
# main.py — Starting point (entry door) of our Python FastAPI backend
# ----------------------------------------------------------------------

from fastapi import FastAPI

from app.auth import router as auth_router
from app.db import check_mongodb_connection
from app.files import router as files_router
from app.storage import check_minio_connection, create_bucket_if_needed

# Create the FastAPI app instance (this is our main backend brain object)
app = FastAPI(
    title="SimpleDrive Backend API",
    description="Small and simple Google Drive clone backend",
    version="1.0.0"
)

# Add all the sign-up and login endpoints from auth.py to this backend.
app.include_router(auth_router)

# Add all upload and file-list endpoints from files.py to this backend.
app.include_router(files_router)


@app.on_event("startup")
def set_up_file_bucket():
    """Create the MinIO bucket when the backend starts."""
    # Make sure the bucket exists before anybody tries to upload a file.
    create_bucket_if_needed()

# ----------------------------------------------------------------------
# Health Check Endpoint
# ----------------------------------------------------------------------
# What is an endpoint? It is a specific web address your backend listens to.
# What is GET? An HTTP method used when you want to fetch / read data.
# When someone visits "/api/health", this function runs and replies.
@app.get("/api/health")
def health_check():
    """
    Check whether the backend, MongoDB, and MinIO are all available.
    """
    # Ask MongoDB to reply to a small "ping" message.
    check_mongodb_connection()

    # Ask MinIO whether it can see our file bucket.
    check_minio_connection()

    # Return one JSON reply showing that all three parts are working.
    return {
        "backend": "ok",
        "mongodb": "ok",
        "minio": "ok",
    }
