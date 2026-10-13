"""
tests/conftest.py
Shared fixtures for the test suite.
"""
import pytest
import pandas as pd
from pathlib import Path

# Small synthetic order fixtures for unit tests
SYNTHETIC_ORDERS = pd.DataFrame({
    "order_id": ["ord_001", "ord_002", "ord_003"],
    "customer_id": ["cust_a", "cust_b", "cust_c"],
    "order_status": ["delivered", "delivered", "canceled"],
    "order_purchase_timestamp": ["2018-01-01 10:00:00", "2018-02-01 10:00:00", "2018-03-01 10:00:00"],
    "order_approved_at": ["2018-01-01 11:00:00", "2018-02-01 11:00:00", None],
    "order_delivered_carrier_date": ["2018-01-05 09:00:00", "2018-02-10 09:00:00", None],
    "order_delivered_customer_date": ["2018-01-08 15:00:00", "2018-02-12 15:00:00", None],
    "order_estimated_delivery_date": ["2018-01-10 00:00:00", "2018-02-08 00:00:00", None],
})

SYNTHETIC_CUSTOMERS = pd.DataFrame({
    "customer_id": ["cust_a", "cust_b", "cust_c"],
    "customer_unique_id": ["uniq_x", "uniq_y", "uniq_z"],
    "customer_zip_code_prefix": ["01310", "20040", "30140"],
    "customer_city": ["sao paulo", "rio de janeiro", "belo horizonte"],
    "customer_state": ["SP", "RJ", "MG"],
})

SYNTHETIC_ITEMS = pd.DataFrame({
    "order_id": ["ord_001", "ord_001", "ord_002"],
    "order_item_id": ["1", "2", "1"],
    "product_id": ["prod_1", "prod_2", "prod_1"],
    "seller_id": ["sell_1", "sell_1", "sell_2"],
    "shipping_limit_date": ["2018-01-05", "2018-01-05", "2018-02-05"],
    "price": ["100.00", "50.00", "200.00"],
    "freight_value": ["10.00", "5.00", "15.00"],
})

SYNTHETIC_PAYMENTS = pd.DataFrame({
    "order_id": ["ord_001", "ord_002"],
    "payment_sequential": ["1", "1"],
    "payment_type": ["credit_card", "credit_card"],
    "payment_installments": ["1", "1"],
    "payment_value": ["165.00", "215.00"],
})

@pytest.fixture
def synthetic_orders():
    return SYNTHETIC_ORDERS.copy()

@pytest.fixture
def synthetic_customers():
    return SYNTHETIC_CUSTOMERS.copy()

@pytest.fixture
def synthetic_items():
    return SYNTHETIC_ITEMS.copy()

@pytest.fixture
def synthetic_payments():
    return SYNTHETIC_PAYMENTS.copy()

@pytest.fixture
def tmp_data_dir(tmp_path, synthetic_orders, synthetic_customers, synthetic_items, synthetic_payments):
    """Write synthetic CSVs to a temp directory for ingestion tests."""
    from src.config import REQUIRED_FILES
    
    # Write each synthetic file with required column names
    synthetic_orders.rename(columns={
        "order_purchase_timestamp": "order_purchase_timestamp",
        "order_approved_at": "order_approved_at",
        "order_delivered_carrier_date": "order_delivered_carrier_date",
        "order_delivered_customer_date": "order_delivered_customer_date",
        "order_estimated_delivery_date": "order_estimated_delivery_date",
    }).to_csv(tmp_path / "olist_orders_dataset.csv", index=False)
    
    synthetic_customers.to_csv(tmp_path / "olist_customers_dataset.csv", index=False)
    synthetic_items.to_csv(tmp_path / "olist_order_items_dataset.csv", index=False)
    synthetic_payments.to_csv(tmp_path / "olist_order_payments_dataset.csv", index=False)
    
    # Write minimal required files for other tables
    pd.DataFrame({"review_id": [], "order_id": [], "review_score": [],
                  "review_comment_title": [], "review_comment_message": [],
                  "review_creation_date": [], "review_answer_timestamp": []}).to_csv(
        tmp_path / "olist_order_reviews_dataset.csv", index=False)
    
    pd.DataFrame({"seller_id": [], "seller_zip_code_prefix": [],
                  "seller_city": [], "seller_state": []}).to_csv(
        tmp_path / "olist_sellers_dataset.csv", index=False)
    
    pd.DataFrame({"product_id": [], "product_category_name": [],
                  "product_name_lenght": [], "product_description_lenght": [],
                  "product_photos_qty": [], "product_weight_g": [],
                  "product_length_cm": [], "product_height_cm": [],
                  "product_width_cm": []}).to_csv(
        tmp_path / "olist_products_dataset.csv", index=False)
    
    pd.DataFrame({"geolocation_zip_code_prefix": [], "geolocation_lat": [],
                  "geolocation_lng": [], "geolocation_city": [],
                  "geolocation_state": []}).to_csv(
        tmp_path / "olist_geolocation_dataset.csv", index=False)
    
    pd.DataFrame({"product_category_name": [],
                  "product_category_name_english": []}).to_csv(
        tmp_path / "product_category_name_translation.csv", index=False)
    
    return tmp_path
