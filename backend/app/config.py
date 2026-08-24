# ----------------------------------------------------------------------
# config.py - Reads settings given to our backend from the .env file
# ----------------------------------------------------------------------

import os


# Read the MongoDB address from the environment variables.
# "mongo" is the name of our MongoDB container inside Docker.
mongo_uri = os.getenv("MONGO_URI")

# Read the database name where SimpleDrive will keep its details.
mongo_database_name = os.getenv("MONGO_DB_NAME")

# Read the MinIO server address from the environment variables.
minio_endpoint = os.getenv("MINIO_ENDPOINT")

# Read the MinIO address which the browser can reach from the laptop.
minio_public_endpoint = os.getenv("MINIO_PUBLIC_ENDPOINT")

# Read MinIO login details from the environment variables.
minio_root_user = os.getenv("MINIO_ROOT_USER")
minio_root_password = os.getenv("MINIO_ROOT_PASSWORD")

# Read the bucket name where the actual uploaded files will live.
minio_bucket_name = os.getenv("MINIO_BUCKET_NAME")
