-- dq_01_order_id.sql
-- Check: Null or duplicate order IDs in raw.raw_orders
-- Severity: HARD FAIL.
-- Business Reason: Primary key integrity. An order ID must be unique and non-null to prevent mart join corruption.

WITH duplicates AS (
    SELECT
        order_id,
        COUNT(*) AS cnt
    FROM raw.raw_orders
    GROUP BY order_id
    HAVING COUNT(*) > 1 OR order_id IS NULL
)
SELECT
    COUNT(*) AS failing_rows,
    (
        SELECT STRING_AGG(COALESCE(order_id, 'NULL'), ', ')
        FROM (SELECT order_id FROM duplicates LIMIT 5) top5
    ) AS sample_ids
FROM duplicates
;
