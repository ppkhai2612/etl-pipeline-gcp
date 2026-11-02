#!/bin/bash
# One-time database seeding script.
# Generates synthetic e-commerce data and loads it into PostgreSQL.
#
# Usage: ./data-generation/seed_database.sh
# Requires: .env file in project root with POSTGRES_* variables set

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Load environment variables from project root
if [ -f "$PROJECT_ROOT/.env" ]; then
    set -a
    source <(grep -v '^\s*#' "$PROJECT_ROOT/.env" | grep -v '^\s*$')
    set +a
else
    echo "ERROR: .env file not found at $PROJECT_ROOT/.env"
    echo "Copy .env.example to .env and fill in your values."
    exit 1
fi

echo "========================================"
echo "  Database Seeding — Starting"
echo "========================================"
echo ""

# Step 1: Generate CSV files (skip if any existing files are found)
DATA_DIR="$SCRIPT_DIR/output/historical"

cd "$SCRIPT_DIR"

PRODUCTS_CSV=$(ls "$DATA_DIR"/products_full_load_*.csv 2>/dev/null | sort | tail -1)
CUSTOMERS_CSV=$(ls "$DATA_DIR"/customers_full_load_*.csv 2>/dev/null | sort | tail -1)
ORDERS_CSV=$(ls "$DATA_DIR"/orders_full_load_*.csv 2>/dev/null | sort | tail -1)

if [ -n "$PRODUCTS_CSV" ] && [ -n "$CUSTOMERS_CSV" ] && [ -n "$ORDERS_CSV" ]; then
    echo "Step 1/2: CSV files already exist — skipping generation."
    echo "  $(basename "$PRODUCTS_CSV")"
    echo "  $(basename "$CUSTOMERS_CSV")"
    echo "  $(basename "$ORDERS_CSV")"
else
    echo "Step 1/2: Generating synthetic data..."
    python generate_historical.py
fi

echo ""

# Step 2: Load into PostgreSQL
echo "Step 2/2: Loading into PostgreSQL..."
python load_to_postgres.py

echo ""
echo "========================================"
echo "  Seeding complete!"
echo "========================================"