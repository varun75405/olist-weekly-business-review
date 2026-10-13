-- dq_02_delivery_dates.sql
-- Check: Delivery timestamp earlier than purchase timestamp in raw.raw_orders
-- Severity: SOFT (EXCEPTION).
-- Business Reason: Detect temporal sequencing errors where delivery precedes order purchase.

WITH bad_dates AS (
    SELECT
        order_id,
        order_purchase_timestamp,
        order_delivered_customer_date
    FROM raw.raw_orders
    WHERE order_delivered_customer_date IS NOT NULL
      AND order_purchase_timestamp IS NOT NULL
      AND order_delivered_customer_date::TIMESTAMP < order_purchase_timestamp::TIMESTAMP
)
SELECT
    COUNT(*) AS failing_rows,
    (
        SELECT STRING_AGG(order_id, ', ')
        FROM (SELECT order_id FROM bad_dates LIMIT 5) top5
    ) AS sample_ids
FROM bad_dates
;
