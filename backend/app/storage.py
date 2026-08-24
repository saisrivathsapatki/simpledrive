# ----------------------------------------------------------------------
# storage.py - Connects our backend to MinIO file storage
# ----------------------------------------------------------------------

from minio import Minio

from app.config import (
    minio_bucket_name,
    minio_endpoint,
    minio_public_endpoint,
    minio_root_password,
    minio_root_user,
)


# Create one MinIO client. This object lets Python store and read files.
# secure=False means we are using normal http on our local laptop, not https.
minio_client = Minio(
    minio_endpoint,
    access_key=minio_root_user,
    secret_key=minio_root_password,
    secure=False,
)

# This client makes download links with localhost, which the browser can reach.
minio_public_client = Minio(
    minio_public_endpoint,
    access_key=minio_root_user,
    secret_key=minio_root_password,
    secure=False,
    # MinIO uses this default region, so no localhost connection is needed here.
    region="us-east-1",
)


def create_bucket_if_needed():
    """Create our file bucket once if MinIO does not have it already."""
    # First check whether the bucket already exists.
    bucket_exists = minio_client.bucket_exists(minio_bucket_name)

    # Make the bucket only when it is missing.
    if not bucket_exists:
        minio_client.make_bucket(minio_bucket_name)


def check_minio_connection():
    """Ask MinIO about our bucket to confirm it is available."""
    # This request proves that MinIO is alive and that our login details work.
    minio_client.bucket_exists(minio_bucket_name)
