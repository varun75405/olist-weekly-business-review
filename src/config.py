import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env if present
env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / os.getenv("DATA_DIR", "data")
SQL_DIR = BASE_DIR / "sql"
CHARTS_DIR = BASE_DIR / "charts"
REPORTS_DIR = BASE_DIR / "reports"

# Ensure output directories exist
CHARTS_DIR.mkdir(parents=True, exist_ok=True)
REPORTS_DIR.mkdir(parents=True, exist_ok=True)

# Database credentials
DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "postgres")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")

DB_SCHEMA_RAW = os.getenv("DB_SCHEMA_RAW", "raw")
DB_SCHEMA_STAGING = os.getenv("DB_SCHEMA_STAGING", "staging")
DB_SCHEMA_ANALYTICS = os.getenv("DB_SCHEMA_ANALYTICS", "analytics")

DATABASE_URL = f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# Required CSV files and expected column schemas
REQUIRED_FILES = {
    "raw_orders": {
        "filename": "olist_orders_dataset.csv",
        "columns": [
            "order_id", "customer_id", "order_status",
            "order_purchase_timestamp", "order_approved_at",
            "order_delivered_carrier_date", "order_delivered_customer_date",
            "order_estimated_delivery_date"
        ]
    },
    "raw_order_items": {
        "filename": "olist_order_items_dataset.csv",
        "columns": [
            "order_id", "order_item_id", "product_id", "seller_id",
            "shipping_limit_date", "price", "freight_value"
        ]
    },
    "raw_payments": {
        "filename": "olist_order_payments_dataset.csv",
        "columns": [
            "order_id", "payment_sequential", "payment_type",
            "payment_installments", "payment_value"
        ]
    },
    "raw_reviews": {
        "filename": "olist_order_reviews_dataset.csv",
        "columns": [
            "review_id", "order_id", "review_score",
            "review_comment_title", "review_comment_message",
            "review_creation_date", "review_answer_timestamp"
        ]
    },
    "raw_customers": {
        "filename": "olist_customers_dataset.csv",
        "columns": [
            "customer_id", "customer_unique_id",
            "customer_zip_code_prefix", "customer_city", "customer_state"
        ]
    },
    "raw_sellers": {
        "filename": "olist_sellers_dataset.csv",
        "columns": [
            "seller_id", "seller_zip_code_prefix",
            "seller_city", "seller_state"
        ]
    },
    "raw_products": {
        "filename": "olist_products_dataset.csv",
        "columns": [
            "product_id", "product_category_name",
            "product_name_lenght", "product_description_lenght",
            "product_photos_qty", "product_weight_g",
            "product_length_cm", "product_height_cm", "product_width_cm"
        ]
    },
    "raw_geolocation": {
        "filename": "olist_geolocation_dataset.csv",
        "columns": [
            "geolocation_zip_code_prefix", "geolocation_lat",
            "geolocation_lng", "geolocation_city", "geolocation_state"
        ]
    },
    "raw_product_category_translation": {
        "filename": "product_category_name_translation.csv",
        "columns": [
            "product_category_name", "product_category_name_english"
        ]
    }
}
