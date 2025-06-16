#!/bin/bash

# Get the project number
PROJECT_NUMBER=$(gcloud projects describe $(gcloud config get-value project) --format='value(projectNumber)')
SERVICE_ACCOUNT="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"

# # Grant Secret Manager access to the Cloud Run service account
# echo "Granting Secret Manager access to Cloud Run service account..."
# gcloud projects add-iam-policy-binding $(gcloud config get-value project) \
#     --member="serviceAccount:${SERVICE_ACCOUNT}" \
#     --role="roles/secretmanager.secretAccessor"

# # Create secrets for sensitive values
# echo "Setting up secrets..."
# while IFS='=' read -r key value; do
#     # Skip comments and empty lines
#     [[ $key =~ ^#.*$ ]] && continue
#     [[ -z $key ]] && continue
    
#     # Remove any quotes from the value
#     value=$(echo "$value" | tr -d '"' | tr -d "'")
    
#     # Create secrets for sensitive values
#     case $key in
#         OPENAI_API_KEY|ARIZE_API_KEY|ARIZE_SPACE_ID|ARIZE_MODEL_ID)
#             create_or_update_secret "$key" "$value"
#             ;;
#     esac
# done < .env

# Build the container
echo "Building container..."
gcloud builds submit --tag gcr.io/arize-461218/langgraph-fin-agent

# Deploy to Cloud Run with secrets and non-sensitive env vars
echo "Deploying to Cloud Run..."
gcloud run deploy langgraph-fin-agent \
  --image gcr.io/arize-461218/langgraph-fin-agent \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --memory 2Gi \
  --timeout 600 \

echo "Deployment complete!" 