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
ENV TRANSFORMERS_CACHE=/app/models
ENV HF_HOME=/app/models
ENV PYTHONPATH=/app
ENV PORT=8080

# Optional Arize configuration (can be overridden at runtime)
ENV ARIZE_SPACE_ID=""
ENV ARIZE_API_KEY=""
ENV ARIZE_MODEL_ID="mustang_manual_bot"

# Expose the port
EXPOSE 8080

# Print directory structure for debugging
RUN ls -la /app && \
    ls -la /app/backend && \
    echo "Python path: $PYTHONPATH"

# Run the FastAPI app with uvicorn
# Cloud Run expects the app to listen on 0.0.0.0:$PORT
CMD exec uvicorn backend.main:app --host 0.0.0.0 --port $PORT --workers 1 --log-level debug 