# Serverless Deployment Guide for GuardRails AI Server

This guide covers deploying your GuardRails AI server to various serverless platforms.

## Platform Recommendations

### 🟢 **Google Cloud Run** (Recommended)
**Best for:** Production workloads, flexible scaling, longer timeouts

**Pros:**
- Up to 60-minute timeout
- Up to 32GB memory
- Easy container deployment
- Good cold start performance

**Deploy:**
```bash
# Build and push to Google Container Registry
gcloud builds submit --tag gcr.io/YOUR_PROJECT_ID/guardrails-server

# Deploy to Cloud Run
gcloud run deploy guardrails-server \
  --image gcr.io/YOUR_PROJECT_ID/guardrails-server \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --memory 4Gi \
  --timeout 3600 \
  --set-env-vars GUARDRAILS_TOKEN=your_token_here
```

### 🟡 **AWS Lambda** (Challenging but possible)
**Best for:** Event-driven workloads, cost optimization

**Limitations:**
- 15-minute timeout
- 10GB container image limit
- Cold starts with ML models

**Requirements:**
1. Add `mangum` to requirements.txt
2. Use `Dockerfile.lambda`
3. Reduce validators to essential ones only

**Deploy with AWS SAM:**
```yaml
# template.yaml
AWSTemplateFormatVersion: '2010-09-09'
Transform: AWS::Serverless-2016-10-31

Resources:
  GuardrailsFunction:
    Type: AWS::Serverless::Function
    Properties:
      PackageType: Image
      ImageUri: your-account.dkr.ecr.region.amazonaws.com/guardrails:latest
      Timeout: 900  # 15 minutes max
      MemorySize: 3008  # Max memory
      Environment:
        Variables:
          GUARDRAILS_TOKEN: !Ref GuardrailsToken
```

### 🟢 **Azure Container Instances**
**Best for:** Simple deployment, predictable workloads

**Deploy:**
```bash
# Build and push to Azure Container Registry
az acr build --registry YOUR_REGISTRY --image guardrails-server .

# Deploy to Container Instances
az container create \
  --resource-group YOUR_RG \
  --name guardrails-server \
  --image your_registry.azurecr.io/guardrails-server \
  --cpu 2 \
  --memory 4 \
  --restart-policy Always \
  --environment-variables GUARDRAILS_TOKEN=your_token_here
```

## Build Arguments

Set your GuardRails token during build:

```bash
# Docker build with token
docker build --build-arg GUARDRAILS_TOKEN=your_token_here -t guardrails-server .

# Without token (limited functionality)
docker build -t guardrails-server .
```

## Performance Optimization Tips

### 1. **Guard Selection**
Choose only the guards you need:
```python
# In config.py - comment out unused guards
# guard = Guard()  # Disable if not needed
# pii_guard = Guard()  # Heavy model - disable if not needed
```

### 2. **Memory Configuration**
- **Cloud Run**: 2-4GB recommended
- **Lambda**: 3008MB (maximum)
- **Azure**: 2-4GB recommended

### 3. **Cold Start Optimization**
```python
# In server.py - add global initialization
import asyncio
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Pre-warm guards during startup
    for guard_name, guard in GUARDS.items():
        try:
            # Run a quick validation to warm up the guard
            guard.validate("test", num_reasks=0)
        except:
            pass  # Expected to fail, just warming up
    yield

# Update app initialization
app = FastAPI(lifespan=lifespan, ...)
```

### 4. **Monitoring & Observability**
Add health checks and metrics:
```python
@app.get("/ready")
async def readiness_check():
    """Check if all guards are loaded"""
    return {"status": "ready", "guards": list(GUARDS.keys())}
```

## Cost Comparison

| Platform | Cold Start | Warm Instance | Memory | Timeout |
|----------|------------|---------------|---------|---------|
| Cloud Run | ~2-5s | ~100ms | 32GB | 60min |
| Lambda | ~5-15s | ~50ms | 10GB | 15min |
| Azure CI | ~10s | ~100ms | 16GB | No limit |

## Troubleshooting

### Common Issues:

1. **"NLTK data not found"**
   - Ensure NLTK_DATA environment variable is set
   - Check that data was downloaded during build

2. **"Guard not found"**
   - Verify GuardRails token is valid
   - Check that hub install succeeded during build

3. **Timeout during cold start**
   - Reduce number of guards
   - Increase memory allocation
   - Use Cloud Run instead of Lambda

4. **Large image size**
   - Use multi-stage builds (already included)
   - Remove unused validators
   - Consider Lambda-specific optimizations

## Next Steps

1. Choose your platform based on requirements
2. Set up CI/CD pipeline for automated deployment
3. Configure monitoring and alerting
4. Test with production load 