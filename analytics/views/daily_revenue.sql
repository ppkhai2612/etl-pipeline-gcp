-- View: daily_revenue
-- Purpose: Daily revenue and order metrics for trend analysis and dashboards.
--
-- Source: ecommerce_dwh_dev.orders_latest (one row per order_id, latest state)
-- Refresh: On every query (regular view — BigQuery recomputes on access)
--
-- Usage:
--   SELECT * FROM `ecommerce_dwh_dev.daily_revenue`
--   WHERE order_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
--   ORDER BY order_date DESC;

CREATE OR REPLACE VIEW `ecommerce_dwh_dev.daily_revenue` AS
SELECT
    order_date,

    -- Volume
    COUNT(DISTINCT order_id)    AS total_orders,
    COUNT(DISTINCT customer_id) AS unique_customers,
    SUM(quantity)               AS total_items_sold,

    -- Revenue
    ROUND(SUM(total_amount), 2)          AS gross_revenue,
    ROUND(SUM(discount_amount), 2)       AS total_discounts,
    ROUND(SUM(tax_amount), 2)            AS total_tax,
    ROUND(SUM(shipping_cost), 2)         AS total_shipping,
    ROUND(SUM(total_amount
        - discount_amount
        - tax_amount
        - shipping_cost), 2)             AS net_revenue,

    -- Averages
    ROUND(AVG(total_amount), 2)          AS avg_order_value,
    ROUND(AVG(quantity), 2)              AS avg_items_per_order,

    -- Status breakdown
    COUNTIF(order_status = 'completed')  AS orders_completed,
    COUNTIF(order_status = 'pending')    AS orders_pending,
    COUNTIF(order_status = 'shipped')    AS orders_shipped,
    COUNTIF(order_status = 'cancelled')  AS orders_cancelled,
    ROUND(
        SAFE_DIVIDE(
            COUNTIF(order_status = 'cancelled'),
            COUNT(*)
        ) * 100, 2
    )                                    AS cancellation_rate_pct

FROM `ecommerce_dwh_dev.orders_latest`
GROUP BY order_date
ORDER BY order_date DESC;