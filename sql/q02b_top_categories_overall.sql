-- q02b_top_categories_overall.sql
-- Dedicated Query for Chart 2: Total delivered revenue by product category across all states
-- Revenue definition: Line revenue = price + freight_value for delivered orders.
-- Fan-out prevention: Aggregated directly over staging.order_items mapped to delivered orders.
-- Product translation: Maps Portuguese names to English via category translation; falls back to raw or 'uncategorized'.

WITH order_item_revenue AS (
    SELECT
        o.order_id,
        oi.product_id,
        oi.price + oi.freight_value AS line_revenue
    FROM staging.orders o
    JOIN staging.order_items oi ON o.order_id = oi.order_id
    WHERE o.order_status = 'delivered'
),
product_categories AS (
    SELECT
        p.product_id,
        COALESCE(ct.category_english, p.product_category_name, 'uncategorized') AS category_english
    FROM staging.products p
    LEFT JOIN staging.category_translation ct ON p.product_category_name = ct.product_category_name
)
SELECT
    pc.category_english,
    ROUND(SUM(oir.line_revenue), 2) AS revenue,
    COUNT(DISTINCT oir.order_id) AS order_count
FROM order_item_revenue oir
JOIN product_categories pc ON oir.product_id = pc.product_id
GROUP BY pc.category_english
ORDER BY revenue DESC
LIMIT 15;
