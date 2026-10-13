import time
import logging
import pandas as pd
from pathlib import Path
from sqlalchemy import text
from src.config import DATA_DIR, REQUIRED_FILES, DB_SCHEMA_RAW
from src.db import get_engine, init_db

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("ingest")

class IngestionError(Exception):
    """Raised when file validation or atomic database loading fails."""
    pass

def validate_dataset_files(data_dir: Path = DATA_DIR):
    """Validates existence of all required CSV files and expected column headers."""
    if not data_dir.exists():
        raise IngestionError(f"Data directory '{data_dir}' does not exist.")

    for table_name, meta in REQUIRED_FILES.items():
        file_path = data_dir / meta["filename"]
        if not file_path.exists():
            raise IngestionError(
                f"Missing required CSV file: '{meta['filename']}' for table '{table_name}'. "
                f"Expected path: {file_path}"
            )
        
        # Check column names
        try:
            df_head = pd.read_csv(file_path, nrows=1)
        except Exception as e:
            raise IngestionError(f"Error reading CSV header from '{meta['filename']}': {str(e)}")
        
        missing_cols = set(meta["columns"]) - set(df_head.columns)
        if missing_cols:
            raise IngestionError(
                f"File '{meta['filename']}' is missing required columns: {sorted(list(missing_cols))}. "
                f"Found columns: {list(df_head.columns)}"
            )

    logger.info("Dataset files and schema headers validated successfully.")

def cleanup_stage_tables(engine, stage_tables):
    """Safely drops any temporary staging tables created during failed ingestion."""
    try:
        with engine.begin() as cleanup_conn:
            for tbl in stage_tables:
                cleanup_conn.execute(text(f"DROP TABLE IF EXISTS {DB_SCHEMA_RAW}.{tbl} CASCADE;"))
        logger.info("Cleaned up temporary staging tables.")
    except Exception as cleanup_err:
        logger.warning(f"Error while cleaning up temporary staging tables: {cleanup_err}")

def load_raw_tables(data_dir: Path = DATA_DIR):
    """
    All-table staging and transactional swap strategy:
    
    Guarantees:
      1. All 9 required CSV files are staged into isolated temporary tables (raw.{table}_stage_tmp).
      2. If ANY file fails to read, parse, or load into its temporary table, the operation halts immediately,
         all temporary staging tables are dropped, and existing production raw tables remain completely untouched.
      3. Only when ALL 9 tables are 100% staged successfully does a single PostgreSQL transaction execute the
         atomic swap (DROP production raw table, RENAME _stage_tmp to production raw table).
      4. Guarantees true all-or-nothing atomicity across the entire multi-table raw dataset reload.
    """
    start_time = time.time()
    init_db()
    engine = get_engine()
    
    table_counts = {}
    staged_tables = []

    logger.info("Phase 1: Staging all 9 dataset files into temporary tables...")
    try:
        for table_name, meta in REQUIRED_FILES.items():
            stage_start = time.time()
            file_path = data_dir / meta["filename"]
            tmp_table = f"{table_name}_stage_tmp"
            logger.info(f"Staging '{meta['filename']}' into {DB_SCHEMA_RAW}.{tmp_table}...")
            
            # Read CSV in text mode to preserve exact raw strings
            df = pd.read_csv(file_path, dtype=str)
            row_count = len(df)
            
            # Write into temporary table
            df.to_sql(
                name=tmp_table,
                con=engine,
                schema=DB_SCHEMA_RAW,
                if_exists="replace",
                index=False,
                chunksize=15000
            )
            staged_tables.append(tmp_table)
            
            duration = time.time() - stage_start
            logger.info(f"Staged {row_count:,} rows into {DB_SCHEMA_RAW}.{tmp_table} in {duration:.2f}s.")
            table_counts[table_name] = row_count

        logger.info("Phase 2: All tables staged successfully. Executing atomic transactional swap of all raw tables...")
        with engine.begin() as conn:
            for table_name in REQUIRED_FILES.keys():
                tmp_table = f"{table_name}_stage_tmp"
                conn.execute(text(f"DROP TABLE IF EXISTS {DB_SCHEMA_RAW}.{table_name} CASCADE;"))
                conn.execute(text(f"ALTER TABLE {DB_SCHEMA_RAW}.{tmp_table} RENAME TO {table_name};"))

    except Exception as e:
        logger.error(f"Ingestion failed during staging phase: {str(e)}. Rolling back and preserving production tables.")
        cleanup_stage_tables(engine, staged_tables)
        raise IngestionError(f"Database load failed; production raw tables preserved untouched: {str(e)}") from e

    total_duration = time.time() - start_time
    logger.info(f"All raw tables loaded and atomically swapped in {total_duration:.2f}s.")
    return table_counts

def run_ingestion():
    logger.info("--- Starting Pipeline Stage 1: Dataset Validation & Raw Ingestion ---")
    validate_dataset_files()
    counts = load_raw_tables()
    return counts

if __name__ == "__main__":
    run_ingestion()
