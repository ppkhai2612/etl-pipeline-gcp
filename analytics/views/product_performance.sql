-- View: product_performance
-- Purpose: One row per product — sales volume, revenue, margin, and a
--          performance classification. Used for merchandising decisions.
--
-- Sources:
--   ecommerce_dwh_dev.products       (catalogue data with cost)
--   ecommerce_dwh_dev.orders_latest  (one row per order_id, latest state)
--
-- Usage:
--   SELECT * FROM `ecommerce_dwh_dev.product_performance`
--   ORDER BY total_revenue DESC
--   LIMIT 20;

CREATE OR REPLACE VIEW `ecommerce_dwh_dev.product_performance` AS
SELECT
    p.product_id,
    p.name                                       AS product_name,
    p.category,

    -- Unit economics
    ROUND(p.price, 2)                            AS unit_price,
    ROUND(p.cost, 2)                             AS unit_cost,
    ROUND(p.price - p.cost, 2)                   AS unit_margin,
    ROUND(SAFE_DIVIDE(p.price - p.cost, p.price) * 100, 2)
                                                 AS profit_margin_pct,

    -- Sales volume
    COUNT(DISTINCT o.order_id)                   AS total_orders,
    COALESCE(SUM(o.quantity), 0)                 AS total_units_sold,

    -- Revenue & profit
    ROUND(COALESCE(SUM(o.total_amount), 0), 2)   AS total_revenue,
    ROUND(COALESCE(SUM(o.quantity * p.cost), 0), 2)
                                                 AS total_cost,
    ROUND(COALESCE(
        SUM(o.total_amount) - SUM(o.quantity * p.cost), 0
    ), 2)                                        AS total_profit,

    -- Averages
    ROUND(COALESCE(AVG(o.quantity), 0), 2)       AS avg_units_per_order,

    -- Sale dates
    MIN(o.order_date)                            AS first_sale_date,
    MAX(o.order_date)                            AS last_sale_date,
    DATE_DIFF(CURRENT_DATE(),
        COALESCE(MAX(o.order_date), CURRENT_DATE()), DAY)
                                                 AS days_since_last_sale,

    -- Performance tier
    CASE
        WHEN COALESCE(SUM(o.quantity), 0) >= 1000 THEN 'Best Seller'
        WHEN COALESCE(SUM(o.quantity), 0) >=  500 THEN 'Good Seller'
        WHEN COALESCE(SUM(o.quantity), 0) >=  100 THEN 'Average Seller'
        ELSE                                            'Slow Mover'
    END                                          AS performance_tier

FROM `ecommerce_dwh_dev.products` p
LEFT JOIN `ecommerce_dwh_dev.orders_latest` o
    ON p.product_id = o.product_id
    AND o.order_status != 'cancelled'
GROUP BY
    p.product_id, p.name, p.category, p.price, p.cost;