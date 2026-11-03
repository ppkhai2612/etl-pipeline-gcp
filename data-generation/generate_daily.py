"""Daily Data Generator

Insert new orders and customers into PostgreSQL. 

Simulates one day of new e-commerce activity. Run this before the
incremental load pipeline to create data for it to pick up.

Usage:
    python data-generation/generate_daily.py              # uses today's date
    python data-generation/generate_daily.py 2026-03-01   # specific date
"""

import os
import sys
import random
from pathlib import Path
from datetime import datetime, date

import pandas as pd
from faker import Faker
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

DB_URL = (
    f"postgresql+psycopg2://{os.environ['POSTGRES_USER']}:{os.environ['POSTGRES_PASSWORD']}"
    f"@{os.environ['POSTGRES_HOST']}:{os.environ.get('POSTGRES_PORT', 5432)}"
    f"/{os.environ['POSTGRES_DB']}"
)

DAILY_NEW_CUSTOMERS = 20
DAILY_NEW_ORDERS = 100

ORDER_STATUSES = ["completed", "pending", "shipped", "cancelled"]
PAYMENT_METHODS = ["credit_card", "debit_card", "paypal", "bank_transfer"]

fake = Faker("en_GB")


def next_id(conn, table: str, id_col: str) -> int:
    row = conn.execute(
        text(f"SELECT COALESCE(MAX({id_col}), 0) FROM {table}")
    ).fetchone()
    return row[0] + 1


def gen_customers(conn, run_date: date, count: int) -> pd.DataFrame:
    start_id = next_id(conn, "customers", "customer_id")
    rows = []
    for i in range(count):
        rows.append(
            {
                "customer_id": start_id + i,
                "first_name": fake.first_name(),
                "last_name": fake.last_name(),
                "email": fake.unique.email(),
                "country": "United Kingdom",
                "country_code": "GB",
                "city": fake.city(),
                "segment": random.choice(["Bronze", "Silver", "Gold", "Platinum"]),
                "registration_date": run_date,
                "is_active": True,
            }
        )
    return pd.DataFrame(rows)


def gen_orders(conn, run_date: date, count: int) -> pd.DataFrame:
    start_id = next_id(conn, "orders", "order_id")
    max_cust = conn.execute(text("SELECT MAX(customer_id) FROM customers")).fetchone()[0]
    max_prod = conn.execute(text("SELECT MAX(product_id) FROM products")).fetchone()[0]

    # Wall-clock time of insertion — this is what the watermark compares against.
    # order_timestamp carries the synthetic "business" time for the day.
    insert_time = datetime.now()

    rows = []
    for i in range(count):
        qty = random.randint(1, 5)
        unit_price = round(random.uniform(5, 500), 2)
        discount = round(random.uniform(0, unit_price * 0.2), 2)
        tax = round((unit_price - discount) * qty * 0.2, 2)
        shipping = round(random.uniform(2.99, 12.99), 2)
        total = round((unit_price - discount) * qty + tax + shipping, 2)
        order_ts = datetime(
            run_date.year,
            run_date.month,
            run_date.day,
            random.randint(0, 23),
            random.randint(0, 59),
            random.randint(0, 59),
        )
        rows.append(
            {
                "order_id": start_id + i,
                "customer_id": random.randint(1, max_cust),
                "product_id": random.randint(1, max_prod),
                "order_date": run_date,
                "order_timestamp": order_ts,
                "quantity": qty,
                "unit_price": unit_price,
                "discount_amount": discount,
                "tax_amount": tax,
                "shipping_cost": shipping,
                "total_amount": total,
                "order_status": random.choice(ORDER_STATUSES),
                "payment_method": random.choice(PAYMENT_METHODS),
                "created_at": insert_time,
                "updated_at": insert_time,
            }
        )
    return pd.DataFrame(rows)


def main():
    run_date_str = sys.argv[1] if len(sys.argv) > 1 else date.today().isoformat()
    run_date = date.fromisoformat(run_date_str)

    print("=" * 60)
    print("Daily Data Generator")
    print(f"Date : {run_date}")
    print("=" * 60)

    engine = create_engine(DB_URL)

    with engine.begin() as conn:
        # Customers first so new orders can reference them
        customers_df = gen_customers(conn, run_date, DAILY_NEW_CUSTOMERS)
        customers_df.to_sql(
            "customers", conn, if_exists="append", index=False, method="multi"
        )
        print(f"  ✅ Inserted {len(customers_df)} new customers")

        orders_df = gen_orders(conn, run_date, DAILY_NEW_ORDERS)
        orders_df.to_sql(
            "orders", conn, if_exists="append", index=False, method="multi"
        )
        print(f"  ✅ Inserted {len(orders_df)} new orders")

    print()
    print("Done! Run incremental-load/incremental_load.py to move this data to BigQuery.")


if __name__ == "__main__":
    main()