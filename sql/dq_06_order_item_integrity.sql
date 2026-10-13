-- dq_06_order_item_integrity.sql
-- Check: Order items in raw.raw_order_items referencing missing orders or non-positive price/freight
-- Severity: SOFT (EXCEPTION).
-- Business Reason: Detect orphaned line items or invalid financial values in raw line items.

WITH orphaned_items AS (
    SELECT oi.order_id
    FROM raw.raw_order_items oi
    LEFT JOIN raw.raw_orders o ON oi.order_id = o.order_id
    WHERE o.order_id IS NULL
),
invalid_prices AS (
    SELECT order_id
    FROM raw.raw_order_items
    WHERE price::NUMERIC <= 0
       OR freight_value::NUMERIC < 0
),
combined AS (
    SELECT order_id FROM orphaned_items
    UNION ALL
    SELECT order_id FROM invalid_prices
)
SELECT
    COUNT(*) AS failing_rows,
    (
        SELECT STRING_AGG(order_id, ', ')
        FROM (SELECT order_id FROM combined LIMIT 5) top5
    ) AS sample_ids
FROM combined
;
