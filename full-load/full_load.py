"""Full Load Pipeline: PostgreSQL -> GCS -> BigQuery

Extracts all data from Cloud SQL PostgreSQL, stages it in Cloud Storage
as Parquet files, then loads it into BigQuery. This is a one-time historical
load — subsequent updates use the incremental pipeline.

Usage:
    python full-load/full_load.py
"""

import os
import tempfile
from datetime import date, datetime
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine
from google.cloud import storage, bigquery

# Load .env from project root
load_dotenv(Path(__file__).parent.parent / ".env")

# Config
PROJECT_ID = os.environ["GCP_PROJECT_ID"]
RAW_BUCKET = "etl-pipeline-gcp-raw-dev"
BQ_DATASET = "ecommerce_dwh_dev"
RUN_DATE = date.today().isoformat()  # e.g. "2026-02-27"

DB_URL = (
    f"postgresql+psycopg2://{os.environ['POSTGRES_USER']}:{os.environ['POSTGRES_PASSWORD']}"
    f"@{os.environ['POSTGRES_HOST']}:{os.environ.get('POSTGRES_PORT', 5432)}"
    f"/{os.environ['POSTGRES_DB']}"
)

# Load order matters: products and customers before orders (foreign keys)
TABLES = ["products", "customers", "orders"]

# BigQuery schemas
BIGQUERY_SCHEMAS: dict[str, list[bigquery.SchemaField]] = {
    "products": [
        bigquery.SchemaField("product_id", "INTEGER"),
        bigquery.SchemaField("name", "STRING"),
        bigquery.SchemaField("category", "STRING"),
        bigquery.SchemaField("subcategory", "STRING"),
        bigquery.SchemaField("brand", "STRING"),
        bigquery.SchemaField("sku", "STRING"),
        bigquery.SchemaField("price", "FLOAT64"),
        bigquery.SchemaField("cost", "FLOAT64"),
        bigquery.SchemaField("weight_kg", "FLOAT64"),
        bigquery.SchemaField("is_active", "BOOLEAN"),
        bigquery.SchemaField("created_at", "DATE"),
    ],
    "customers": [
        bigquery.SchemaField("customer_id", "INTEGER"),
        bigquery.SchemaField("first_name", "STRING"),
        bigquery.SchemaField("last_name", "STRING"),
        bigquery.SchemaField("email", "STRING"),
        bigquery.SchemaField("country", "STRING"),
        bigquery.SchemaField("country_code", "STRING"),
        bigquery.SchemaField("city", "STRING"),
        bigquery.SchemaField("segment", "STRING"),
        bigquery.SchemaField("registration_date", "DATE"),
        bigquery.SchemaField("is_active", "BOOLEAN"),
    ],
    "orders": [
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
    ],
}


# Pipeline steps
def extract_table(engine, table: str) -> pd.DataFrame:
    print(f"  Extracting {table}...")
    t = datetime.now()
    df = pd.read_sql(f"SELECT * FROM {table}", engine)
    elapsed = (datetime.now() - t).total_seconds()
    print(f"    ✅ {len(df):,} rows in {elapsed:.1f}s")
    return df


def upload_to_gcs(df: pd.DataFrame, table: str, gcs_client) -> str:
    """Write DataFrame as Parquet and upload to the raw GCS bucket.
    
    Path: full-load/{run_date}/{table}.parquet
    Returns: the GCS URI of the uploaded file.
    """
    gcs_path = f"full-load/{RUN_DATE}/{table}.parquet"
    bucket = gcs_client.bucket(RAW_BUCKET)
    blob = bucket.blob(gcs_path)

    print(f"  Uploading to gs://{RAW_BUCKET}/{gcs_path}...")
    with tempfile.NamedTemporaryFile(suffix=".parquet", delete=True) as tmp:
        df.to_parquet(tmp.name, index=False, engine="pyarrow")
        blob.upload_from_filename(tmp.name, content_type="application/octet-stream")

    uri = f"gs://{RAW_BUCKET}/{gcs_path}"
    print("    ✅ Uploaded")
    return uri


def load_to_bigquery(uri: str, table: str, bq_client) -> None:
    """Load a Parquet file from GCS into a BigQuery table.
    
    Uses WRITE_TRUNCATE — full load always replaces the entire table.
    """
    bq_table_ref = f"{PROJECT_ID}.{BQ_DATASET}.{table}"
    print(f"  Loading BigQuery {BQ_DATASET}.{table}...")

    job_config = bigquery.LoadJobConfig(
        source_format=bigquery.SourceFormat.PARQUET,
        write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
        schema=BIGQUERY_SCHEMAS[table],
    )

    t = datetime.now()
    load_job = bq_client.load_table_from_uri(uri, bq_table_ref, job_config=job_config)
    load_job.result()  # blocks until complete
    elapsed = (datetime.now() - t).total_seconds()

    dest = bq_client.get_table(bq_table_ref)
    print(f"    ✅ {dest.num_rows:,} rows in BigQuery ({elapsed:.1f}s)")


# Main
def main() -> None:
    print("=" * 60)
    print("Full Load Pipeline: PostgreSQL -> GCS -> BigQuery")
    print(f"Run date : {RUN_DATE}")
    print(f"Project  : {PROJECT_ID}")
    print(f"Bucket   : {RAW_BUCKET}")
    print(f"Dataset  : {BQ_DATASET}")
    print("=" * 60)

    engine = create_engine(DB_URL)
    gcs_client = storage.Client(project=PROJECT_ID)
    bq_client = bigquery.Client(project=PROJECT_ID)

    for table in TABLES:
        print(f"\n[{table.upper()}]")
        df = extract_table(engine, table)
        uri = upload_to_gcs(df, table, gcs_client)
        load_to_bigquery(uri, table, bq_client)

    print()
    print("=" * 60)
    print("Full load complete!")
    print(f"BigQuery: {PROJECT_ID}.{BQ_DATASET}")
    print("=" * 60)


if __name__ == "__main__":
    main()