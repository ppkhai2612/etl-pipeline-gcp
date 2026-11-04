"""Data Quality Checks

Runs a suite of checks against the orders table in BigQuery after each
incremental load. Exits with code 1 if any CRITICAL check fails, so that
Cloud Run marks the execution as failed and triggers a retry / alert.

Checks:

    [FRESHNESS]   Rows arrived today (within the last 24 hours by updated_at)
    [VOLUME]      Today's incremental batch is within expected bounds
    [NULLS]       No nulls in critical columns
    [DUPLICATES]  orders_latest view has no duplicate order_ids
    [NEGATIVES]   No rows with total_amount <= 0
    [STATUS]      order_status values are all in the allowed set

Usage:
    python data-quality/quality_checks.py
"""

import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from dotenv import load_dotenv
from google.cloud import bigquery

load_dotenv(Path(__file__).parent.parent / ".env")

PROJECT_ID = os.environ["GCP_PROJECT_ID"]
DATASET = "ecommerce_dwh_dev"

VALID_STATUSES = {"completed", "pending", "shipped", "cancelled"}

# How many new rows we expect per incremental run (sanity bounds)
MIN_DAILY_ROWS = 10
MAX_DAILY_ROWS = 10_000


# Check runner
class CheckResult:
    def __init__(self, name: str, passed: bool, severity: str, detail: str):
        self.name = name
        self.passed = passed
        self.severity = severity  # CRITICAL | WARNING
        self.detail = detail

    def __str__(self) -> str:
        icon = "✅" if self.passed else ("❌" if self.severity == "CRITICAL" else "⚠️ ")
        status = "PASS" if self.passed else f"FAIL [{self.severity}]"
        return f"  {icon}  {self.name:<40} {status}  —  {self.detail}" 


def run_checks(bq: bigquery.Client) -> list[CheckResult]:
    results = []

    def query(sql: str):
        return list(bq.query(sql).result())

    table = f"`{PROJECT_ID}.{DATASET}.orders`"
    view_latest = f"`{PROJECT_ID}.{DATASET}.orders_latest`"

    now_utc = datetime.now(timezone.utc)
    cutoff = (now_utc - timedelta(hours=24)).strftime("%Y-%m-%d %H:%M:%S")

    # 1. FRESHNESS — rows updated in the last 24 hours
    rows = query(f"""
        SELECT COUNT(*) AS cnt
        FROM {table}
        WHERE updated_at >= TIMESTAMP('{cutoff}')
    """)
    fresh_count = rows[0].cnt
    results.append(
        CheckResult(
            name="Freshness: rows in last 24h",
            passed=fresh_count >= MIN_DAILY_ROWS,
            severity="CRITICAL",
            detail=f"{fresh_count:,} rows with updated_at >= {cutoff}",
        )
    )

    # 2. VOLUME — today's batch not suspiciously large or empty
    # results.append(
    #     CheckResult(
    #         name="Volume: batch within expected range",
    #         passed=MIN_DAILY_ROWS <= fresh_count <= MAX_DAILY_ROWS,
    #         severity="WARNING",
    #         detail=f"{fresh_count:,} rows  (expected {MIN_DAILY_ROWS}-{MAX_DAILY_ROWS:,})",
    #     )
    # )

    # # 3. NULLS — critical columns must be fully populated
    # critical_cols = [
    #     "order_id",
    #     "customer_id",
    #     "product_id",
    #     "order_date",
    #     "total_amount",
    # ]
    # for col in critical_cols:
    #     rows = query(f"""
    #         SELECT COUNT(*) AS cnt
    #         FROM {table}
    #         WHERE {col} IS NULL
    #     """)
    #     null_count = rows[0].cnt
    #     results.append(
    #         CheckResult(
    #             name=f"Nulls: {col}",
    #             passed=null_count == 0,
    #             severity="CRITICAL",
    #             detail=f"{null_count:,} null rows",
    #         )
    #     )

    # # 4. DUPLICATES — orders_latest must have 1 row per order_id
    # rows = query(f"""
    #     SELECT COUNT(*) AS cnt
    #     FROM (
    #         SELECT order_id, COUNT(*) AS n
    #         FROM {view_latest}
    #         GROUP BY order_id
    #         HAVING n > 1
    #     )
    # """)
    # dup_count = rows[0].cnt
    # results.append(
    #     CheckResult(
    #         name="Duplicates: orders_latest unique order_id",
    #         passed=dup_count == 0,
    #         severity="CRITICAL",
    #         detail=f"{dup_count:,} duplicate order_ids in view",
    #     )
    # )

    # # 5. NEGATIVES — total_amount must be positive
    # rows = query(f"""
    #     SELECT COUNT(*) AS cnt
    #     FROM {table}
    #     WHERE total_amount <= 0
    # """)
    # neg_count = rows[0].cnt
    # results.append(
    #     CheckResult(
    #         name="Negatives: total_amount > 0",
    #         passed=neg_count == 0,
    #         severity="WARNING",
    #         detail=f"{neg_count:,} rows with total_amount <= 0",
    #     )
    # )

    # 6. STATUS VALUES — only known statuses allowed
    rows = query(f"""
        SELECT ARRAY_AGG(DISTINCT order_status) AS statuses
        FROM {table}
    """)
    actual_statuses = set(rows[0].statuses or [])
    bad_statuses = actual_statuses - VALID_STATUSES
    results.append(
        CheckResult(
            name="Validity: order_status values",
            passed=len(bad_statuses) == 0,
            severity="WARNING",
            detail=(
                f"all values valid: {sorted(actual_statuses)}"
                if not bad_statuses
                else f"unexpected values: {sorted(bad_statuses)}"
            ),
        )
    )

    return results


# Main 
def main() -> None:
    run_ts = run_ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    print("=" * 60)
    print("Data Quality Checks")
    print(f"Run     : {run_ts}")
    print(f"Project : {PROJECT_ID}")
    print(f"Dataset : {DATASET}")
    print("=" * 60)

    bq_client = bigquery.Client(project=PROJECT_ID)
    results = run_checks(bq_client)

    print()
    for r in results:
        print(r)

    passed = sum(1 for r in results if r.passed)
    failed = len(results) - passed
    critical = sum(1 for r in results if not r.passed and r.severity == "CRITICAL")

    print()
    print("=" * 60)
    print(
        f"  {passed}/{len(results)} checks passed  |  {failed} failed  |  {critical} critical"
    )
    print("=" * 60)

    if critical > 0:
        print("\n❌  Critical checks failed — pipeline output may be unreliable.")
        sys.exit(1)

    print("\n✅  All critical checks passed.")


if __name__ == "__main__":
    main()