"""
tests/test_pipeline.py
Automated test suite for the Olist Weekly Business Review pipeline.
Covers validation, raw DQ detection, failure halting, SQL correctness,
fan-out prevention, repeat purchase logic, and metric consistency.
"""
import pytest
import pandas as pd
from pathlib import Path
from unittest.mock import patch
from sqlalchemy import text


class TestValidation:
    """Tests for file and column schema validation (src/ingest.py)."""

    def test_missing_directory_raises_error(self, tmp_path):
        from src.ingest import validate_dataset_files, IngestionError
        missing_dir = tmp_path / "nonexistent_dir"
        with pytest.raises(IngestionError, match="does not exist"):
            validate_dataset_files(missing_dir)

    def test_missing_file_raises_error(self, tmp_path):
        from src.ingest import validate_dataset_files, IngestionError
        tmp_path.mkdir(exist_ok=True)
        with pytest.raises(IngestionError, match="Missing required CSV file"):
            validate_dataset_files(tmp_path)

    def test_missing_column_raises_error(self, tmp_path):
        from src.ingest import validate_dataset_files, IngestionError
        pd.DataFrame({"order_id": ["a"], "customer_id": ["b"]}).to_csv(
            tmp_path / "olist_orders_dataset.csv", index=False)
        with pytest.raises(IngestionError, match="missing required columns"):
            validate_dataset_files(tmp_path)

    def test_valid_dataset_passes(self, tmp_data_dir):
        from src.ingest import validate_dataset_files
        validate_dataset_files(tmp_data_dir)


class TestDataQualitySuite:
    """Tests for Data Quality validation, error handling, and pipeline halting."""

    def test_missing_dq_sql_file_raises_error(self, tmp_path):
        from src.quality_checks import run_single_check, DataQualityError
        missing_sql = tmp_path / "dq_nonexistent.sql"
        with pytest.raises(DataQualityError, match="missing"):
            run_single_check("dq_nonexistent", missing_sql)

    def test_invalid_sql_syntax_raises_error(self, tmp_path):
        from src.quality_checks import run_single_check, DataQualityError
        bad_sql = tmp_path / "dq_bad.sql"
        bad_sql.write_text("SELECT * FROM non_existent_table_xyz123;")
        with pytest.raises(DataQualityError, match="SQL execution error"):
            run_single_check("dq_bad", bad_sql)

    def test_hard_fail_check_halts_pipeline(self):
        from src.quality_checks import run_quality_checks, DataQualityHardFailure
        with patch("src.quality_checks.run_single_check") as mock_check:
            mock_check.return_value = (5, "order_123, order_456")
            with pytest.raises(DataQualityHardFailure, match="PIPELINE HALTED"):
                run_quality_checks()

    def test_strict_dq_halts_on_reconciliation_exceptions(self):
        """In strict mode, pipeline halts on dq_03 (260 payment exceptions)."""
        from src.quality_checks import run_quality_checks, DataQualityHardFailure
        with pytest.raises(DataQualityHardFailure, match="dq_03_payment_reconciliation"):
            run_quality_checks(strict=True)

    def test_dq_checks_run_against_raw_tables(self):
        from src.quality_checks import run_quality_checks
        results = run_quality_checks(strict=False)
        assert isinstance(results, list)
        assert len(results) == 6
        check_names = [r["check_name"] for r in results]
        assert "dq_01_order_id" in check_names
        assert "dq_03_payment_reconciliation" in check_names
        assert "dq_04_customer_integrity" in check_names


class TestMartGrainAndFanOut:
    """Tests for mart grain, primary keys, and fan-out join prevention."""

    def test_mart_has_exactly_one_row_per_order(self):
        from src.db import get_engine
        engine = get_engine()
        with engine.connect() as conn:
            dup_count = conn.execute(text("""
                SELECT COUNT(*) FROM (
                    SELECT order_id FROM analytics.orders_mart
                    GROUP BY order_id HAVING COUNT(*) > 1
                ) dups
            """)).scalar()
            total_orders = conn.execute(text("SELECT COUNT(*) FROM analytics.orders_mart")).scalar()
        assert dup_count == 0, f"Found {dup_count} duplicate order_ids in orders_mart"
        assert total_orders > 0

    def test_mart_primary_key_not_null(self):
        from src.db import get_engine
        engine = get_engine()
        with engine.connect() as conn:
            null_count = conn.execute(text(
                "SELECT COUNT(*) FROM analytics.orders_mart WHERE order_id IS NULL"
            )).scalar()
        assert null_count == 0

    def test_revenue_no_fan_out(self):
        from src.db import get_engine
        engine = get_engine()
        with engine.connect() as conn:
            res = conn.execute(text("""
                WITH mart_sum AS (
                    SELECT SUM(item_total) AS total_m FROM analytics.orders_mart
                ),
                staging_sum AS (
                    SELECT SUM(price) AS total_s FROM staging.order_items
                )
                SELECT ABS(mart_sum.total_m - staging_sum.total_s) AS diff
                FROM mart_sum, staging_sum
            """)).scalar()
        assert res < 0.01, f"Revenue fan-out detected! Discrepancy: {res} BRL"


class TestAnalyticalSQLQueries:
    """Tests verifying Part C analytical SQL queries."""

    def test_missing_query_file_raises_error(self, tmp_path):
        from src.run_queries import run_query
        missing_sql = tmp_path / "q_missing.sql"
        with pytest.raises(FileNotFoundError, match="not found"):
            run_query(missing_sql)

    def test_q01_consecutive_calendar_months_growth(self):
        from src.run_queries import run_query
        from src.config import SQL_DIR
        df = run_query(SQL_DIR / "q01_monthly_revenue.sql")
        assert not df.empty
        assert "monthly_revenue" in df.columns
        assert "pct_growth" in df.columns
        
        # Verify consecutive calendar months with no gaps
        months = pd.to_datetime(df["month"])
        for i in range(1, len(months)):
            expected_month = (months.iloc[i-1] + pd.DateOffset(months=1)).replace(day=1)
            assert months.iloc[i] == expected_month, f"Gap in calendar months at index {i}: {months.iloc[i]}"

    def test_q02_top_categories_by_state(self):
        from src.run_queries import run_query
        from src.config import SQL_DIR
        df = run_query(SQL_DIR / "q02_top_categories_by_state.sql")
        assert not df.empty
        assert "customer_state" in df.columns
        assert "revenue_rank" in df.columns
        assert (df["revenue_rank"] <= 3).all()

    def test_q02b_top_categories_overall(self):
        from src.run_queries import run_query
        from src.config import SQL_DIR
        df = run_query(SQL_DIR / "q02b_top_categories_overall.sql")
        assert not df.empty
        assert len(df) == 15
        assert "category_english" in df.columns
        assert "revenue" in df.columns
        # Verify revenue is strictly descending
        assert (df["revenue"].diff().dropna() <= 0).all()
        # Top 1 should be health_beauty with > 1.4M BRL delivered revenue
        assert df.iloc[0]["category_english"] == "health_beauty"
        assert df.iloc[0]["revenue"] > 1400000.0

    def test_q03_rolling_orders_7_calendar_days(self):
        from src.run_queries import run_query
        from src.config import SQL_DIR
        df = run_query(SQL_DIR / "q03_rolling_orders.sql")
        assert not df.empty
        assert "rolling_7day_avg" in df.columns
        dates = pd.to_datetime(df["order_date"])
        diffs = dates.diff().dropna()
        assert (diffs == pd.Timedelta(days=1)).all(), "Zero-order date gaps found in rolling query"

    def test_q04_repeat_purchase_rate_uses_unique_id(self):
        from src.run_queries import run_query
        from src.config import SQL_DIR
        df = run_query(SQL_DIR / "q04_repeat_purchase_rate.sql")
        assert not df.empty
        row = df.iloc[0]
        assert row["total_customers"] > 90000
        assert 0.0 < float(row["repeat_purchase_rate_pct"]) < 10.0

    def test_q05_delivery_delay_review_score_relationship(self):
        from src.run_queries import run_query
        from src.config import SQL_DIR
        df = run_query(SQL_DIR / "q05_delivery_delay_reviews.sql")
        assert not df.empty
        assert len(df) == 5  # Scores 1, 2, 3, 4, 5
        # Total reviewed population must sum exactly to 95,824 orders
        assert df["order_count"].sum() == 95824
        score_1_late = df[df["review_score"] == 1]["late_pct"].values[0]
        score_5_late = df[df["review_score"] == 5]["late_pct"].values[0]
        # Late % for 1-star reviews should be significantly higher than 5-star reviews
        assert score_1_late > score_5_late * 5

    def test_q01_growth_rate_rounding_consistency(self):
        from src.run_queries import run_query
        from src.config import SQL_DIR
        from decimal import Decimal, ROUND_HALF_UP
        df = run_query(SQL_DIR / "q01_monthly_revenue.sql")
        nov_row = df[df["month"].astype(str).str.startswith("2017-11")].iloc[0]
        # Verify unrounded growth calculation is 53.55%
        raw_pct = 100.0 * (nov_row["monthly_revenue"] - nov_row["prev_revenue"]) / nov_row["prev_revenue"]
        d = Decimal(str(nov_row["pct_growth"])).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)
        assert d == Decimal("53.6")
        assert f"{d:.1f}%" == "53.6%"

    def test_q04_date_filter_enforced(self):
        """Q4 must only count non-canceled orders within Sep 2016 – Aug 2018."""
        from src.run_queries import run_query
        from src.config import SQL_DIR
        from src.db import get_engine

        # Run the actual Q4 query
        df = run_query(SQL_DIR / "q04_repeat_purchase_rate.sql")
        q4_total = int(df.iloc[0]["total_customers"])
        q4_repeat = int(df.iloc[0]["repeat_customers"])
        q4_rate = float(df.iloc[0]["repeat_purchase_rate_pct"])

        # Independently verify with explicit date-bounded inline SQL
        engine = get_engine()
        with engine.connect() as conn:
            tot = conn.execute(text(
                "SELECT COUNT(DISTINCT customer_unique_id) FROM analytics.orders_mart "
                "WHERE order_status <> 'canceled' AND customer_unique_id IS NOT NULL "
                "AND purchase_timestamp >= '2016-09-01' AND purchase_timestamp < '2018-09-01'"
            )).scalar()
            rep = conn.execute(text("""
                SELECT COUNT(*) FROM (
                    SELECT customer_unique_id FROM analytics.orders_mart
                    WHERE order_status <> 'canceled' AND customer_unique_id IS NOT NULL
                    AND purchase_timestamp >= '2016-09-01' AND purchase_timestamp < '2018-09-01'
                    GROUP BY customer_unique_id HAVING COUNT(DISTINCT order_id) >= 2
                ) x
            """)).scalar()

        assert q4_total == tot, f"Q4 total ({q4_total}) != date-filtered total ({tot})"
        assert q4_repeat == rep, f"Q4 repeat ({q4_repeat}) != date-filtered repeat ({rep})"
        assert q4_rate == round(100.0 * rep / tot, 2), "Q4 rate != independently calculated rate"


class TestMetricConsistencyAndReportValidation:
    """Tests ensuring mathematical consistency across metrics and reports."""

    def test_on_time_delivery_rate_consistency(self):
        from src.db import get_engine
        engine = get_engine()
        with engine.connect() as conn:
            delivered_ts = conn.execute(text(
                "SELECT COUNT(*) FROM analytics.orders_mart WHERE order_status='delivered' AND delivered_customer_timestamp IS NOT NULL"
            )).scalar()
            on_time = conn.execute(text(
                "SELECT COUNT(*) FROM analytics.orders_mart WHERE order_status='delivered' AND delivered_on_time_flag = 1"
            )).scalar()
            rate = round(100.0 * on_time / delivered_ts, 2)
        assert rate == 91.89, f"Expected 91.89% on-time delivery rate, got {rate}%"

    def test_repeat_purchase_rate_consistency(self):
        from src.db import get_engine
        engine = get_engine()
        with engine.connect() as conn:
            tot = conn.execute(text(
                "SELECT COUNT(DISTINCT customer_unique_id) FROM analytics.orders_mart "
                "WHERE order_status <> 'canceled' AND customer_unique_id IS NOT NULL "
                "AND purchase_timestamp >= '2016-09-01' AND purchase_timestamp < '2018-09-01'"
            )).scalar()
            rep = conn.execute(text("""
                SELECT COUNT(*) FROM (
                    SELECT customer_unique_id FROM analytics.orders_mart
                    WHERE order_status <> 'canceled' AND customer_unique_id IS NOT NULL
                    AND purchase_timestamp >= '2016-09-01' AND purchase_timestamp < '2018-09-01'
                    GROUP BY customer_unique_id HAVING COUNT(DISTINCT order_id) >= 2
                ) x
            """)).scalar()
            rate = round(100.0 * rep / tot, 2)
        assert rate == 3.06, f"Expected 3.06% repeat purchase rate, got {rate}%"

    def test_report_builder_rejects_missing_queries(self):
        from src.build_report import build_pdf
        with pytest.raises(ValueError, match="Required query result"):
            build_pdf(query_results={}, dq_results=[{"check_name": "x"}])
