-- q05_delivery_delay_reviews.sql
-- Query 5: Delivery delay versus review score relationship
-- Delivery delay sign convention:
--   positive (+) = Delivered after estimated delivery date (LATE)
--   negative (-) = Delivered on or before estimated delivery date (EARLY)
-- Scope: Delivered orders with both delivery and review timestamps.
-- Grouping: Rounded integer review scores (1 to 5 stars).
-- Outputs: order_count, avg_delay_days, late_pct (% of orders delivered late),
--          min_delay_days, max_delay_days.

SELECT
    ROUND(review_score)::INT AS review_score,
    COUNT(*) AS order_count,
    ROUND(AVG(delivery_delay_days), 2) AS avg_delay_days,
    ROUND(
        100.0 * COUNT(*) FILTER (WHERE delivered_on_time_flag = 0)
        / NULLIF(COUNT(*), 0),
        2
    ) AS late_pct,
    ROUND(MIN(delivery_delay_days), 2) AS min_delay_days,
    ROUND(MAX(delivery_delay_days), 2) AS max_delay_days
FROM analytics.orders_mart
WHERE order_status = 'delivered'
  AND delivery_delay_days IS NOT NULL
  AND review_score IS NOT NULL
GROUP BY 1
ORDER BY 1
;
