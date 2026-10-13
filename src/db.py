import logging
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from src.config import DATABASE_URL, DB_SCHEMA_RAW, DB_SCHEMA_STAGING, DB_SCHEMA_ANALYTICS

logger = logging.getLogger(__name__)

def get_engine() -> Engine:
    """Creates and returns a SQLAlchemy engine instance."""
    return create_engine(DATABASE_URL, pool_pre_ping=True)

def init_db():
    """Initializes schemas in PostgreSQL database if they do not exist."""
    engine = get_engine()
    with engine.begin() as conn:
        for schema in [DB_SCHEMA_RAW, DB_SCHEMA_STAGING, DB_SCHEMA_ANALYTICS]:
            logger.info(f"Ensuring schema '{schema}' exists.")
            conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {schema};"))
    logger.info("Database schemas initialized successfully.")

def execute_sql_file(file_path, params=None):
    """Executes a SQL file against the database using SQLAlchemy connection."""
    engine = get_engine()
    with open(file_path, 'r', encoding='utf-8') as f:
        sql_script = f.read()
    
    with engine.begin() as conn:
        result = conn.execute(text(sql_script), params or {})
        return result
