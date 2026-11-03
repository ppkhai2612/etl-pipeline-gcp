"""Incremental Load Pipeline: PostgreSQL -> GCS -> BigQuery

Extracts only rows inserted or updated since the last successful run.
Uses a watermark stored in GCS (_metadata/watermarks.json inside the raw
bucket) to track the high-water mark (the latest `updated_at` timestamp
seen so far).

Only orders are tracked incrementally — products and customers are
stable enough to be handled by the full load pipeline.

Usage:
    python incremental-load/incremental_load.py
"""

import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine
from google.cloud import storage, bigquery

# Load .env from project root
load_dotenv(Path(__file__).parent.parent / ".env")

# Config
PROJECT_ID = os.environ["GCP_PROJECT_ID"]
RAW_BUCKET = os.environ["GCS_RAW_BUCKET"]
BQ_DATASET = "ecommerce_dwh_dev"
WATERMARK_BLOB = "_metadata/watermarks.json"  # path inside RAW_BUCKET

_pg_host = os.environ["POSTGRES_HOST"]
_pg_user = os.environ["POSTGRES_USER"]
_pg_pass = os.environ["POSTGRES_PASSWORD"]
_pg_db = os.environ["POSTGRES_DB"]
_pg_port = os.environ.get("POSTGRES_PORT", "5432")

if _pg_host.startswith("/"):
    # Unix socket (Cloud SQL proxy socket path) — host must be a query param
    DB_URL = f"postgresql+psycopg2://{_pg_user}:{_pg_pass}@/{_pg_db}?host={_pg_host}"
else:
    DB_URL = f"postgresql+psycopg2://{_pg_user}:{_pg_pass}@{_pg_host}:{_pg_port}/{_pg_db}"

ORDERS_SCHEMA = [
    bigquery.SchemaField("order_id", "INTEGER"),
    bigquery.SchemaField("customer_id", "INTEGER"),
    bigquery.SchemaField("product_id", "INTEGER"),
    bigquery.SchemaField("order_date", "DATE"),
    bigquery.SchemaField("order_timestamp", "TIMESTAMP"),
    bigquery.SchemaField("quantity", "INTEGER"),
    bigquery.SchemaField("unit_price", "FLOAT64"),
    bigquery.SchemaField("discount_amount", "FLOAT64"),
    bigquery.SchemaField("tax_amount", "FLOAT64"),
    bigquery.SchemaField("shipping_cost", "FLOAT64"),
    bigquery.SchemaField("total_amount", "FLOAT64"),
    bigquery.SchemaField("order_status", "STRING"),
    bigquery.SchemaField("payment_method", "STRING"),
    bigquery.SchemaField("created_at", "TIMESTAMP"),
    bigquery.SchemaField("updated_at", "TIMESTAMP"),
]


# Watermark helpers
def load_watermark(gcs_client) -> datetime | None:
    """Read the last successful watermark from GCS.
    
    Stored at: gs://{RAW_BUCKET}/_metadata/watermarks.json
    Returns None if the file doesn't exist yet (first run).
    """
    blob = gcs_client.bucket(RAW_BUCKET).blob(WATERMARK_BLOB)
    if not blob.exists():
        return None
    data = json.loads(blob.download_as_text())
    ts = data.get("orders")
    return datetime.fromisoformat(ts) if ts else None


def save_watermark(ts: datetime, gcs_client) -> None:
    """Persist the watermark back to GCS after a successful run."""
    blob = gcs_client.bucket(RAW_BUCKET).blob(WATERMARK_BLOB)
    # Read existing content first so other table watermarks aren't overwritten
    existing = json.loads(blob.download_as_text()) if blob.exists() else {}
    existing["orders"] = ts.isoformat()
    blob.upload_from_string(
        json.dumps(existing, indent=2), content_type="application/json"
    )


# Pipeline steps
def extract_new_orders(engine, watermark: datetime | None) -> pd.DataFrame:
    """
    Extract orders from PostgreSQL that are newer than the watermark.
    If no watermark exists (first incremental run), print the warning message —
    the full load pipeline must run first.
    """
    if watermark is None:
        # No watermark: pull everything added after the full load baseline.
        # We can't know when the full load ran, so we require it to be set first.
        print("  ⚠️  No watermark found. Extracting all orders as baseline.")
        query = "SELECT * FROM orders"
    else:
        query = f"SELECT * FROM orders WHERE updated_at > '{watermark.isoformat()}'"
    
    print(f"  Watermark : {watermark or 'none (full extract)'}")
    t = datetime.now()
    df = pd.read_sql(query, engine)
    elapsed = (datetime.now() - t).total_seconds()
    print(f"  Extracted : {len(df):,} rows in {elapsed:.1f}s")
    return df


def upload_to_gcs(df: pd.DataFrame, run_ts: str, gcs_client) -> str:
    """Upload incremental Parquet file to the raw GCS bucket.

    Path pattern: incremental/{run_timestamp}/orders.parquet
    """
    gcs_path = f"incremental/{run_ts}/orders.parquet"
    bucket = gcs_client.bucket(RAW_BUCKET)
    blob = bucket.blob(gcs_path)

    print(f"  Uploading to gs://{RAW_BUCKET}/{gcs_path}...")
    with tempfile.NamedTemporaryFile(suffix=".parquet", delete=True) as tmp:
        df.to_parquet(tmp.name, index=False, engine="pyarrow")
        blob.upload_from_filename(tmp.name, content_type="application/octet-stream")

    return f"gs://{RAW_BUCKET}/{gcs_path}"


def load_to_bigquery(uri: str, bq_client) -> None:
    """Append incremental orders to BigQuery.

    Uses WRITE_APPEND — new rows are added, not replaced.
    Deduplication (handling order updates) happens downstream via a view.
    """
    bq_table_ref = f"{PROJECT_ID}.{BQ_DATASET}.orders"
    print(f"  Loading into BigQuery {BQ_DATASET}.orders (APPEND)...")

    job_config = bigquery.LoadJobConfig(
        source_format=bigquery.SourceFormat.PARQUET,
        write_disposition=bigquery.WriteDisposition.WRITE_APPEND,
        schema=ORDERS_SCHEMA,
    )

    t = datetime.now()
    load_job = bq_client.load_table_from_uri(uri, bq_table_ref, job_config=job_config)
    load_job.result()
    elapsed = (datetime.now() - t).total_seconds()

    dest = bq_client.get_table(bq_table_ref)
    print(f"  ✅ Done in {elapsed:.1f}s — {dest.num_rows:,} total rows in BigQuery")


def main() -> None:
    run_ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    print("=" * 60)
    print("Incremental Load Pipeline: PostgreSQL -> GCS -> BigQuery")
    print(f"Run     : {run_ts}")
    print(f"Project : {PROJECT_ID}")
    print(f"Bucket  : {RAW_BUCKET}")
    print(f"Dataset : {BQ_DATASET}")
    print("=" * 60)

    engine = create_engine(DB_URL)
    gcs_client = storage.Client(project=PROJECT_ID)
    bq_client = bigquery.Client(project=PROJECT_ID)

    watermark = load_watermark(gcs_client)

    print("\n[ORDERS]")
    df = extract_new_orders(engine, watermark)

    if df.empty:
        print("  ✅ No new orders since last run. Nothing to load.")
        return

    uri = upload_to_gcs(df, run_ts, gcs_client)
    print("    ✅ Uploaded")
    load_to_bigquery(uri, bq_client)
    
    # Capture the high-water mark for the next run.
    # - Baseline run (no prior watermark): use datetime.now() so only rows
    #   inserted *after* this pipeline run are picked up incrementally.
    #   MAX(updated_at) would be wrong here — historical data has synthetic
    #   timestamps scattered across the day, possibly in the future.
    # - Incremental run: use MAX(updated_at) from this batch, which is the
    #   latest change we've processed.
    if watermark is None:
        new_watermark = datetime.now()
    else:
        new_watermark = pd.to_datetime(df["updated_at"]).max().to_pydatetime()
    
    save_watermark(new_watermark, gcs_client)
    print(f"\n  Watermark updated -> {new_watermark.isoformat()}")

    print()
    print("=" * 60)
    print("Incremental load complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()