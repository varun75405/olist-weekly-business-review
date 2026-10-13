-- q01_monthly_revenue.sql
-- Query 1: Month-over-month revenue and growth using a complete calendar month series.
-- Revenue definition: order_revenue = item_total + freight_total from orders_mart.
-- Filters: Delivered orders only (order_status = 'delivered') to represent realized revenue.
-- Calendar series: generate_series() ensures every calendar month is present so LAG()
-- always compares strictly adjacent consecutive calendar months.
-- Division by zero: Handled via NULLIF on LAG(monthly_revenue).

WITH date_bounds AS (
    SELECT
        DATE_TRUNC('month', MIN(purchase_timestamp))::DATE AS min_month,
        DATE_TRUNC('month', MAX(purchase_timestamp))::DATE AS max_month
    FROM analytics.orders_mart
    WHERE order_status = 'delivered'
      AND purchase_timestamp IS NOT NULL
),
calendar_months AS (
    SELECT generate_series(
        (SELECT min_month FROM date_bounds),
        (SELECT max_month FROM date_bounds),
        INTERVAL '1 month'
    )::DATE AS month
),
monthly_rev AS (
    SELECT
        DATE_TRUNC('month', purchase_timestamp)::DATE AS month,
        SUM(order_revenue) AS monthly_revenue,
        COUNT(DISTINCT order_id) AS order_count
    FROM analytics.orders_mart
    WHERE order_status = 'delivered'
      AND purchase_timestamp IS NOT NULL
    GROUP BY 1
),
calendar_revenue AS (
    SELECT
        cm.month,
        COALESCE(mr.monthly_revenue, 0.0) AS monthly_revenue,
        COALESCE(mr.order_count, 0) AS order_count
    FROM calendar_months cm
    LEFT JOIN monthly_rev mr ON cm.month = mr.month
)
SELECT
    month,
    ROUND(monthly_revenue, 2) AS monthly_revenue,
    order_count,
    ROUND(LAG(monthly_revenue) OVER (ORDER BY month), 2) AS prev_revenue,
    ROUND(monthly_revenue - LAG(monthly_revenue) OVER (ORDER BY month), 2) AS revenue_change,
    ROUND(
        100.0 * (monthly_revenue - LAG(monthly_revenue) OVER (ORDER BY month))
        / NULLIF(LAG(monthly_revenue) OVER (ORDER BY month), 0),
        2
    ) AS pct_growth
FROM calendar_revenue
ORDER BY month
;
