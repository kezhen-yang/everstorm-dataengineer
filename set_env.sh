#!/bin/bash

# Sets the Google Cloud environment variables for the Everstorm workshop.
# It must be SOURCED, not executed, so the exports land in your shell:
#   source ./set_env.sh

# --- Configuration ---
PROJECT_FILE="~/project_id.txt"
GOOGLE_CLOUD_LOCATION="us-central1"
REPO_NAME="everstorm-repo"
INSTANCE_NAME="everstorm-kb-db"
DB_USER="postgres"
DB_PASSWORD="1234qwer" # Workshop convenience. See README "Hardening" before real use.
DB_NAME="everstorm_kb"
AGENT_NAME="support_agent"
# ---------------------


echo "--- Setting Google Cloud Environment Variables ---"

# --- Authentication Check ---
echo "Checking gcloud authentication status..."
if gcloud auth print-access-token > /dev/null 2>&1; then
  echo "gcloud is authenticated."
else
  echo "Error: gcloud is not authenticated."
  echo "Please log in by running: gcloud auth login"
  return 1
fi


# 1. Check if project file exists and set Project ID
PROJECT_FILE_PATH=$(eval echo $PROJECT_FILE)
if [ ! -f "$PROJECT_FILE_PATH" ]; then
  echo "Error: Project file not found at $PROJECT_FILE_PATH"
  echo "Please create $PROJECT_FILE_PATH containing your Google Cloud project ID."
  return 1
fi
PROJECT_ID_FROM_FILE=$(cat "$PROJECT_FILE_PATH")
echo "Setting gcloud config project to: $PROJECT_ID_FROM_FILE"
gcloud config set project "$PROJECT_ID_FROM_FILE" --quiet

# --- Export Core GCP Identifiers ---
export PROJECT_ID=$(gcloud config get project)
export GOOGLE_CLOUD_PROJECT="$PROJECT_ID"
export PROJECT_NUMBER=$(gcloud projects describe ${PROJECT_ID} --format="value(projectNumber)")
export SERVICE_ACCOUNT_NAME=$(gcloud compute project-info describe --format="value(defaultServiceAccount)")

echo "Exported PROJECT_ID=$PROJECT_ID"
echo "Exported PROJECT_NUMBER=$PROJECT_NUMBER"
echo "Exported SERVICE_ACCOUNT_NAME=$SERVICE_ACCOUNT_NAME"

# --- Export Location and Region ---
export GOOGLE_CLOUD_LOCATION="$GOOGLE_CLOUD_LOCATION"
export REGION="$GOOGLE_CLOUD_LOCATION"
echo "Exported REGION=$REGION"

# --- Cloud Storage ---
export BUCKET_NAME="${PROJECT_ID}-everstorm"
echo "Exported BUCKET_NAME=$BUCKET_NAME"

# --- BigQuery ---
export BQ_DATASET="everstorm_data"
echo "Exported BQ_DATASET=$BQ_DATASET"

# --- Dataflow ---
export DF_JOB_NAME="everstorm-kb-vectorize-$(date +%Y%m%d-%H%M%S)"
echo "Exported DF_JOB_NAME=$DF_JOB_NAME"

# --- Vertex AI / GenAI ---
export GOOGLE_GENAI_USE_VERTEXAI="TRUE"

# --- Cloud SQL / Database ---
export INSTANCE_NAME="$INSTANCE_NAME"
export DB_USER="$DB_USER"
export DB_PASSWORD="$DB_PASSWORD"
export DB_NAME="$DB_NAME"
export KB_TABLE="policy_chunks"
echo "Exported INSTANCE_NAME=$INSTANCE_NAME"
echo "Exported DB_NAME=$DB_NAME"
echo "Exported KB_TABLE=$KB_TABLE"

# --- Artifact Registry & Cloud Run ---
export REPO_NAME="$REPO_NAME"
export IMAGE_NAME="everstorm-support-agent"
export AGENT_NAME="$AGENT_NAME"
export IMAGE_TAG="latest"
export IMAGE_PATH="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO_NAME}/${IMAGE_NAME}:${IMAGE_TAG}"
export SERVICE_NAME="everstorm-support-agent"
export PUBLIC_URL="https://everstorm-support-agent-${PROJECT_NUMBER}.${REGION}.run.app"

echo "Exported REPO_NAME=$REPO_NAME"
echo "Exported IMAGE_PATH=$IMAGE_PATH"
echo "Exported SERVICE_NAME=$SERVICE_NAME"
echo "Exported PUBLIC_URL=$PUBLIC_URL"

echo ""
echo "--- Environment setup complete ---"
