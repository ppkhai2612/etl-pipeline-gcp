# Architecture

```mermaid
flowchart LR
    subgraph SOURCE["Operational data source"]
        GEN["Data generation scripts<br/>(initial seed / daily data)"]
        SQL[("Cloud SQL<br/>PostgreSQL: ecommerce<br/>products · customers · orders")]
        GEN -->|"Seed / add records"| SQL
    end

    subgraph LOCAL["Local development and bootstrap"]
        FULL["Full-load pipeline<br/>full_load.py"]
    end

    subgraph SCHEDULED["Scheduled GCP workloads · us-east1"]
        SCHED["Cloud Scheduler<br/>incremental: 01:00 Asia/Ho_Chi_Minh<br/>quality: 03:00 Asia/Ho_Chi_Minh"]
        INC["Cloud Run Job<br/>etl-incremental-load"]
        DQ["Cloud Run Job<br/>etl-data-quality"]
        SCHED -->|"Start job"| INC
        SCHED -->|"Start job"| DQ
    end

    AR["Artifact Registry<br/>container images"]
    SA["etl-pipeline-sa<br/>Cloud SQL · Storage · BigQuery · Secret access"]

    subgraph STAGING["Cloud Storage · raw bucket"]
        PARQUET["Parquet staging files<br/>full-load/ · incremental/"]
        WM["_metadata/watermarks.json<br/>orders high-water mark"]
    end

    subgraph DWH["BigQuery · ecommerce_dwh_dev"]
        RAW[("Raw tables<br/>products · customers · orders")]
        LATEST["orders_latest<br/>deduplicated view"]
        ANALYTICS["Analytics views<br/>daily_revenue<br/>customer_lifetime_value<br/>product_performance"]
        RAW --> LATEST
        LATEST --> ANALYTICS
        RAW --> ANALYTICS
    end

    subgraph OPS["Operations"]
        LOG["Cloud Logging"]
        MON["Cloud Monitoring<br/>Cloud Run execution failures"]
        EMAIL["Email notification channel"]
        MON -->|"Failure alert"| EMAIL
    end

    FULL -->|"Read all three tables"| SQL
    FULL -->|"Upload Parquet"| PARQUET
    FULL -->|"BigQuery load · WRITE_TRUNCATE"| RAW

    INC -->|"Read changed orders by updated_at"| SQL
    INC -->|"Upload Parquet"| PARQUET
    INC -->|"Load orders · WRITE_APPEND"| RAW
    INC <-->|"Read / advance watermark"| WM

    DQ -->|"Run freshness, volume, null, duplicate, amount, and status checks"| DWH

    AR -.->|"Images"| INC
    AR -.->|"Image"| DQ
    SA -.->|"Workload identity"| FULL
    SA -.->|"Workload identity"| INC
    SA -.->|"Workload identity"| DQ

    FULL -.-> LOG
    INC -.-> LOG
    DQ -.-> LOG
    INC -.-> MON
    DQ -.-> MON

    USERS["Analysts / dashboards"] --> ANALYTICS
```

## Architecture Overview

Cloud SQL PostgreSQL is the operational source for the ecommerce `products`, `customers`, and `orders` data. Data generation scripts seed the initial dataset and can add daily customers and orders. The pipeline stages extracts as Parquet in a Cloud Storage raw bucket before loading them into the `ecommerce_dwh_dev` BigQuery dataset.

### Data Flows

- **Initial full load:** Run `full-load/full_load.py` locally to extract the three source tables, stage Parquet files in GCS, and load BigQuery tables with `WRITE_TRUNCATE`.
- **Incremental load:** Cloud Scheduler starts the `etl-incremental-load` Cloud Run Job daily at 01:00 Asia/Ho_Chi_Minh. The job reads orders newer than the stored `updated_at` watermark, stages them in GCS, appends them to the BigQuery `orders` table, and advances the watermark in `/_metadata/watermarks.json`.
- **Data quality:** Cloud Scheduler starts `etl-data-quality` daily at 03:00 Asia/Ho_Chi_Minh. It checks destination freshness, volume, nulls, duplicates, amount validity, and order status validity. Critical failures cause the job to fail.
- **Analytics:** The `orders_latest` view selects the latest version of each order. The `daily_revenue`, `customer_lifetime_value`, and `product_performance` views provide the reporting layer for analysts and dashboards.

### Runtime and Access

The incremental load and data quality jobs run as Cloud Run Jobs using images stored in Artifact Registry. The `etl-pipeline-sa` service account grants workloads access to Cloud SQL, Cloud Storage, BigQuery, and Secret Manager for the database password. Local scripts use the configured service account credentials during development.

### Observability

Cloud Run job output is available in Cloud Logging. Cloud Monitoring watches job execution failures and sends notifications through the configured email channel. Data quality check results are reported by the quality job; a critical check failure surfaces as a failed Cloud Run execution and can trigger the failure alert.
