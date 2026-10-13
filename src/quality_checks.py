import time
import logging
from pathlib import Path
from sqlalchemy import text
from src.db import get_engine
from src.config import SQL_DIR, DB_SCHEMA_ANALYTICS

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("quality_checks")

class DataQualityError(Exception):
    """Raised when a DQ check file is missing or fails SQL execution."""
    pass

class DataQualityHardFailure(Exception):
    """Raised when a mandatory (hard fail) data quality check fails."""
    pass

DQ_CHECKS = [
    ("dq_01_order_id",              "Null or duplicate order IDs in raw orders",               True),
    ("dq_02_delivery_dates",        "Delivered timestamp earlier than purchase timestamp",       False),
    ("dq_03_payment_reconciliation","Payment total vs item+freight reconciliation (>0.05 BRL)",  False),
    ("dq_04_customer_integrity",    "Orders with missing customer foreign key references",      True),
    ("dq_05_review_scores",         "Review scores outside valid 1-5 range or null",            False),
    ("dq_06_order_item_integrity",  "Orphaned order items or non-positive item prices",         False),
]

def ensure_audit_table():
    """Create the DQ audit table in PostgreSQL if it doesn't exist."""
    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(text(f"""
            CREATE SCHEMA IF NOT EXISTS {DB_SCHEMA_ANALYTICS};
            CREATE TABLE IF NOT EXISTS {DB_SCHEMA_ANALYTICS}.dq_audit (
                id SERIAL PRIMARY KEY,
                check_name TEXT NOT NULL,
                description TEXT NOT NULL,
                is_hard_fail BOOLEAN NOT NULL,
                failing_rows BIGINT NOT NULL,
                sample_ids TEXT,
                status TEXT NOT NULL,
                run_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """))

def run_single_check(check_name, sql_path: Path):
    """
    Executes a single DQ check SQL script.
    Raises DataQualityError if the SQL file is missing or execution errors out.
    """
    if not sql_path.exists():
        raise DataQualityError(f"Mandatory DQ check file missing: {sql_path}")

    with open(sql_path, "r", encoding="utf-8") as f:
        sql = f.read()

    engine = get_engine()
    try:
        with engine.connect() as conn:
            result = conn.execute(text(sql))
            row = result.fetchone()
    except Exception as e:
        raise DataQualityError(f"SQL execution error in check '{check_name}': {str(e)}") from e

    if row is None:
        return 0, None
    failing_rows = int(row[0]) if row[0] is not None else 0
    sample_ids = str(row[1]) if len(row) > 1 and row[1] is not None else None
    return failing_rows, sample_ids

def log_to_audit(check_name, description, is_hard_fail, failing_rows, sample_ids, status):
    """Records one execution result in the dq_audit ledger table."""
    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(text(f"""
            INSERT INTO {DB_SCHEMA_ANALYTICS}.dq_audit
                (check_name, description, is_hard_fail, failing_rows, sample_ids, status)
            VALUES
                (:check_name, :description, :is_hard_fail, :failing_rows, :sample_ids, :status)
        """), {
            "check_name": check_name,
            "description": description,
            "is_hard_fail": is_hard_fail,
            "failing_rows": failing_rows,
            "sample_ids": sample_ids,
            "status": status
        })

def run_quality_checks():
    """
    Executes all source-level data quality checks on raw tables before staging/mart.
    Halts the pipeline immediately if any check file is missing, errors, or fails a hard check.
    """
    logger.info("--- Starting Data Quality Validation Suite (Raw Tables) ---")
    ensure_audit_table()
    results = []

    for check_name, description, is_hard_fail in DQ_CHECKS:
        sql_path = SQL_DIR / f"{check_name}.sql"
        start = time.time()
        
        failing_rows, sample_ids = run_single_check(check_name, sql_path)
        duration = time.time() - start

        if failing_rows == 0:
            status = "PASS"
        else:
            status = "FAIL_HARD" if is_hard_fail else "FAIL_SOFT"

        log_to_audit(check_name, description, is_hard_fail, failing_rows, sample_ids, status)

        log_fn = logger.info if status == "PASS" else logger.warning
        log_fn(f"[{status}] {check_name}: {failing_rows:,} failing rows | {description} ({duration:.2f}s)")

        results.append({
            "check_name": check_name,
            "description": description,
            "is_hard_fail": is_hard_fail,
            "failing_rows": failing_rows,
            "sample_ids": sample_ids,
            "status": status
        })

    # Strict check: Halt pipeline if any hard-fail checks failed
    hard_failures = [r for r in results if r["status"] == "FAIL_HARD"]
    if hard_failures:
        msg = "PIPELINE HALTED: Mandatory Data Quality checks failed on raw data:\n"
        for hf in hard_failures:
            msg += f"  - {hf['check_name']}: {hf['failing_rows']:,} invalid rows (Sample: {hf['sample_ids']})\n"
        logger.error(msg)
        raise DataQualityHardFailure(msg)

    logger.info("All raw data quality checks passed successfully (or recorded documented exceptions).")
    return results

if __name__ == "__main__":
    run_quality_checks()
