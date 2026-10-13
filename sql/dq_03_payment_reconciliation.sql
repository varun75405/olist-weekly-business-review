-- dq_03_payment_reconciliation.sql
-- Check: Payment total vs (item price + freight) reconciliation in raw data
-- Severity: SOFT (DOCUMENTED EXCEPTION).
-- Tolerance: BRL 0.05 threshold (detects 260 orders; tighter BRL 0.01 threshold detects 303 orders).
--
-- Empirical breakdown by payment type (> BRL 0.05):
--   • 246 credit card orders: avg diff +11.81 BRL (range -51.62 to +182.81 BRL)
--   • 7 combined credit card + voucher orders: avg diff +2.50 BRL (range +0.36 to +9.26 BRL)
--   • 7 debit card orders: avg diff -7.42 BRL (range -16.50 to -1.60 BRL)
-- Source records do not separate external fees or discounts into dedicated line items;
-- all records are preserved intact with documented exception status.

WITH item_totals AS (
    SELECT
        order_id,
        SUM(price::NUMERIC + freight_value::NUMERIC) AS expected_total
    FROM raw.raw_order_items
    GROUP BY order_id
),
payment_totals AS (
    SELECT
        order_id,
        SUM(payment_value::NUMERIC) AS total_paid
    FROM raw.raw_payments
    GROUP BY order_id
),
discrepancies AS (
    SELECT
        pt.order_id,
        pt.total_paid,
        it.expected_total,
        ABS(pt.total_paid - it.expected_total) AS diff
    FROM payment_totals pt
    JOIN item_totals it ON pt.order_id = it.order_id
    WHERE ABS(pt.total_paid - it.expected_total) > 0.05
)
SELECT
    COUNT(*) AS failing_rows,
    (
        SELECT STRING_AGG(order_id, ', ')
        FROM (SELECT order_id FROM discrepancies ORDER BY diff DESC LIMIT 5) top5
    ) AS sample_ids
FROM discrepancies
;
