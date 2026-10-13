import logging
from pathlib import Path
import pandas as pd
from sqlalchemy import text
from src.db import get_engine
from src.config import SQL_DIR

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("run_queries")

QUERIES = [
    ("q01_monthly_revenue",        "Monthly Revenue & MoM Growth"),
    ("q02_top_categories_by_state", "Top 3 Categories by Revenue per State"),
    ("q02b_top_categories_overall", "Top Categories by Delivered Revenue Overall"),
    ("q03_rolling_orders",         "7-Day Rolling Average of Daily Order Count"),
    ("q04_repeat_purchase_rate",   "Repeat-Purchase Rate"),
    ("q05_delivery_delay_reviews", "Delivery Delay vs Review Score"),
]

def run_query(sql_path: Path) -> pd.DataFrame:
    """Execute a SQL file and return results as a pandas DataFrame."""
    if not sql_path.exists():
        raise FileNotFoundError(f"Required analytical query file not found: {sql_path}")
    with open(sql_path, "r", encoding="utf-8") as f:
        sql = f.read()
    engine = get_engine()
    with engine.connect() as conn:
        df = pd.read_sql(text(sql), conn)
    return df

def run_all_queries():
    """
    Execute all Part C analytical queries and return {query_name: DataFrame}.
    Fails immediately if any required SQL file is missing.
    """
    logger.info("--- Starting Pipeline Stage 4: Analytical Query Execution ---")
    results = {}
    for query_name, label in QUERIES:
        sql_path = SQL_DIR / f"{query_name}.sql"
        if not sql_path.exists():
            raise FileNotFoundError(f"Required analytical query file not found: {sql_path}")
        logger.info(f"Running query: {label}")
        df = run_query(sql_path)
        logger.info(f"  -> {len(df)} rows returned.")
        results[query_name] = df
    logger.info("All analytical queries executed successfully.")
    return results

if __name__ == "__main__":
    results = run_all_queries()
    for k, df in results.items():
        print(f"\n=== {k} ===")
        print(df.head(10).to_string(index=False))
