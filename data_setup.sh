#!/bin/bash

# Provisions the Everstorm data environment:
#   1. Creates the Cloud SQL PostgreSQL instance (in the background, ~10-15 min).
#   2. Creates the GCS bucket.
#   3. Uploads the support tickets and the knowledge-base chunks.
#
# Run AFTER sourcing set_env.sh. Idempotent: safe to re-run after a partial failure.

# --- Pre-flight Check ---
if [ -z "$PROJECT_ID" ] || [ -z "$BUCKET_NAME" ] || [ -z "$REGION" ] || [ -z "$INSTANCE_NAME" ] || [ -z "$DB_PASSWORD" ]; then
  echo "Error: Required environment variables are not set."
  echo "Please run 'source ./set_env.sh' before executing this script."
  exit 1
fi

echo "--- Everstorm Data Environment Setup for Project: $PROJECT_ID ---"
echo ""

# --- 1. Cloud SQL instance ---
echo "--> Task 1: Checking/creating Cloud SQL instance '$INSTANCE_NAME'."
echo "    This starts in the background and takes 10-15 minutes."

gcloud sql instances describe $INSTANCE_NAME --project=$PROJECT_ID >/dev/null 2>&1

if [ $? -eq 0 ]; then
  echo "    Instance '$INSTANCE_NAME' already exists. Skipping creation."
else
  gcloud sql instances create $INSTANCE_NAME \
    --database-version=POSTGRES_16 \
    --tier=db-custom-1-3840 \
    --region=$REGION \
    --root-password="$DB_PASSWORD" \
    --storage-size=10GB \
    --edition=enterprise \
    --enable-google-ml-integration \
    --database-flags cloudsql.enable_google_ml_integration=on > /dev/null 2>&1 &

  SQL_PID=$!
  echo "    Creation started in the background (PID: $SQL_PID)."
fi
echo ""


# --- 2. GCS bucket ---
echo "--> Task 2: Checking/creating GCS bucket 'gs://$BUCKET_NAME'."
gcloud storage buckets describe gs://$BUCKET_NAME >/dev/null 2>&1 || \
gcloud storage buckets create gs://$BUCKET_NAME --project=$PROJECT_ID --location=$REGION --uniform-bucket-level-access
echo "    Bucket 'gs://$BUCKET_NAME' is ready."
echo ""


# --- 3. Upload the two corpora ---
#
# tickets/ -> BigQuery (Parts 1-2). One ticket per FILE and per LINE: the external
#             table reads CSV with a field delimiter, which yields one row per
#             line. These files are pre-flattened for exactly that reason.
#
# kb/      -> Cloud SQL via Dataflow (Parts 3-5). Section-level chunks, because
#             the pipeline embeds each whole file as a single vector and has no
#             chunking stage of its own.
#
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
TICKETS_DIR="${SCRIPT_DIR}/data/tickets"
KB_DIR="${SCRIPT_DIR}/data/kb"

echo "--> Task 3: Uploading data files to GCS."
if [ -d "$TICKETS_DIR" ]; then
  echo "    Uploading support tickets from $TICKETS_DIR..."
  gcloud storage cp ${TICKETS_DIR}/*.txt gs://${BUCKET_NAME}/tickets/ --quiet
  echo "    Uploaded $(ls ${TICKETS_DIR}/*.txt | wc -l | tr -d ' ') tickets."
else
  echo "    Warning: Directory not found, skipping: $TICKETS_DIR"
fi

if [ -d "$KB_DIR" ]; then
  echo "    Uploading knowledge-base chunks from $KB_DIR..."
  gcloud storage cp ${KB_DIR}/*.md gs://${BUCKET_NAME}/kb/ --quiet
  echo "    Uploaded $(ls ${KB_DIR}/*.md | wc -l | tr -d ' ') chunks."
else
  echo "    Warning: Directory not found, skipping: $KB_DIR"
fi
echo ""

echo "--- Everstorm Data Environment Setup Complete ---"
echo ""
echo "Verify with:"
echo "  gcloud storage ls gs://${BUCKET_NAME}/tickets/ | wc -l    # expect 180"
echo "  gcloud storage ls gs://${BUCKET_NAME}/kb/      | wc -l    # expect 263"
echo "  gcloud sql instances describe ${INSTANCE_NAME} --format='value(state)'  # RUNNABLE"
