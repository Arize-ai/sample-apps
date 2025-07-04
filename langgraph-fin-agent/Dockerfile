FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire project structure
COPY . .

# Set environment variables
ENV PYTHONPATH=/app
ENV PORT=8080

# Expose the port
EXPOSE 8080

# Print directory structure for debugging
RUN ls -la /app && \
    echo "Python path: $PYTHONPATH"

# Run the FastAPI app with uvicorn
# Cloud Run expects the app to listen on 0.0.0.0:$PORT
CMD exec uvicorn backend.main:app --host 0.0.0.0 --port $PORT --workers 1 --log-level info 