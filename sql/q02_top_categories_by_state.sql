-- q02_top_categories_by_state.sql
-- Query 2: Top 3 product categories by revenue in each customer state
-- Revenue definition: Line revenue = price + freight_value for delivered orders.
-- Fan-out prevention: Aggregation occurs over order items mapped to orders and customer states.
-- DENSE_RANK() is partitioned by customer_state ordered by total category revenue DESC.
-- Ties: If categories tie in revenue, DENSE_RANK assigns the same rank (which may return >3 rows for that state).
-- Product translation: Maps Portuguese names to English via category translation; falls back to raw or 'uncategorized'.

WITH order_item_revenue AS (
    SELECT
        o.order_id,
        c.customer_state,
        oi.product_id,
        oi.price + oi.freight_value AS line_revenue
    FROM staging.orders o
    JOIN staging.customers c ON o.customer_id = c.customer_id
    JOIN staging.order_items oi ON o.order_id = oi.order_id
    WHERE o.order_status = 'delivered'
),
product_categories AS (
    SELECT
        p.product_id,
        COALESCE(ct.category_english, p.product_category_name, 'uncategorized') AS category_english
    FROM staging.products p
    LEFT JOIN staging.category_translation ct ON p.product_category_name = ct.product_category_name
),
state_category_rev AS (
    SELECT
        oir.customer_state,
        pc.category_english,
        SUM(oir.line_revenue) AS revenue,
        COUNT(DISTINCT oir.order_id) AS order_count
    FROM order_item_revenue oir
    JOIN product_categories pc ON oir.product_id = pc.product_id
    GROUP BY oir.customer_state, pc.category_english
),
ranked AS (
    SELECT
        customer_state,
        category_english,
        ROUND(revenue, 2) AS revenue,
        order_count,
        DENSE_RANK() OVER (PARTITION BY customer_state ORDER BY revenue DESC) AS revenue_rank
    FROM state_category_rev
)
SELECT
    customer_state,
    category_english,
    revenue,
    order_count,
    revenue_rank
FROM ranked
WHERE revenue_rank <= 3
ORDER BY customer_state, revenue_rank, revenue DESC
;
