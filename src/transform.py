import time
import logging
from sqlalchemy import text
from src.db import get_engine
from src.config import SQL_DIR, DB_SCHEMA_STAGING, DB_SCHEMA_ANALYTICS

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("transform")

def run_sql_file(conn, filepath, label):
    """Execute a SQL file and log the duration."""
    start = time.time()
    logger.info(f"Executing SQL: {label}")
    with open(filepath, "r", encoding="utf-8") as f:
        sql = f.read()
    conn.execute(text(sql))
    duration = time.time() - start
    logger.info(f"Completed '{label}' in {duration:.2f}s")

def run_staging():
    """Create cleaned staging tables by executing staging.sql."""
    engine = get_engine()
    with engine.begin() as conn:
        run_sql_file(conn, SQL_DIR / "staging.sql", "staging tables")
    logger.info("Staging layer built successfully.")

def run_mart():
    """Build the order-level analytics mart by executing mart.sql."""
    engine = get_engine()
    with engine.begin() as conn:
        run_sql_file(conn, SQL_DIR / "mart.sql", "analytics mart")
    
    # Log mart row count
    engine2 = get_engine()
    with engine2.connect() as conn:
        result = conn.execute(text(f"SELECT COUNT(*) FROM {DB_SCHEMA_ANALYTICS}.orders_mart"))
        row_count = result.scalar()
    logger.info(f"Mart built: {DB_SCHEMA_ANALYTICS}.orders_mart has {row_count:,} rows.")
    return row_count

def run_transform():
    logger.info("--- Starting Pipeline Stage 2: Staging & Mart Transformation ---")
    run_staging()
    mart_count = run_mart()
    return mart_count

if __name__ == "__main__":
    run_transform()
