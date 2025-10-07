# Dynamic Environment Variables Guide

This guide explains how to use dynamic environment variables with the LangGraph Finance Agent Cloud Run deployment.

## Overview

The LangGraph Finance Agent now supports dynamic environment variable configuration at runtime. This allows you to send different API keys and configuration values with each request, while maintaining fallback to default environment values.

## Supported Environment Variables

The following environment variables can be dynamically overridden:

- `ARIZE_SPACE_ID`
- `ARIZE_MODEL_ID`
- `ARIZE_API_KEY`
- `ARIZE_PROJECT_NAME`
- `OPENAI_API_KEY`
- `FMP_API_KEY`

## How It Works

1. **Default Behavior**: If no environment overrides are provided, the application uses values from the default environment configuration (configured during deployment).

2. **Dynamic Override**: You can send environment variables with each chat request, and the application will use those values for that specific request.

3. **Session Caching**: To improve performance, the application caches initialized LangGraph components for each unique environment configuration for 30 minutes.

## API Usage

### Request Format for Chat Endpoint

Send a POST request to `/api/chat` with the following JSON structure:

```json
{
  "message": "Your financial question here",
  "session_id": "optional-session-id",
  "env_overrides": {
    "ARIZE_SPACE_ID": "your-space-id",
    "ARIZE_MODEL_ID": "your-model-id",
    "ARIZE_API_KEY": "your-api-key",
    "ARIZE_PROJECT_NAME": "your-project-name",
    "OPENAI_API_KEY": "your-openai-key",
    "FMP_API_KEY": "your-fmp-key"
  }
}
```

### Request Format for Finance Query Endpoint

Send a POST request to `/api/finance-query` with the following JSON structure:

```json
{
  "query": "Your detailed financial analysis query",
  "thread_id": "optional-thread-id",
  "env_overrides": {
    "ARIZE_SPACE_ID": "your-space-id",
    "ARIZE_MODEL_ID": "your-model-id",
    "ARIZE_API_KEY": "your-api-key",
    "OPENAI_API_KEY": "your-openai-key"
  }
}
```

### Example cURL Request

```bash
curl -X POST https://your-cloud-run-url/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What is Apple's current stock price and market cap?",
    "env_overrides": {
      "ARIZE_SPACE_ID": "custom-space-id",
      "ARIZE_MODEL_ID": "custom-model-id",
      "ARIZE_API_KEY": "custom-api-key",
      "OPENAI_API_KEY": "custom-openai-key",
      "FMP_API_KEY": "custom-fmp-key"
    }
  }'
```

### Example Python Request

```python
import requests

url = "https://your-cloud-run-url/api/chat"
data = {
    "message": "Analyze Tesla's quarterly performance trends",
    "env_overrides": {
        "ARIZE_SPACE_ID": "custom-space-id",
        "ARIZE_MODEL_ID": "custom-model-id",
        "ARIZE_API_KEY": "custom-api-key",
        "OPENAI_API_KEY": "custom-openai-key",
        "FMP_API_KEY": "custom-fmp-key"
    }
}

response = requests.post(url, json=data)
print(response.json())
```

## Security Considerations

1. **HTTPS Only**: Always use HTTPS when sending API keys to protect them in transit.

2. **Validation**: Only the allowed environment variables listed above can be overridden. Any other variables in `env_overrides` will be ignored.

3. **Temporary Usage**: Environment overrides are only used for the specific request and do not persist.

4. **Access Control**: Implement appropriate authentication and authorization on your Cloud Run service to control who can send requests with custom environment variables.

## Performance Notes

- The first request with a new environment configuration will take longer as it initializes the LangGraph components.
- Subsequent requests with the same configuration will use cached components (cache TTL: 30 minutes).
- Different environment configurations are isolated from each other.

## Fallback Behavior

If any of the following conditions are met, the application will use the default values from the deployment environment:

- No `env_overrides` field is provided in the request
- The `env_overrides` field is empty
- A specific environment variable is not included in `env_overrides`
- A provided value is empty or whitespace-only

## Deployment Configuration

When deploying to Cloud Run, ensure:

1. Default values for all required environment variables are configured in the deployment.
2. CORS is properly configured if accessing from a web frontend.

## Monitoring and Debugging

### Status Endpoint

Check the service status:
```bash
curl https://your-cloud-run-url/api/status
```

Returns information about:
- Service readiness
- LangGraph app availability
- Cache statistics

### Debug Config Endpoint

Check current configuration:
```bash
curl https://your-cloud-run-url/debug/config
```

Returns information about:
- Which environment variables are configured
- Cache status and TTL
- Service configuration

### Logs

The application logs include information about:
- When dynamic environment variables are used
- Cache hits and misses
- Initialization events
- Environment variable overrides

Monitor your Cloud Run logs to track usage and performance of dynamic configurations.

## Example Use Cases

### Multi-tenant Finance Platform
```python
# Different customers with different Arize configurations
customer_a_request = {
    "message": "What's Apple's P/E ratio?",
    "env_overrides": {
        "ARIZE_SPACE_ID": "customer-a-space",
        "ARIZE_MODEL_ID": "customer-a-model"
    }
}

customer_b_request = {
    "message": "Analyze Microsoft's quarterly trends",
    "env_overrides": {
        "ARIZE_SPACE_ID": "customer-b-space", 
        "ARIZE_MODEL_ID": "customer-b-model"
    }
}
```

### Development vs Production
```python
# Use different API keys for development
dev_request = {
    "message": "Test financial query",
    "env_overrides": {
        "OPENAI_API_KEY": "dev-openai-key",
        "FMP_API_KEY": "dev-fmp-key",
        "ARIZE_MODEL_ID": "dev-model"
    }
}
```

### A/B Testing Different Models
```python
# Test different model configurations
model_a_request = {
    "message": "Analyze stock performance",
    "env_overrides": {
        "ARIZE_MODEL_ID": "model-variant-a"
    }
}

model_b_request = {
    "message": "Analyze stock performance", 
    "env_overrides": {
        "ARIZE_MODEL_ID": "model-variant-b"
    }
}
``` 