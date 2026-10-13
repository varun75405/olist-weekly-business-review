-- staging.sql
-- Builds clean staging tables from raw tables.
-- Grain documented per table below.
-- All casts and null handling happen here; raw tables are untouched.

SET search_path TO staging, raw, public;

-- ============================================================
-- staging.orders
-- Grain: one row per order_id
-- ============================================================
DROP TABLE IF EXISTS staging.orders CASCADE;
CREATE TABLE staging.orders AS
SELECT
    order_id,
    customer_id,
    order_status,
    order_purchase_timestamp::TIMESTAMP   AS purchase_timestamp,
    order_approved_at::TIMESTAMP          AS approved_timestamp,
    order_delivered_carrier_date::TIMESTAMP   AS delivered_carrier_timestamp,
    order_delivered_customer_date::TIMESTAMP  AS delivered_customer_timestamp,
    order_estimated_delivery_date::TIMESTAMP  AS estimated_delivery_timestamp
FROM raw.raw_orders
WHERE order_id IS NOT NULL;

ALTER TABLE staging.orders ADD PRIMARY KEY (order_id);
CREATE INDEX ON staging.orders (customer_id);

-- ============================================================
-- staging.customers
-- Grain: one row per customer_id
-- ============================================================
DROP TABLE IF EXISTS staging.customers CASCADE;
CREATE TABLE staging.customers AS
SELECT
    customer_id,
    customer_unique_id,
    customer_zip_code_prefix,
    customer_city,
    customer_state
FROM raw.raw_customers
WHERE customer_id IS NOT NULL;

ALTER TABLE staging.customers ADD PRIMARY KEY (customer_id);

-- ============================================================
-- staging.order_items
-- Grain: one row per (order_id, order_item_id)
-- Revenue definition: price is the item list price, freight_value is shipping cost.
-- item_total = SUM(price) per order; freight_total = SUM(freight_value) per order.
-- ============================================================
DROP TABLE IF EXISTS staging.order_items CASCADE;
CREATE TABLE staging.order_items AS
SELECT
    order_id,
    order_item_id::INT               AS order_item_id,
    product_id,
    seller_id,
    shipping_limit_date::TIMESTAMP   AS shipping_limit_date,
    price::NUMERIC(12,2)             AS price,
    freight_value::NUMERIC(12,2)     AS freight_value
FROM raw.raw_order_items
WHERE order_id IS NOT NULL
  AND price::NUMERIC >= 0
  AND freight_value::NUMERIC >= 0;

CREATE INDEX ON staging.order_items (order_id);
CREATE INDEX ON staging.order_items (product_id);

-- ============================================================
-- staging.payments
-- Grain: one row per (order_id, payment_sequential)
-- Multiple payment methods per order are retained individually.
-- ============================================================
DROP TABLE IF EXISTS staging.payments CASCADE;
CREATE TABLE staging.payments AS
SELECT
    order_id,
    payment_sequential::INT     AS payment_sequential,
    payment_type,
    payment_installments::INT   AS payment_installments,
    payment_value::NUMERIC(12,2) AS payment_value
FROM raw.raw_payments
WHERE order_id IS NOT NULL;

CREATE INDEX ON staging.payments (order_id);

-- ============================================================
-- staging.reviews
-- Grain: one row per (review_id)
-- Multiple reviews per order possible; we keep all and aggregate later.
-- ============================================================
DROP TABLE IF EXISTS staging.reviews CASCADE;
CREATE TABLE staging.reviews AS
SELECT
    review_id,
    order_id,
    review_score::SMALLINT           AS review_score,
    review_comment_title,
    review_comment_message,
    review_creation_date::TIMESTAMP  AS review_creation_date,
    review_answer_timestamp::TIMESTAMP AS review_answer_timestamp
FROM raw.raw_reviews
WHERE order_id IS NOT NULL
  AND review_score IS NOT NULL
  AND review_score::SMALLINT BETWEEN 1 AND 5;

CREATE INDEX ON staging.reviews (order_id);

-- ============================================================
-- staging.products
-- Grain: one row per product_id
-- ============================================================
DROP TABLE IF EXISTS staging.products CASCADE;
CREATE TABLE staging.products AS
SELECT
    product_id,
    product_category_name,
    NULLIF(product_name_lenght, '')::INT         AS product_name_length,
    NULLIF(product_description_lenght, '')::INT  AS product_description_length,
    NULLIF(product_photos_qty, '')::INT          AS product_photos_qty,
    NULLIF(product_weight_g, '')::NUMERIC        AS product_weight_g,
    NULLIF(product_length_cm, '')::NUMERIC       AS product_length_cm,
    NULLIF(product_height_cm, '')::NUMERIC       AS product_height_cm,
    NULLIF(product_width_cm, '')::NUMERIC        AS product_width_cm
FROM raw.raw_products
WHERE product_id IS NOT NULL;

ALTER TABLE staging.products ADD PRIMARY KEY (product_id);

-- ============================================================
-- staging.sellers
-- Grain: one row per seller_id
-- ============================================================
DROP TABLE IF EXISTS staging.sellers CASCADE;
CREATE TABLE staging.sellers AS
SELECT
    seller_id,
    seller_zip_code_prefix,
    seller_city,
    seller_state
FROM raw.raw_sellers
WHERE seller_id IS NOT NULL;

ALTER TABLE staging.sellers ADD PRIMARY KEY (seller_id);

-- ============================================================
-- staging.category_translation
-- Grain: one row per product_category_name
-- ============================================================
DROP TABLE IF EXISTS staging.category_translation CASCADE;
CREATE TABLE staging.category_translation AS
SELECT
    product_category_name,
    product_category_name_english AS category_english
FROM raw.raw_product_category_translation
WHERE product_category_name IS NOT NULL;

ALTER TABLE staging.category_translation ADD PRIMARY KEY (product_category_name);
