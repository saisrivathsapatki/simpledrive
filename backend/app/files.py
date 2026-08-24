# ----------------------------------------------------------------------
# files.py - Upload files and show the logged-in user's file list
# ----------------------------------------------------------------------

from datetime import datetime, timedelta
import uuid

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from app.auth import get_current_user
from app.config import minio_bucket_name
from app.db import database
from app.storage import minio_client, minio_public_client


# Keep all file-related endpoints under the /api/files address.
router = APIRouter(prefix="/api/files")

# Each user can use at most 200 MB of storage.
storage_limit_bytes = 200 * 1024 * 1024


def get_file_size(uploaded_file: UploadFile):
    """Measure an uploaded file without reading all its content into memory."""
    # Move to the end to find the file size in bytes.
    uploaded_file.file.seek(0, 2)
    file_size = uploaded_file.file.tell()

    # Return to the beginning so MinIO can upload the whole file.
    uploaded_file.file.seek(0)
    return file_size


def get_owned_file(file_id: str, current_user: dict):
    """Find one file only when it belongs to the logged-in user."""
    # A bad-looking MongoDB id should look the same as a missing file.
    try:
        mongo_file_id = ObjectId(file_id)
    except InvalidId:
        raise HTTPException(status_code=404, detail="File not found")

    # Owner id is part of this query, so another user's file stays invisible.
    file_document = database.files.find_one({
        "_id": mongo_file_id,
        "owner_id": current_user["_id"],
    })

    if file_document is None:
        raise HTTPException(status_code=404, detail="File not found")

    return file_document


@router.post("/upload")
def upload_file(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
):
    """Upload one file for the logged-in user."""
    # Stop an empty file because it is not useful in our small drive.
    file_size = get_file_size(file)
    if file_size == 0:
        raise HTTPException(status_code=400, detail="Please choose a non-empty file")

    # Check storage before uploading so a user cannot cross the 200 MB limit.
    total_after_upload = current_user["storage_used"] + file_size
    if total_after_upload > storage_limit_bytes:
        raise HTTPException(status_code=400, detail="This upload would cross your 200 MB storage limit")

    # Use a random object key, not the file name, to avoid name clashes.
    object_key = str(current_user["_id"]) + "/" + str(uuid.uuid4())

    # Use a safe general type when the browser does not send a file type.
    content_type = file.content_type or "application/octet-stream"

    # Store the actual file bytes inside the SimpleDrive MinIO bucket.
    minio_client.put_object(
        minio_bucket_name,
        object_key,
        file.file,
        file_size,
        content_type=content_type,
    )

    # Store the file details inside MongoDB after MinIO accepts the bytes.
    file_result = database.files.insert_one({
        "owner_id": current_user["_id"],
        "name": file.filename,
        "size": file_size,
        "content_type": content_type,
        "object_key": object_key,
        "created_at": datetime.utcnow(),
    })

    # Increase only this user's saved storage total.
    database.users.update_one(
        {"_id": current_user["_id"]},
        {"$inc": {"storage_used": file_size}},
    )

    return {
        "message": "File uploaded successfully",
        "id": str(file_result.inserted_id),
        "name": file.filename,
        "size": file_size,
    }


@router.get("")
def list_my_files(current_user: dict = Depends(get_current_user)):
    """Return all files belonging to the logged-in user."""
    # Fetch only records whose owner id matches the current logged-in user.
    file_documents = database.files.find({"owner_id": current_user["_id"]})

    # Put newest uploads first so the most recent file appears at the top.
    file_documents = file_documents.sort("created_at", -1)

    # Build a clean list without exposing MinIO's private object key.
    files = []
    for file_document in file_documents:
        files.append({
            "id": str(file_document["_id"]),
            "name": file_document["name"],
            "size": file_document["size"],
            "content_type": file_document["content_type"],
            "created_at": file_document["created_at"],
        })

    return {"files": files}


@router.get("/{file_id}/download")
def download_file(file_id: str, current_user: dict = Depends(get_current_user)):
    """Create a five-minute download link for one owned file."""
    # Check ownership before creating any link to the real file.
    file_document = get_owned_file(file_id, current_user)

    # Make a temporary MinIO link which expires after five minutes.
    download_url = minio_public_client.presigned_get_object(
        minio_bucket_name,
        file_document["object_key"],
        expires=timedelta(minutes=5),
    )

    return {"download_url": download_url}


@router.patch("/{file_id}")
def rename_file(
    file_id: str,
    payload: dict,
    current_user: dict = Depends(get_current_user),
):
    """Change the displayed name of one owned file."""
    # Read the requested new name and remove accidental outer spaces.
    new_name = payload.get("name", "").strip()
    if new_name == "":
        raise HTTPException(status_code=400, detail="Please provide a file name")

    # Check ownership before changing the MongoDB record.
    get_owned_file(file_id, current_user)

    # Update only the visible name; the safe MinIO object key stays unchanged.
    database.files.update_one(
        {"_id": ObjectId(file_id)},
        {"$set": {"name": new_name}},
    )

    return {"message": "File renamed successfully", "name": new_name}


@router.delete("/{file_id}")
def delete_file(file_id: str, current_user: dict = Depends(get_current_user)):
    """Remove one owned file from MinIO, MongoDB, and storage total."""
    # Check ownership and keep the details needed for all three delete steps.
    file_document = get_owned_file(file_id, current_user)

    # First delete the actual file bytes from MinIO.
    minio_client.remove_object(minio_bucket_name, file_document["object_key"])

    # Next delete the file's details from MongoDB.
    database.files.delete_one({"_id": file_document["_id"]})

    # Finally reduce the owner's saved storage total by this file's size.
    database.users.update_one(
        {"_id": current_user["_id"]},
        {"$inc": {"storage_used": -file_document["size"]}},
    )

    return {"message": "File deleted successfully"}
