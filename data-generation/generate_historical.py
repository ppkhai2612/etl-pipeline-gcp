"""Historical Data Generator

Generates 1 year of historical e-commerce data (500K orders, 20K customers, 5K products)
"""

import sys
from pathlib import Path
from datetime import datetime

# Add current directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from generators.products import generate_products
from generators.customers import generate_customers
from generators.orders import generate_orders
from utils.config import (
    NUM_CUSTOMERS,
    NUM_ORDERS,
    NUM_PRODUCTS,
    HISTORICAL_START_DATE,
    HISTORICAL_END_DATE,
    RANDOM_SEED,
    CATEGORIES,
    BRANDS,
    PRICE_RANGES,
    COUNTRIES,
    CUSTOMER_SEGMENTS,
    ORDER_STATUSES,
    PAYMENT_METHODS,
    DEVICE_TYPES,
    CURRENCIES,
)


def main():
    """Main execution function"""
    print("=" * 70)
    print("E-Commerce Data Generator - Historical Load")
    print("=" * 70)
    print()

    print("Configuration:")
    print(f"  Products: {NUM_PRODUCTS:,}")
    print(f"  Customers: {NUM_CUSTOMERS:,}")
    print(f"  Orders: {NUM_ORDERS:,}")
    print(f"  Date Range: {HISTORICAL_START_DATE} to {HISTORICAL_END_DATE}")
    print(f"  Random Seed: {RANDOM_SEED}")
    print()

    # Create output directory
    output_path = Path(__file__).parent / "output" / "historical"
    output_path.mkdir(parents=True, exist_ok=True)
    print(f"Output Directory: {output_path}")
    print()

    # Step 1: Generate Products
    print("=" * 70)
    print("Step 1/3: Generating Products...")
    print("=" * 70)
    start_time = datetime.now()
    
    products_df = generate_products(
        num_products=NUM_PRODUCTS,
        categories=CATEGORIES,
        brands=BRANDS,
        price_ranges=PRICE_RANGES,
        seed=RANDOM_SEED,
    )

    # Save to CSV
    products_file = output_path / "products_full_load_20260217.csv"
    products_df.to_csv(products_file, index=False)

    elapsed = (datetime.now() - start_time).total_seconds()
    file_size = products_file.stat().st_size / (1024 * 1024)  # MB

    print(f"✅ Generated {len(products_df):,} products in {elapsed:.2f}s")
    print(f"   Saved to: {products_file.name}")
    print(f"   File size: {file_size:.1f} MB")
    print()

    print("=" * 70)
    print("Step 2/3: Generating Customers...")
    print("=" * 70)
    start_time = datetime.now()

    customers_df = generate_customers(
        num_customers=NUM_CUSTOMERS,
        countries=COUNTRIES,
        segments=CUSTOMER_SEGMENTS,
        seed=RANDOM_SEED,
    )

    # Save to CSV
    customers_file = output_path / "customers_full_load_20260217.csv"
    customers_df.to_csv(customers_file, index=False)

    elapsed = (datetime.now() - start_time).total_seconds()
    file_size = customers_file.stat().st_size / (1024 * 1024)  # MB

    print(f"✅ Generated {len(customers_df):,} customers in {elapsed:.2f}s")
    print(f"   Saved to: {customers_file.name}")
    print(f"   File size: {file_size:.1f} MB")
    print()

    # Step 3: Generate Orders
    print("=" * 70)
    print("Step 3/3: Generating Orders...")
    print("=" * 70)
    start_time = datetime.now()

    orders_df = generate_orders(
        num_orders=NUM_ORDERS,
        customers_df=customers_df,
        products_df=products_df,
        start_date=HISTORICAL_START_DATE,
        end_date=HISTORICAL_END_DATE,
        statuses=ORDER_STATUSES,
        payment_methods=PAYMENT_METHODS,
        device_types=DEVICE_TYPES,
        currencies=CURRENCIES,
        seed=RANDOM_SEED,
    )

    # Save to CSV
    orders_file = output_path / "orders_full_load_20260217.csv"
    orders_df.to_csv(orders_file, index=False)

    elapsed = (datetime.now() - start_time).total_seconds()
    file_size = orders_file.stat().st_size / (1024 * 1024)  # MB

    print(f"✅ Generated {len(orders_df):,} orders in {elapsed:.2f}s")
    print(f"   Saved to: {orders_file.name}")
    print(f"   File size: {file_size:.1f} MB")
    print()

    # Summary
    total_size = (
        products_file.stat().st_size
        + customers_file.stat().st_size
        + orders_file.stat().st_size
    ) / (1024 * 1024)

    print("=" * 70)
    print("Generation Complete!")
    print("=" * 70)
    print()
    print("Generated Files:")
    print(
        f"  1. {products_file.name} ({products_file.stat().st_size / (1024 * 1024):.1f} MB)"
    )
    print(
        f"  2. {customers_file.name} ({customers_file.stat().st_size / (1024 * 1024):.1f} MB)"
    )
    print(
        f"  3. {orders_file.name} ({orders_file.stat().st_size / (1024 * 1024):.1f} MB)"
    )
    print()
    print(f"Total Size: {total_size:.1f} MB")
    print()
    print("Next Steps:")
    print("  1. Review generated CSV files in output/historical/")
    print("  2. Run generate_daily.py for incremental data")
    print("  3. Upload to GCS: gs://etl-pipe-1-raw-dev/historical/")
    print()



if __name__ == "__main__":
    main()