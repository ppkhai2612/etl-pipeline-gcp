#!/bin/bash
# Create Cloud Storage Buckets for ETL Pipeline
# Reads bucket names and region from .env in the project root
#
# Usage: ./scripts/create_buckets.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Load .env
if [ -f "$PROJECT_ROOT/.env" ]; then
    set -a
    source <(grep -v '^\s*#' "$PROJECT_ROOT/.env" | grep -v '^\s*$')
    set +a
else
    echo "ERROR: .env file not found at $PROJECT_ROOT/.env"
    echo "Copy .env.example to .env and fill in your values."
    exit 1
fi

# Validate required variables
for var in GCP_PROJECT_ID GCS_REGION GCS_RAW_BUCKET GCS_STAGING_BUCKET GCS_PROCESSED_BUCKET; do
    if [ -z "${!var}" ]; then
        echo "ERROR: $var is not set in .env"
        exit 1
    fi
done

echo "=========================================="
echo "  Creating Cloud Storage Buckets"
echo "=========================================="
echo "  Project : $GCP_PROJECT_ID"
echo "  Region  : $GCS_REGION"
echo ""

create_bucket() {
    local name="$1"
    if gcloud storage buckets describe "gs://${name}" &>/dev/null; then
        echo "  ⚠️  Already exists: gs://${name}"
    else
        gcloud storage buckets create "gs://${name}" --project="$GCP_PROJECT_ID" --location="$GCS_REGION" 
        echo "  ✅ Created: gs://${name}"
    fi
}

create_bucket "$GCS_RAW_BUCKET"
create_bucket "$GCS_STAGING_BUCKET"
create_bucket "$GCS_PROCESSED_BUCKET"

echo ""
echo "=========================================="
echo "  Done!"
echo "=========================================="
echo "  gs://$GCS_RAW_BUCKET"
echo "  gs://$GCS_STAGING_BUCKET"
echo "  gs://$GCS_PROCESSED_BUCKET"
echo ""
echo "Verify with: gcloud storage ls --project=your-gcp-project-id"