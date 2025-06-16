# LangGraph Finance Agent Backend

A FastAPI backend service that provides financial analysis capabilities using LangGraph agents. This service can be deployed on Google Cloud Run and provides REST API endpoints for financial queries and analysis.

## Features

- **Financial Analysis**: Ask questions about stocks, companies, and financial data
- **LangGraph Integration**: Powered by advanced agent workflows
- **REST API**: Clean HTTP endpoints for integration
- **Cloud Ready**: Deployable on Google Cloud Run
- **Scalable**: Containerized with Docker

## API Endpoints

### Chat Endpoint
- **POST** `/api/chat`
  - Simple chat interface for financial questions
  - Request: `{"message": "What is Apple's current stock price?", "session_id": "optional", "env_overrides": {"OPENAI_API_KEY": "custom-key"}}`
  - Response: `{"response": "...", "session_id": "..."}`

### Finance Query Endpoint
- **POST** `/api/finance-query`
  - Detailed financial analysis queries
  - Request: `{"query": "Analyze Tesla's quarterly performance", "thread_id": "optional", "env_overrides": {"ARIZE_MODEL_ID": "custom-model"}}`
  - Response: `{"result": {...}, "thread_id": "..."}`

### Health Check
- **GET** `/health`
  - Service health status

### Status
- **GET** `/api/status`
  - Detailed service status and readiness

## Local Development

### Prerequisites
- Python 3.11+
- Poetry (for dependency management)

### Setup
1. Clone the repository
2. Install dependencies:
   ```bash
   poetry install
   ```

3. Set up environment variables:
   ```bash
   cp .env.example .env
   # Edit .env with your API keys
   ```

4. Run the development server:
   ```bash
   uvicorn backend.main:app --reload --port 8080
   ```

5. Visit `http://localhost:8080/docs` for API documentation

## Cloud Deployment (Google Cloud Run)

### Prerequisites
- Google Cloud SDK installed and configured
- Docker installed (for local testing)
- Active Google Cloud Project with billing enabled

### Deploy to Cloud Run

1. **Authenticate with Google Cloud:**
   ```bash
   gcloud auth login
   gcloud config set project YOUR_PROJECT_ID
   ```

2. **Enable required APIs:**
   ```bash
   gcloud services enable cloudbuild.googleapis.com
   gcloud services enable run.googleapis.com
   ```

3. **Deploy using the script:**
   ```bash
   ./scripts/deploy.sh
   ```

   Or manually:
   ```bash
   # Build the container
   gcloud builds submit --tag gcr.io/YOUR_PROJECT_ID/langgraph-fin-agent

   # Deploy to Cloud Run
   gcloud run deploy langgraph-fin-agent \
     --image gcr.io/YOUR_PROJECT_ID/langgraph-fin-agent \
     --platform managed \
     --region us-central1 \
     --allow-unauthenticated \
     --memory 2Gi \
     --timeout 600
   ```

### Environment Variables

Set these environment variables in Cloud Run or your local environment:

- `OPENAI_API_KEY`: Your OpenAI API key
- `ARIZE_API_KEY`: Arize Phoenix API key (optional)
- `ARIZE_SPACE_ID`: Arize Phoenix Space ID (optional)
- `ARIZE_PROJECT_NAME`: Project name for tracing (optional)
- `CORS_ORIGINS`: Allowed CORS origins (comma-separated)
- `FMP_API_KEY`: Financial Modeling Prep API key (optional)

## Dynamic Environment Variables

The service supports runtime environment variable overrides for maximum flexibility. You can send different API keys and configuration values with each request. See the [Dynamic Environment Variables Guide](backend/deployment/DYNAMIC_ENV_GUIDE.md) for detailed information.

### Supported Dynamic Variables

- `ARIZE_SPACE_ID`
- `ARIZE_MODEL_ID` 
- `ARIZE_API_KEY`
- `ARIZE_PROJECT_NAME`
- `OPENAI_API_KEY`
- `FMP_API_KEY`

## Usage Examples

### Using curl

```bash
# Health check
curl https://YOUR_SERVICE_URL/health

# Chat request
curl -X POST https://YOUR_SERVICE_URL/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What is the current market cap of Microsoft?"}'

# Chat request with environment overrides
curl -X POST https://YOUR_SERVICE_URL/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What is the current market cap of Microsoft?",
    "env_overrides": {
      "ARIZE_MODEL_ID": "custom-model",
      "OPENAI_API_KEY": "custom-openai-key"
    }
  }'

# Finance query
curl -X POST https://YOUR_SERVICE_URL/api/finance-query \
  -H "Content-Type: application/json" \
  -d '{"query": "Analyze the quarterly performance of tech stocks"}'
```

### Using Python

```python
import requests

# Initialize the client
base_url = "https://YOUR_SERVICE_URL"

# Simple chat
response = requests.post(f"{base_url}/api/chat", json={
    "message": "What are the top performing stocks today?"
})
print(response.json())

# Detailed finance query
response = requests.post(f"{base_url}/api/finance-query", json={
    "query": "Compare Apple and Microsoft financial performance"
})
print(response.json())

# Chat with custom environment variables
response = requests.post(f"{base_url}/api/chat", json={
    "message": "What are the top performing stocks today?",
    "env_overrides": {
        "ARIZE_MODEL_ID": "custom-model",
        "OPENAI_API_KEY": "custom-openai-key"
    }
})
print(response.json())
```

## Architecture

- **FastAPI**: Web framework for the REST API
- **LangGraph**: Agent workflow orchestration
- **Uvicorn**: ASGI server for production
- **Docker**: Containerization for cloud deployment
- **Google Cloud Run**: Serverless container platform

## Monitoring and Observability

The service includes integration with Arize Phoenix for observability:
- Request tracing
- Performance monitoring  
- Error tracking
- Agent workflow visibility

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test locally
5. Submit a pull request

## License

[Add your license information here]