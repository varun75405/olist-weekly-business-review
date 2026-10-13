#!/usr/bin/env python3
"""
pipeline.py — Main end-to-end pipeline runner for Olist Weekly Business Review.

Execution Order:
  1. Validate dataset files & ingest raw CSVs to PostgreSQL atomically
  2. Execute source-integrity Data Quality checks on raw tables (Halts on hard failure)
  3. Build staging tables & order-level analytics mart (SQL transformations)
  4. Execute Part C analytical queries (PostgreSQL SQL)
  5. Generate Matplotlib visualizations from query outputs
  6. Compile 5-page Executive PDF Report & VP Memo

Usage:
    python pipeline.py [--skip-ingest] [--skip-checks] [--only-report]
"""
import sys
import time
import logging
import argparse

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("pipeline")

def run_pipeline(skip_ingest=False, skip_checks=False, only_report=False, strict_dq=None):
    import os
    if strict_dq is None:
        strict_dq = os.getenv("STRICT_DQ", "1").lower() not in ("0", "false", "no")
    start_time = time.time()
    logger.info("=" * 65)
    logger.info("  Olist Weekly Business Review — Production Pipeline")
    logger.info("=" * 65)

    dq_results = []
    query_results = {}
    chart_paths = {}

    if not only_report:
        # ── Stage 1: Validate & Ingest Raw Data ───────────────────────────────
        if not skip_ingest:
            from src.ingest import run_ingestion
            run_ingestion()
        else:
            logger.info("Skipping CSV ingestion (--skip-ingest flag set).")

        # ── Stage 2: Data Quality Checks on Raw Data ──────────────────────────
        # Source integrity checks run BEFORE staging transformations
        if not skip_checks:
            from src.quality_checks import run_quality_checks
            try:
                dq_results = run_quality_checks(strict=strict_dq)
            except Exception as e:
                logger.error(f"PIPELINE TERMINATED AT STAGE 2: {str(e)}")
                sys.exit(1)
        else:
            logger.info("Skipping DQ checks (--skip-checks flag set).")

        # ── Stage 3: Staging & Analytics Mart Transformations ────────────────
        from src.transform import run_transform
        run_transform()

    # ── Stage 4: Part C Analytical Queries ───────────────────────────────────
    from src.run_queries import run_all_queries
    query_results = run_all_queries()

    # ── Stage 5: Generate Visualizations ─────────────────────────────────────
    from src.generate_charts import generate_all_charts
    chart_paths = generate_all_charts(query_results)

    # ── Stage 6: Compile 5-Page Executive PDF Report ─────────────────────────
    if not dq_results:
        from src.db import get_engine
        from sqlalchemy import text
        engine = get_engine()
        with engine.connect() as conn:
            rows = conn.execute(text("""
                SELECT check_name, description, is_hard_fail, failing_rows, sample_ids, status
                FROM (
                    SELECT DISTINCT ON (check_name)
                        id, check_name, description, is_hard_fail, failing_rows, sample_ids, status
                    FROM analytics.dq_audit
                    ORDER BY check_name, id DESC
                ) sub
                ORDER BY id ASC;
            """)).fetchall()
            dq_results = [dict(r._mapping) for r in rows]

    from src.build_report import build_pdf
    report_path = build_pdf(query_results, dq_results, chart_paths)

    total_duration = time.time() - start_time
    logger.info("=" * 65)
    logger.info(f"  Pipeline successfully completed in {total_duration:.1f}s")
    logger.info(f"  Executive Report: {report_path}")
    logger.info("=" * 65)
    return report_path

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Olist BDA Pipeline Runner")
    parser.add_argument("--skip-ingest", action="store_true",
                        help="Skip CSV ingestion (re-use existing raw tables)")
    parser.add_argument("--skip-checks", action="store_true",
                        help="Skip DQ checks")
    parser.add_argument("--only-report", action="store_true",
                        help="Only regenerate charts and PDF report")
    parser.add_argument("--allow-dq-exceptions", action="store_true",
                        help="Allow documented business-anomaly DQ exceptions (e.g. 260 payment discrepancies) to proceed to downstream report generation")
    args = parser.parse_args()
    import os
    env_strict = os.getenv("STRICT_DQ", "1").lower() not in ("0", "false", "no")
    strict_dq = env_strict and (not args.allow_dq_exceptions)
    run_pipeline(
        skip_ingest=args.skip_ingest,
        skip_checks=args.skip_checks,
        only_report=args.only_report,
        strict_dq=strict_dq
    )
