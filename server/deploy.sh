#!/bin/bash

# Ensure script stops on first error
set -e

echo "========================================="
echo "Starting Google Cloud Run Deployment..."
echo "========================================="

# You can modify these variables based on your GCP project
PROJECT_ID=$(gcloud config get-value project)
SERVICE_NAME="schedule-backend"
REGION="asia-east1" # Change region if needed (e.g. us-central1)
# Accept environment file as an argument (e.g., ./deploy.sh .env-stage)
ENV_FILE="${1:-.env}"

if [ -z "$PROJECT_ID" ]; then
    echo "❌ Error: No Google Cloud project selected."
    echo "Please set your project using: gcloud config set project [YOUR_PROJECT_ID]"
    exit 1
fi

echo "Deploying to Project: $PROJECT_ID"
echo "Service Name: $SERVICE_NAME"
echo "Region: $REGION"

# Read .env file and format it into a YAML file for --env-vars-file
echo "========================================="
echo "Parsing $ENV_FILE for environment variables..."
YAML_FILE="env_vars.yaml"

if [ -f "$ENV_FILE" ]; then
    > "$YAML_FILE" # Clear or create the YAML file
    while IFS= read -r line || [ -n "$line" ]; do
        # Ignore comments and empty lines
        if [[ ! "$line" =~ ^#.*$ ]] && [[ -n "$line" ]]; then
            # Split line into KEY and VALUE
            KEY="${line%%=*}"
            VALUE="${line#*=}"
            
            # Escape single quotes by doubling them for YAML
            ESCAPED_VALUE="${VALUE//\'/\'\'}"
            
            echo "${KEY}: '${ESCAPED_VALUE}'" >> "$YAML_FILE"
        fi
    done < "$ENV_FILE"
    echo "✅ Loaded environment variables into $YAML_FILE"
else
    echo "⚠️ .env file not found at $ENV_FILE. Proceeding without env vars."
fi

# Deploying source code directly to Cloud Run
echo "========================================="
echo "Deploying to Cloud Run (This will build the image automatically)..."

if [ -f "$YAML_FILE" ]; then
    gcloud run deploy "$SERVICE_NAME" \
      --source . \
      --region "$REGION" \
      --allow-unauthenticated \
      --project "$PROJECT_ID" \
      --memory 1Gi \
      --cpu 1 \
      --env-vars-file "$YAML_FILE"

    # Clean up the generated YAML file
    rm -f "$YAML_FILE"
else
    gcloud run deploy "$SERVICE_NAME" \
      --source . \
      --region "$REGION" \
      --allow-unauthenticated \
      --project "$PROJECT_ID" \
      --memory 1Gi \
      --cpu 1
fi

echo "========================================="
echo "✅ Deployment finished successfully!"
echo "========================================="
