-- q03_rolling_orders.sql
-- Query 3: Seven-day rolling average of daily order count
-- Uses generate_series() calendar series to ensure zero-order dates are explicitly included,
-- guaranteeing that the rolling window represents exactly 7 calendar days.
-- Incomplete periods: The first 6 days of the dataset average across available preceding days
-- in the window (ROWS BETWEEN 6 PRECEDING AND CURRENT ROW).
-- Order scope: All orders with purchase_timestamp to measure total marketplace demand volume.

WITH date_range AS (
    SELECT
        MIN(purchase_timestamp::DATE) AS min_date,
        MAX(purchase_timestamp::DATE) AS max_date
    FROM analytics.orders_mart
    WHERE purchase_timestamp IS NOT NULL
),
calendar AS (
    SELECT generate_series(
        (SELECT min_date FROM date_range),
        (SELECT max_date FROM date_range),
        INTERVAL '1 day'
    )::DATE AS order_date
),
daily_counts AS (
    SELECT
        purchase_timestamp::DATE AS order_date,
        COUNT(DISTINCT order_id) AS daily_order_count
    FROM analytics.orders_mart
    WHERE purchase_timestamp IS NOT NULL
    GROUP BY 1
),
calendar_with_counts AS (
    SELECT
        c.order_date,
        COALESCE(d.daily_order_count, 0) AS daily_order_count
    FROM calendar c
    LEFT JOIN daily_counts d ON c.order_date = d.order_date
)
SELECT
    order_date,
    daily_order_count,
    ROUND(
        AVG(daily_order_count) OVER (
            ORDER BY order_date
            ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
        ),
        2
    ) AS rolling_7day_avg
FROM calendar_with_counts
ORDER BY order_date
;
