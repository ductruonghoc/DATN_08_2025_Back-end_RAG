# Use an official Python runtime as the base image
FROM python:3.10-slim

# Set the working directory in the container
WORKDIR /app

# Install system dependencies required for gRPC and PDF processing
RUN apt-get update && apt-get install -y \
    build-essential \
    python3-dev \
    poppler-utils \
    libpoppler-cpp-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first to leverage Docker cache
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire application
COPY . .

# Expose the gRPC server port
EXPOSE 50051

# Command to run the gRPC server
CMD ["python", "pdf-grpc-server.py"]