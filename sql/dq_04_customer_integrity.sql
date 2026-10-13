-- dq_04_customer_integrity.sql
-- Check: Orders in raw.raw_orders referencing customer_ids not present in raw.raw_customers
-- Severity: HARD FAIL.
-- Business Reason: Referential integrity. Orders without a customer cannot be mapped to geography or unique human cohorts.

WITH orphaned AS (
    SELECT
        o.order_id
    FROM raw.raw_orders o
    LEFT JOIN raw.raw_customers c ON o.customer_id = c.customer_id
    WHERE c.customer_id IS NULL
)
SELECT
    COUNT(*) AS failing_rows,
    (
        SELECT STRING_AGG(order_id, ', ')
        FROM (SELECT order_id FROM orphaned LIMIT 5) top5
    ) AS sample_ids
FROM orphaned
;
