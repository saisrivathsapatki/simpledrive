# ----------------------------------------------------------------------
# main.py — Starting point (entry door) of our Python FastAPI backend
# ----------------------------------------------------------------------

from fastapi import FastAPI

# Create the FastAPI app instance (this is our main backend brain object)
app = FastAPI(
    title="SimpleDrive Backend API",
    description="Small and simple Google Drive clone backend",
    version="1.0.0"
)

# ----------------------------------------------------------------------
# Health Check Endpoint
# ----------------------------------------------------------------------
# What is an endpoint? It is a specific web address your backend listens to.
# What is GET? An HTTP method used when you want to fetch / read data.
# When someone visits "/api/health", this function runs and replies.
@app.get("/api/health")
def health_check():
    """
    Simple check to tell whether our FastAPI backend server is alive and kicking.
    """
    # Returns a simple JSON response: {"status": "ok"}
    # What is JSON? A simple key-value text format (like a Python dictionary).
    return {"status": "ok"}
