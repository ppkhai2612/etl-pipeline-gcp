-- View: customer_lifetime_value
-- Purpose: One row per customer — lifetime spend, order history, value tier,
--          and activity status. Used for segmentation and retention analysis.
--
-- Sources:
--   ecommerce_dwh_dev.customers      (registration data)
--   ecommerce_dwh_dev.orders_latest  (one row per order_id, latest state)
--
-- Usage:
--   SELECT * FROM `ecommerce_dwh_dev.customer_lifetime_value`
--   WHERE customer_status = 'Active'
--   ORDER BY lifetime_value DESC
--   LIMIT 100;

CREATE OR REPLACE VIEW `ecommerce_dwh_dev.customer_lifetime_value` AS
SELECT
    c.customer_id,
    CONCAT(c.first_name, ' ', c.last_name) AS customer_name,
    c.email,
    c.segment                              AS acquisition_segment,
    c.registration_date,
    c.city,
    c.country,

    -- Order history
    COUNT(o.order_id)                      AS total_orders,
    COALESCE(SUM(o.quantity), 0)           AS total_items_purchased,
    MIN(o.order_date)                      AS first_order_date,
    MAX(o.order_date)                      AS last_order_date,

    -- Value metrics
    ROUND(COALESCE(SUM(o.total_amount), 0), 2)  AS lifetime_value,
    ROUND(COALESCE(AVG(o.total_amount), 0), 2)  AS avg_order_value,

    -- Tenure (days from first to last order; 0 for single-order customers)
    DATE_DIFF(
        COALESCE(MAX(o.order_date), c.registration_date),
        COALESCE(MIN(o.order_date), c.registration_date),
        DAY
    )                                      AS customer_tenure_days,

    -- Recency
    DATE_DIFF(
        CURRENT_DATE(),
        COALESCE(MAX(o.order_date), c.registration_date),
        DAY
    )                                      AS days_since_last_order,

    -- Value tier
    CASE
        WHEN COALESCE(SUM(o.total_amount), 0) >= 10000 THEN 'VIP'
        WHEN COALESCE(SUM(o.total_amount), 0) >=  5000 THEN 'High Value'
        WHEN COALESCE(SUM(o.total_amount), 0) >=  1000 THEN 'Mid Value'
        ELSE                                                  'Low Value'
    END                                    AS value_tier,

    -- Activity status
    CASE
        WHEN DATE_DIFF(CURRENT_DATE(),
            COALESCE(MAX(o.order_date), c.registration_date), DAY) <= 30
        THEN 'Active'
        WHEN DATE_DIFF(CURRENT_DATE(),
            COALESCE(MAX(o.order_date), c.registration_date), DAY) <= 90
        THEN 'At Risk'
        ELSE 'Churned'
    END                                    AS customer_status

FROM `ecommerce_dwh_dev.customers` c
LEFT JOIN `ecommerce_dwh_dev.orders_latest` o
    ON c.customer_id = o.customer_id
    AND o.order_status != 'cancelled'      -- exclude cancelled orders from LTV
GROUP BY
    c.customer_id, c.first_name, c.last_name, c.email,
    c.segment, c.registration_date, c.city, c.country;