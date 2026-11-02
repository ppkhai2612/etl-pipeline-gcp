"""Load generated CSV data into Cloud SQL PostgreSQL.

This is a one-time database seeding script — not part of the ETL pipeline.
"""

import os
import sys
from pathlib import Path
from datetime import datetime

import pandas as pd
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Load .env from project root
load_dotenv(Path(__file__).parent.parent / ".env")

DB_URL = (
    f"postgresql+psycopg2://{os.environ['POSTGRES_USER']}:{os.environ['POSTGRES_PASSWORD']}"
    f"@{os.environ['POSTGRES_HOST']}:{os.environ.get('POSTGRES_PORT', 5432)}"
    f"/{os.environ['POSTGRES_DB']}"
)

CREATE_TABLES_SQL = """
CREATE TABLE IF NOT EXISTS products (
    product_id    SERIAL PRIMARY KEY,
    name          VARCHAR(255) NOT NULL,
    category      VARCHAR(100),
    subcategory   VARCHAR(100),
    brand         VARCHAR(100),
    sku           VARCHAR(50) UNIQUE NOT NULL,
    price         NUMERIC(10, 2),
    cost          NUMERIC(10, 2),
    weight_kg     NUMERIC(6, 2),
    is_active     BOOLEAN DEFAULT TRUE,
    created_at    DATE
);

CREATE TABLE IF NOT EXISTS customers (
    customer_id       SERIAL PRIMARY KEY,
    first_name        VARCHAR(100),
    last_name         VARCHAR(100),
    email             VARCHAR(255) UNIQUE NOT NULL,
    country           VARCHAR(100),
    country_code      CHAR(2),
    city              VARCHAR(100),
    segment           VARCHAR(50),
    registration_date DATE,
    is_active         BOOLEAN DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS orders (
    order_id        SERIAL PRIMARY KEY,
    customer_id     INTEGER REFERENCES customers(customer_id),
    product_id      INTEGER REFERENCES products(product_id),
    order_date      DATE NOT NULL,
    order_timestamp TIMESTAMP NOT NULL,
    quantity        SMALLINT,
    unit_price      NUMERIC(10, 2),
    discount_amount NUMERIC(10, 2),
    tax_amount      NUMERIC(10, 2),
    shipping_cost   NUMERIC(10, 2),
    total_amount    NUMERIC(10, 2),
    order_status    VARCHAR(50),
    payment_method  VARCHAR(50),
    created_at      TIMESTAMP,
    updated_at      TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_orders_order_date   ON orders(order_date);
CREATE INDEX IF NOT EXISTS idx_orders_customer_id  ON orders(customer_id);
CREATE INDEX IF NOT EXISTS idx_orders_updated_at   ON orders(updated_at);
"""

# Target schema columns (must match CREATE_TABLES_SQL)
PRODUCTS_COLUMNS = [
    "product_id",
    "name",
    "category",
    "subcategory",
    "brand",
    "sku",
    "price",
    "cost",
    "weight_kg",
    "is_active",
    "created_at",
]
CUSTOMERS_COLUMNS = [
    "customer_id",
    "first_name",
    "last_name",
    "email",
    "country",
    "country_code",
    "city",
    "segment",
    "registration_date",
    "is_active",
]
ORDERS_COLUMNS = [
    "order_id",
    "customer_id",
    "product_id",
    "order_date",
    "order_timestamp",
    "quantity",
    "unit_price",
    "discount_amount",
    "tax_amount",
    "shipping_cost",
    "total_amount",
    "order_status",
    "payment_method",
    "created_at",
    "updated_at",
]

# Map CSV column names → schema column names (only where they differ)
PRODUCTS_RENAME = {
    "product_name": "name",
    "unit_price": "price",
    "cost_price": "cost",
    "release_date": "created_at",
}
CUSTOMERS_RENAME = {
    "customer_segment": "segment",
}
ORDERS_RENAME: dict = {}  # orders CSV columns already match the schema


def load_csv_to_table(
    engine,
    csv_path: Path,
    table_name: str,
    columns: list,
    rename: dict | None = None,
    chunksize: int = 500,
):
    df = pd.read_csv(csv_path)
    # Rename CSV columns to match our schema before filtering
    if rename:
        df = df.rename(columns=rename)
    # Keep only columns defined in our schema
    df = df[[c for c in columns if c in df.columns]]
    total = len(df)
    print(f"  Loading {total:,} rows into {table_name}...")
    t = datetime.now()
    df.to_sql(
        table_name,
        engine,
        if_exists="append",
        index=False,
        chunksize=chunksize,
        method="multi",
    )
    elapsed = (datetime.now() - t).total_seconds()
    print(f"  ✅ {total:,} rows loaded in {elapsed:.1f}s")


def main():
    print("=" * 60)
    print("PostgreSQL Database Seeder")
    print("=" * 60)

    engine = create_engine(DB_URL)

    # Create schema
    print("Creating tables...")
    with engine.connect() as conn:
        conn.execute(text(CREATE_TABLES_SQL))
        conn.commit()
    print("  ✅ Tables created")
    print()

    data_path = Path(__file__).parent / "output" / "historical"

    if not data_path.exists():
        print("ERROR: No CSV files found. Run generate_historical.py first.")
        sys.exit(1)

    def find_csv(prefix: str) -> Path:
        matches = sorted(data_path.glob(f"{prefix}*.csv"))
        if not matches:
            print(f"ERROR: No file matching '{prefix}*.csv' in {data_path}")
            sys.exit(1)
        return matches[-1]  # pick the latest if multiple exist

    load_csv_to_table(
        engine,
        find_csv("products_full_load"),
        "products",
        PRODUCTS_COLUMNS,
        PRODUCTS_RENAME,
    )
    load_csv_to_table(
        engine,
        find_csv("customers_full_load"),
        "customers",
        CUSTOMERS_COLUMNS,
        CUSTOMERS_RENAME,
    )
    load_csv_to_table(
        engine,
        find_csv("orders_full_load"),
        "orders",
        ORDERS_COLUMNS,
        ORDERS_RENAME,
    )

    print()
    print("Database seeded successfully!")
    print(f"Connection: {os.environ['POSTGRES_HOST']}/{os.environ['POSTGRES_DB']}")


if __name__ == "__main__":
    main()