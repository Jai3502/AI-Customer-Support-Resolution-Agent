#!/usr/bin/env bash
# ==============================================================================
# Google Cloud Run Automated Deployment Script
# ==============================================================================

set -e

PROJECT_ID=$(gcloud config get-value project 2>/dev/null || echo "ai-customer-support-proj")
REGION="asia-south1"
SERVICE_NAME="ai-customer-support-agent"
IMAGE_TAG="gcr.io/${PROJECT_ID}/${SERVICE_NAME}:latest"

echo "🚀 Starting Cloud Deployment for ${SERVICE_NAME}..."
echo "📦 Project: ${PROJECT_ID} | Region: ${REGION}"

# Step 1: Build Container Image via Cloud Build or Docker
echo "🔨 Building Docker image: ${IMAGE_TAG}"
gcloud builds submit --tag "${IMAGE_TAG}" .

# Step 2: Deploy Container to Google Cloud Run
echo "☁️ Deploying image to Google Cloud Run..."
gcloud run deploy "${SERVICE_NAME}" \
  --image "${IMAGE_TAG}" \
  --platform managed \
  --region "${REGION}" \
  --allow-unauthenticated \
  --port 8501 \
  --set-env-vars GEMINI_MODEL="gemini-3.5-flash-lite"

echo "✅ Deployment completed successfully!"
gcloud run services describe "${SERVICE_NAME}" --platform managed --region "${REGION}" --format 'value(status.url)'
