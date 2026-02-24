#!/bin/bash

# Ensure script stops on first error
set -e

echo "Starting Google Cloud Run Deployment..."

# You can modify these variables based on your GCP project
PROJECT_ID=$(gcloud config get-value project)
SERVICE_NAME="schedule-management-api"
REGION="asia-east1" # Change region if needed (e.g. us-central1)

if [ -z "$PROJECT_ID" ]; then
    echo "Error: No Google Cloud project selected."
    echo "Please set your project using: gcloud config set project [YOUR_PROJECT_ID]"
    exit 1
fi

echo "Deploying to Project: $PROJECT_ID"
echo "Service Name: $SERVICE_NAME"
echo "Region: $REGION"

# Deploying directly from source to Cloud Run
# This command automatically builds the container using Cloud Build and deploys it
gcloud run deploy "$SERVICE_NAME" \
  --source . \
  --region "$REGION" \
  --allow-unauthenticated \
  --project "$PROJECT_ID"

echo "Deployment finished!"
