# Instrumentation and Environment Variable Setup

This document describes the instrumentation and environment variable handling that has now been implemented in the LangGraph Finance Agent to match the functionality of the Arize Chatbot.

## Overview

The LangGraph Finance Agent now supports the same flexible instrumentation and environment variable override capabilities that are available in the Arize Chatbot project. This ensures both services behave consistently when it comes to:

- **OpenTelemetry Instrumentation**: Runtime configuration of tracing and monitoring
- **Environment Variable Overrides**: Per-request environment variable customization
- **Arize Integration**: Seamless integration with Arize observability platform

## Key Components Added

### 1. Flexible Instrumentation (`flexible_instrumentation.py`)

A comprehensive instrumentation manager that allows runtime configuration without relying on global state:

- **TracerConfig**: Dataclass for OpenTelemetry tracer configuration
- **FlexibleInstrumentation**: Manager class for handling instrumentation lifecycle
- **LangChain Integration**: Uses `LangChainInstrumentor` instead of `LlamaIndexInstrumentor`

Key features:
- Runtime reconfiguration of instrumentation
- Environment variable header support for Arize
- Automatic cleanup of resources
- Context manager for temporary configurations

### 2. Environment Variable Validation

Enhanced environment variable handling with support for:

```python
allowed_vars = {
    'ARIZE_SPACE_ID',
    'ARIZE_MODEL_ID',
    'ARIZE_API_KEY',
    'OPENAI_API_KEY',
    'FMP_API_KEY'  # Finance-specific addition
}
```

### 3. Enhanced API Endpoints

All endpoints now support `env_overrides` parameter:

- `/api/chat` - Chat endpoint with environment variable overrides
- `/api/finance-query` - Finance-specific endpoint with overrides
- `/debug/config` - Enhanced debug endpoint showing instrumentation status
- `/health` - Health check with initialization status

## API Compatibility

The LangGraph Finance Agent now provides the same API interface as Arize Chatbot:

### Request Format

```json
{
    "message": "Your message here",
    "session_id": "optional-session-id",
    "env_overrides": {
        "ARIZE_SPACE_ID": "your-space-id",
        "ARIZE_API_KEY": "your-api-key",
        "ARIZE_MODEL_ID": "your-model-id"
    }
}
```

### Response Format

```json
{
    "response": "Agent response",
    "session_id": "session-identifier"
}
```

Note: Unlike Arize Chatbot, LangGraph Finance Agent does not include a `sources` field as it doesn't use RAG with document sources.

## Environment Variables

### Required for Arize Integration

- `ARIZE_SPACE_ID`: Your Arize space identifier
- `ARIZE_API_KEY`: Your Arize API key

### Optional Configuration

- `ARIZE_MODEL_ID`: Model identifier (defaults to "langgraph_finance_agent")
- `OPENAI_API_KEY`: OpenAI API key for LLM operations
- `FMP_API_KEY`: Financial Modeling Prep API key for finance data

### CORS Configuration

- `CORS_ORIGINS`: Comma-separated list of allowed origins (defaults to "*")

## Testing

### Individual Service Testing

Run the instrumentation test for LangGraph Finance Agent:

```bash
cd langgraph-fin-agent
python test_instrumentation.py
```

### Comparative Testing

Compare both services side-by-side:

```bash
# Set the base URLs for both services
export ARIZE_BASE_URL="http://localhost:8081"
export LANGGRAPH_BASE_URL="http://localhost:8080"

# Run the comparison
python compare_apis.py
```

## Debug Endpoints

Both services now provide identical debug information:

### `/debug/config`

Returns comprehensive configuration status:

```json
{
    "instrumentation": {
        "is_configured": true,
        "has_valid_arize_config": true
    },
    "arize_config": {
        "space_id_present": true,
        "api_key_present": true,
        "model_id": "langgraph_finance_agent"
    },
    "environment_vars": {
        "ARIZE_SPACE_ID_set": true,
        "ARIZE_API_KEY_set": true,
        "ARIZE_MODEL_ID": "langgraph_finance_agent",
        "OPENAI_API_KEY_set": true,
        "FMP_API_KEY_set": false
    },
    "cache_info": {
        "total_cached_configs": 0,
        "cache_ttl_minutes": 30
    },
    "service": "langgraph-finance-agent"
}
```

## Key Differences from Arize Chatbot

While the core functionality is identical, there are a few expected differences:

1. **Service Name**: Returns "langgraph-finance-agent" instead of arize-chatbot identifiers
2. **Default Model ID**: Uses "langgraph_finance_agent" as default instead of "default_model"
3. **Instrumentation Library**: Uses LangChain instrumentation instead of LlamaIndex
4. **Response Fields**: Does not include `sources` field as it's not a RAG-based system
5. **Additional Endpoints**: Includes `/api/finance-query` endpoint for finance-specific queries
6. **Environment Variables**: Supports `FMP_API_KEY` for financial data access

## Implementation Notes

- **Caching**: Currently disabled during initialization to ensure proper instrumentation reconfiguration
- **Session Management**: Uses the same session management system as Arize Chatbot
- **Error Handling**: Consistent error handling and logging patterns
- **Backwards Compatibility**: Maintains `app_state` for backwards compatibility

## Usage Examples

### Basic Chat Request

```python
import requests

response = requests.post("http://localhost:8080/api/chat", json={
    "message": "What's the current market sentiment?"
})
```

### Chat with Environment Overrides

```python
response = requests.post("http://localhost:8080/api/chat", json={
    "message": "Analyze Tesla's performance",
    "env_overrides": {
        "ARIZE_SPACE_ID": "your-space-id",
        "ARIZE_API_KEY": "your-api-key",
        "ARIZE_MODEL_ID": "tesla-analysis-agent"
    }
})
```

### Finance-Specific Query

```python
response = requests.post("http://localhost:8080/api/finance-query", json={
    "query": "Get latest earnings for AAPL",
    "thread_id": "earnings-thread-1"
})
```

This setup ensures that both the Arize Chatbot and LangGraph Finance Agent provide consistent behavior for instrumentation and environment variable handling, making them interchangeable from an infrastructure and monitoring perspective. 