-- mart.sql
-- Builds the order-level analytics mart.
-- Grain: exactly one row per order_id.
--
-- Revenue definition:
--   item_total     = SUM(price) across all items for the order
--   freight_total  = SUM(freight_value) across all items for the order
--   order_revenue  = item_total + freight_total
--   payment_total  = SUM(payment_value) across all payment rows for the order
--
-- Fan-out prevention:
--   order_items and payments are each aggregated BEFORE joining to orders.
--   reviews are aggregated (AVG score + COUNT) before joining.
--   This ensures no row multiplication.
--
-- Cancelled/unavailable handling:
--   delivered_customer_timestamp may be NULL for non-delivered orders.
--   delivery_delay_days and delivered_on_time_flag are NULL for such orders.
--   review_score is NULL when no valid review exists.

SET search_path TO analytics, staging, public;

DROP TABLE IF EXISTS analytics.orders_mart CASCADE;

CREATE TABLE analytics.orders_mart AS
WITH
-- Step 1: Aggregate items to order level (prevents fan-out on join)
item_agg AS (
    SELECT
        order_id,
        SUM(price)          AS item_total,
        SUM(freight_value)  AS freight_total,
        COUNT(*)            AS item_count
    FROM staging.order_items
    GROUP BY order_id
),

-- Step 2: Aggregate payments to order level
payment_agg AS (
    SELECT
        order_id,
        SUM(payment_value)  AS payment_total,
        COUNT(*)            AS payment_count,
        STRING_AGG(DISTINCT payment_type, ', ' ORDER BY payment_type) AS payment_types
    FROM staging.payments
    GROUP BY order_id
),

-- Step 3: Aggregate reviews to order level
-- Treatment: When multiple reviews exist per order, use AVG score and latest review.
-- Business reason: multiple reviews are a data artifact; AVG is most representative.
review_agg AS (
    SELECT
        order_id,
        ROUND(AVG(review_score), 2)  AS review_score,
        COUNT(*)                      AS review_count
    FROM staging.reviews
    GROUP BY order_id
)

SELECT
    o.order_id,
    o.customer_id,
    c.customer_unique_id,
    c.customer_state,
    o.order_status,
    o.purchase_timestamp,
    o.approved_timestamp,
    o.delivered_carrier_timestamp,
    o.delivered_customer_timestamp,
    o.estimated_delivery_timestamp,

    -- Revenue fields
    COALESCE(ia.item_total, 0)     AS item_total,
    COALESCE(ia.freight_total, 0)  AS freight_total,
    COALESCE(ia.item_total, 0) + COALESCE(ia.freight_total, 0) AS order_revenue,
    COALESCE(pa.payment_total, 0)  AS payment_total,

    ia.item_count,
    pa.payment_count,
    pa.payment_types,

    -- Review
    ra.review_score,
    ra.review_count,

    -- Delivery delay: positive = late, negative = early delivery
    -- Only computed for orders with actual delivery timestamps
    CASE
        WHEN o.delivered_customer_timestamp IS NOT NULL
         AND o.estimated_delivery_timestamp IS NOT NULL
        THEN EXTRACT(EPOCH FROM (
             o.delivered_customer_timestamp - o.estimated_delivery_timestamp
        )) / 86400.0
        ELSE NULL
    END AS delivery_delay_days,

    -- On-time flag: 1 = delivered on or before estimated date, 0 = late
    -- NULL for non-delivered orders
    CASE
        WHEN o.delivered_customer_timestamp IS NOT NULL
         AND o.estimated_delivery_timestamp IS NOT NULL
        THEN CASE WHEN o.delivered_customer_timestamp <= o.estimated_delivery_timestamp
                  THEN 1 ELSE 0 END
        ELSE NULL
    END AS delivered_on_time_flag

FROM staging.orders o
LEFT JOIN staging.customers c
    ON o.customer_id = c.customer_id
LEFT JOIN item_agg ia
    ON o.order_id = ia.order_id
LEFT JOIN payment_agg pa
    ON o.order_id = pa.order_id
LEFT JOIN review_agg ra
    ON o.order_id = ra.order_id;

-- Enforce one row per order
ALTER TABLE analytics.orders_mart ADD PRIMARY KEY (order_id);
CREATE INDEX ON analytics.orders_mart (customer_unique_id);
CREATE INDEX ON analytics.orders_mart (order_status);
CREATE INDEX ON analytics.orders_mart (purchase_timestamp);
