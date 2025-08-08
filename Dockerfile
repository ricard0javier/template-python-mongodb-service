# Use Python slim image
FROM python:3.11-slim

WORKDIR /app

# Create a non-root user
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file first to leverage Docker cache
COPY requirements.txt ./

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY src/ ./src/

# Set ownership to non-root user
RUN chown -R appuser:appuser /app 

# Switch to non-root user
USER appuser

# Expose port (adjust if your app uses a different port)
EXPOSE 8000

# Run the Python application
CMD ["python", "-m", "src.main"] 