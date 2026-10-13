-- q04_repeat_purchase_rate.sql
-- Query 4: Overall repeat-purchase rate
-- Customer Grain: Uses customer_unique_id (the persistent human identifier across orders)
-- rather than customer_id (which is a per-order surrogate).
-- Eligible orders: Non-canceled orders (order_status <> 'canceled') representing valid customer intent.
-- Observation period: Sep 2016 – Aug 2018 (purchase_timestamp >= '2016-09-01' AND < '2018-09-01').
-- Denominator: Count of distinct customer_unique_id values with at least 1 eligible order.
-- Numerator: Count of distinct customer_unique_id values with at least 2 eligible orders.

WITH eligible_orders AS (
    SELECT
        customer_unique_id,
        order_id
    FROM analytics.orders_mart
    WHERE order_status <> 'canceled'
      AND customer_unique_id IS NOT NULL
      AND purchase_timestamp >= '2016-09-01'
      AND purchase_timestamp < '2018-09-01'
),
customer_order_counts AS (
    SELECT
        customer_unique_id,
        COUNT(DISTINCT order_id) AS order_count
    FROM eligible_orders
    GROUP BY customer_unique_id
),
summary AS (
    SELECT
        COUNT(*) AS total_customers,
        COUNT(*) FILTER (WHERE order_count >= 2) AS repeat_customers,
        ROUND(
            100.0 * COUNT(*) FILTER (WHERE order_count >= 2) / NULLIF(COUNT(*), 0),
            2
        ) AS repeat_purchase_rate_pct
    FROM customer_order_counts
)
SELECT
    total_customers,
    repeat_customers,
    repeat_purchase_rate_pct,
    'Observation: Sep 2016 - Aug 2018 | Excludes canceled orders | Customer grain: customer_unique_id' AS methodology_note
FROM summary
;
