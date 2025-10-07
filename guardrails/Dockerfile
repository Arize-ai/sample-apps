FROM python:3.11-slim as builder

# Accept a build arg for the Guardrails token
ARG GUARDRAILS_TOKEN
ENV GUARDRAILS_TOKEN=$GUARDRAILS_TOKEN

# Install build dependencies
RUN apt-get update && apt-get install -y \
    git \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Create and activate virtual environment
RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Upgrade pip and install setuptools first
RUN pip install --upgrade pip setuptools wheel

# Copy requirements and install Python dependencies
COPY requirements*.txt /tmp/
RUN pip install --no-cache-dir -r /tmp/requirements.txt

# Set the directory for nltk data
ENV NLTK_DATA=/opt/nltk_data
RUN mkdir -p /opt/nltk_data

# Pre-download NLTK data at build time
RUN python -c "import nltk; nltk.download('punkt', download_dir='/opt/nltk_data'); nltk.download('punkt_tab', download_dir='/opt/nltk_data')"

# Configure Guardrails at build time (only if token is provided)
RUN if [ ! -z "$GUARDRAILS_TOKEN" ]; then \
        guardrails configure --enable-metrics --enable-remote-inferencing --token $GUARDRAILS_TOKEN; \
    else \
        guardrails configure --enable-metrics; \
    fi

# Install validators from the hub at build time
RUN guardrails hub install hub://tryolabs/restricttotopic && \
    guardrails hub install hub://arize-ai/dataset_embeddings_guardrails && \
    guardrails hub install hub://guardrails/detect_pii

# Production stage - smaller final image
FROM python:3.11-slim

# Install only runtime dependencies
RUN apt-get update && apt-get install -y \
    && rm -rf /var/lib/apt/lists/*

# Create app directory
WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
COPY --from=builder /opt/nltk_data /opt/nltk_data
COPY --from=builder /root/.guardrailsrc /root/.guardrailsrc

# Enable venv and set environment variables
ENV PATH="/opt/venv/bin:$PATH"
ENV NLTK_DATA=/opt/nltk_data
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Copy application code
COPY . .

# Expose port (for Cloud Run and similar services)
EXPOSE 8000

# For serverless functions, we'll use a more flexible startup
# This works for Google Cloud Run, AWS Lambda with custom runtime, Azure Container Instances
CMD uvicorn server:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1