# Dynamic Environment Variables Guide

This guide explains how to use dynamic environment variables with the Arize Chatbot Cloud Run deployment.

## Overview

The Arize Chatbot now supports dynamic environment variable configuration at runtime. This allows you to send different API keys and configuration values with each request, while maintaining fallback to Google Cloud Secret Manager values.

## Supported Environment Variables

The following environment variables can be dynamically overridden:

- `ARIZE_SPACE_ID`
- `ARIZE_MODEL_ID`
- `ARIZE_API_KEY`
- `OPENAI_API_KEY`

## How It Works

1. **Default Behavior**: If no environment overrides are provided, the application uses values from Google Cloud Secret Manager (configured during deployment).

2. **Dynamic Override**: You can send environment variables with each chat request, and the application will use those values for that specific request.

3. **Session Caching**: To improve performance, the application caches initialized components for each unique environment configuration for 30 minutes.

## API Usage

### Request Format

Send a POST request to `/api/chat` with the following JSON structure:

```json
{
  "message": "Your question here",
  "session_id": "optional-session-id",
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
    "message": "What is Arize?",
    "env_overrides": {
      "ARIZE_SPACE_ID": "custom-space-id",
      "ARIZE_MODEL_ID": "custom-model-id",
      "ARIZE_API_KEY": "custom-api-key",
      "OPENAI_API_KEY": "custom-openai-key"
    }
  }'
```

### Example Python Request

```python
import requests

url = "https://your-cloud-run-url/api/chat"
data = {
    "message": "How do I set up Arize monitoring?",
    "env_overrides": {
        "ARIZE_SPACE_ID": "custom-space-id",
        "ARIZE_MODEL_ID": "custom-model-id",
        "ARIZE_API_KEY": "custom-api-key",
        "OPENAI_API_KEY": "custom-openai-key"
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

- The first request with a new environment configuration will take longer as it initializes the components.
- Subsequent requests with the same configuration will use cached components (cache TTL: 30 minutes).
- Different environment configurations are isolated from each other.

## Fallback Behavior

If any of the following conditions are met, the application will use the default values from Google Cloud Secret Manager:

- No `env_overrides` field is provided in the request
- The `env_overrides` field is empty
- A specific environment variable is not included in `env_overrides`
- A provided value is empty or whitespace-only

## Deployment Configuration

When deploying to Cloud Run, ensure:

1. Google Cloud Secret Manager is configured with default values for all required environment variables.
2. The Cloud Run service has appropriate permissions to access Secret Manager.
3. CORS is properly configured if accessing from a web frontend.

## Monitoring

The application logs include information about:
- When dynamic environment variables are used
- Cache hits and misses
- Initialization events

Monitor your Cloud Run logs to track usage and performance of dynamic configurations.