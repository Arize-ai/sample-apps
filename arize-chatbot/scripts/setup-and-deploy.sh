#!/bin/bash

# # Function to create or update a secret
# create_or_update_secret() {
#     local secret_name=$1
#     local secret_value=$2
    
#     # Check if secret exists
#     if gcloud secrets describe "$secret_name" >/dev/null 2>&1; then
#         echo "Updating existing secret: $secret_name"
#         echo -n "$secret_value" | gcloud secrets versions add "$secret_name" --data-file=-
#     else
#         echo "Creating new secret: $secret_name"
#         echo -n "$secret_value" | gcloud secrets create "$secret_name" --data-file=-
#     fi
# }

# # Load environment variables from .env file
# if [ ! -f .env ]; then
#     echo "Error: .env file not found"
#     exit 1
# fi

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
gcloud builds submit --tag gcr.io/arize-461218/arize-chatbot-1

# Deploy to Cloud Run with secrets and non-sensitive env vars
echo "Deploying to Cloud Run..."
gcloud run deploy arize-chatbot \
  --image gcr.io/arize-461218/arize-chatbot-1 \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --memory 2Gi \
  --timeout 600 \

echo "Deployment complete!" 