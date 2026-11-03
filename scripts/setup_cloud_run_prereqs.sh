#!/bin/bash
# Prepares GCP for Cloud Run Jobs + Cloud Scheduler.
# Safe to re-run: SA creation is skipped if the service account already exists,
# and IAM bindings are idempotent.
#
# Usage (from project root):
#     bash scripts/setup_cloud_run_prereqs.sh

set -euo pipefail

# Load .env
if [[ -f ".env" ]]; then
    ENV_FILE=".env"
elif [[ -f "$(dirname "$0")/../.env" ]]; then
    ENV_FILE="$(dirname "$0")/../.env"
else
    echo "❌  .env not found. Run this script from the project root."
    exit 1
fi
TMP_ENV=$(mktemp)
grep -v '^[[:space:]]*#' "$ENV_FILE" | grep -v '^[[:space:]]*$' | tr -d '\r' > "$TMP_ENV"
set -o allexport
source "$TMP_ENV"
set +o allexport
rm -f "$TMP_ENV"

PROJECT_ID="${GCP_PROJECT_ID}"
SA_NAME="etl-pipeline-sa"
SA_EMAIL="${SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"

echo "============================================================"
echo "  Cloud Run prereqs setup"
echo "  Project : ${PROJECT_ID}"
echo "  SA      : ${SA_EMAIL}"
echo "============================================================"
echo ""

# Step 1: Enable APIs
echo "   Enabling APIs..."
gcloud services enable \
    run.googleapis.com \
    cloudscheduler.googleapis.com \
    artifactregistry.googleapis.com \
    --project="${PROJECT_ID}"
echo "   ✅ APIs enabled"
echo ""

# Step 2: Create service account (skip if it already exists)
echo "   Creating service account..."
if gcloud iam service-accounts describe "${SA_EMAIL}" \
    --project="${PROJECT_ID}" &>/dev/null; then
    echo "   ℹ️  Service account already exists — skipping creation"
else
    gcloud iam service-accounts create "${SA_NAME}" \
        --display-name="ETL Pipeline Service Account" \
        --project="${PROJECT_ID}"
    echo "   ✅ Service account created"
fi
echo ""

# Step 3: Grant IAM roles
echo "   Binding IAM roles..."

ROLES=(
    "roles/cloudsql.client"      # Read from Cloud SQL
    "roles/storage.objectAdmin"  # Read/write GCS (parquet + watermark)
    "roles/bigquery.dataEditor"  # Append rows to BigQuery tables
    "roles/bigquery.jobUser"     # Submit BigQuery load jobs
    "roles/run.invoker"          # Allow Cloud Scheduler to trigger the job
)

for ROLE in "${ROLES[@]}"; do
    gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
        --member="serviceAccount:${SA_EMAIL}" \
        --role="${ROLE}" \
        --condition=None \
        --quiet
    echo "   ✅ ${ROLE}"
done
echo ""

echo "============================================================"
echo "  Done!"
echo "  SA_EMAIL=${SA_EMAIL}"
echo "  (exported for use in subsequent commands)"
echo "============================================================"