# ----------------------------------------------------------------------
# Recipe for our Python Backend Box (Container)
# ----------------------------------------------------------------------

# Step 1: Start from official lightweight Python 3.11 base image
FROM python:3.11-slim

# Step 2: Set the working directory inside the container to /app
WORKDIR /app

# Step 3: Copy the list of required libraries from laptop to container
COPY requirements.txt .

# Step 4: Install all the Python libraries listed in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Step 5: Copy all backend code from laptop into the container /app folder
COPY . .

# Step 6: Command to run when the container starts
# --host 0.0.0.0 allows connections from outside the container
# --port 8000 specifies which port to listen on
# --reload automatically restarts server when you make changes to Python files
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
