# ----------------------------------------------------------------------
# db.py - Connects our backend to the MongoDB database
# ----------------------------------------------------------------------

from pymongo import MongoClient

from app.config import mongo_database_name, mongo_uri


# Create one MongoDB client. A client is the object Python uses to talk
# to the MongoDB container.
mongo_client = MongoClient(mongo_uri)

# Select the database named "simpledrive" from MongoDB.
database = mongo_client[mongo_database_name]


def check_mongodb_connection():
    """Ask MongoDB a tiny question to confirm it is available."""
    # "ping" is a small built-in check. If MongoDB replies, connection is fine.
    mongo_client.admin.command("ping")
