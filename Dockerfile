# Use lightweight Python 3.12 image
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install system dependencies needed for compiling ML/Math libraries
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first to leverage Docker cache
COPY requirements-merged.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements-merged.txt

# Copy the rest of the application
COPY . .

# Expose the FastAPI port
EXPOSE 8000

# Command to run the application in API mode
CMD ["python", "main.py", "--mode", "api"]
