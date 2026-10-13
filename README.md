# Olist E-Commerce Weekly Business Review (WBR)

An end-to-end, production-grade ELT data pipeline, SQL analytics engine, automated data-quality check suite, visualization generator, and PDF executive reporting system built for the Brazilian E-Commerce Public Dataset by Olist.

---

## 1. Project Architecture

The pipeline follows a modern four-tier architecture designed for idempotency, referential integrity, and zero join fan-out:

```
[Raw CSVs (Kaggle)]
        │
        ▼ (src/ingest.py: validation & raw loading)
┌────────────────────────────────────────────────────────┐
│ PostgreSQL: raw schema                                │
│ (raw_orders, raw_order_items, raw_payments, etc.)      │
└────────────────────────────────────────────────────────┘
        │
        ▼ (sql/staging.sql: type-casting, constraints)
┌────────────────────────────────────────────────────────┐
│ PostgreSQL: staging schema                            │
│ (staging.orders, staging.order_items, etc.)           │
└────────────────────────────────────────────────────────┘
        │
        ▼ (sql/mart.sql: CTE aggregation before join)
┌────────────────────────────────────────────────────────┐
│ PostgreSQL: analytics schema                          │
│ (analytics.orders_mart — 1 row per order, PK: order_id)│
└────────────────────────────────────────────────────────┘
        │
        ├─────────────────────────────┬─────────────────────────────┐
        ▼                             ▼                             ▼
┌───────────────────────────┐ ┌───────────────────────────────────────────────┐ ┌───────────────────────────┐
│ Data Quality Suite (Part B)│ │ Analytical SQL (Part C)                       │ │ Visualizations (Part D)   │
│ 6 executable DQ SQL tests │ │ 6 analytical SQL queries                      │ │ 4 Matplotlib charts       │
│ Logged to dq_audit table  │ │ MoM Revenue, Category Rankings, Rolling       │ │ Saved to charts/          │
│                           │ │ Orders, Repeat Purchase, Delivery vs. Reviews │ │                           │
└───────────────────────────┘ └───────────────────────────────────────────────┘ └───────────────────────────┘
        │                             │                             │
        └─────────────────────────────┼─────────────────────────────┘
                                      ▼
                        ┌───────────────────────────┐
                        │ Executive PDF Report      │
                        │ 5-page ReportLab document │
                        │ Saved to reports/         │
                        └───────────────────────────┘
```

---

## 2. Directory Structure

```
olist-weekly-business-review/
├── data/
│   ├── .gitkeep              # Data anchor (raw CSVs supplied separately; excluded from ZIP)
│   ├── [olist_customers_dataset.csv]            # (Downloaded separately to data/)
│   ├── [olist_geolocation_dataset.csv]          # (Downloaded separately to data/)
│   ├── [olist_orders_dataset.csv]               # (Downloaded separately to data/)
│   ├── [olist_order_items_dataset.csv]          # (Downloaded separately to data/)
│   ├── [olist_order_payments_dataset.csv]       # (Downloaded separately to data/)
│   ├── [olist_order_reviews_dataset.csv]        # (Downloaded separately to data/)
│   ├── [olist_products_dataset.csv]             # (Downloaded separately to data/)
│   ├── [olist_sellers_dataset.csv]              # (Downloaded separately to data/)
│   └── [product_category_name_translation.csv]  # (Downloaded separately to data/)
├── src/
│   ├── __init__.py
│   ├── config.py             # Environment configuration & path resolvers
│   ├── db.py                 # SQLAlchemy / psycopg2 engine & schema init
│   ├── ingest.py             # File validation & raw table ingestion
│   ├── transform.py          # SQL staging & analytics mart builder
│   ├── quality_checks.py     # DQ check runner & audit table logger
│   ├── run_queries.py        # Part C SQL execution runner
│   ├── generate_charts.py    # Matplotlib chart generator (4 charts)
│   └── build_report.py       # 5-page ReportLab PDF compiler
├── sql/
│   ├── staging.sql           # Staging layer DDL & type casting
│   ├── mart.sql              # Order-level mart builder (fan-out safe)
│   ├── dq_01_order_id.sql    # DQ 1: Duplicate / null order IDs
│   ├── dq_02_delivery_dates.sql # DQ 2: Delivery before purchase
│   ├── dq_03_payment_reconciliation.sql # DQ 3: Payment vs item+freight
│   ├── dq_04_customer_integrity.sql # DQ 4: Missing customer FK
│   ├── dq_05_review_scores.sql # DQ 5: Out-of-range review scores
│   ├── dq_06_order_item_integrity.sql # DQ 6: Orphaned items / negative price
│   ├── q01_monthly_revenue.sql # Part C Q1: MoM revenue & growth
│   ├── q02_top_categories_by_state.sql # Part C Q2: Top 3 categories per state
│   ├── q02b_top_categories_overall.sql # Chart 2: Top categories overall
│   ├── q03_rolling_orders.sql # Part C Q3: 7-day rolling order average
│   ├── q04_repeat_purchase_rate.sql # Part C Q4: Customer repeat purchase rate
│   └── q05_delivery_delay_reviews.sql # Part C Q5: Delay vs review score
├── tests/
│   ├── __init__.py
│   ├── conftest.py           # Synthetic fixtures for unit testing
│   └── test_pipeline.py      # 24 automated pytest tests
├── charts/
│   ├── chart1_monthly_revenue.png
│   ├── chart2_top_categories.png
│   ├── chart3_delivery_vs_review.png
│   └── chart4_rolling_orders.png
├── reports/
│   └── olist_weekly_business_review.pdf # Final 5-page report
├── dags/
│   └── olist_wbr_dag.py      # Apache Airflow orchestration DAG
├── .env.example
├── .gitignore
├── requirements.txt
├── pipeline.py               # Main CLI pipeline entrypoint
└── README.md
```

---

## 3. Dataset Information & Download

**Dataset Source:** [Kaggle — Brazilian E-Commerce Public Dataset by Olist](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce)

> **Important Note on Submission Archive:**  
> In compliance with submission packaging standards, **raw CSV dataset files are not included in the submission ZIP archive**. Users and evaluators must place or download the raw Olist CSVs into the `data/` directory separately before executing the ingestion pipeline.

To download the dataset automatically using Python:
```bash
python -c "import kagglehub; path = kagglehub.dataset_download('olistbr/brazilian-ecommerce'); print(path)"
```
Then copy all 9 CSV files into the `data/` directory:
- `olist_customers_dataset.csv`
- `olist_geolocation_dataset.csv`
- `olist_orders_dataset.csv`
- `olist_order_items_dataset.csv`
- `olist_order_payments_dataset.csv`
- `olist_order_reviews_dataset.csv`
- `olist_products_dataset.csv`
- `olist_sellers_dataset.csv`
- `product_category_name_translation.csv`

---

## 4. Prerequisites & Installation

- **Python**: Python 3.10+ (tested on Python 3.13)
- **PostgreSQL**: Version 14+ (tested on PostgreSQL 18.4)

Install the required Python packages:
```bash
pip install -r requirements.txt
```

---

## 5. Configuration & Environment Variables

Copy `.env.example` to `.env` and fill in your PostgreSQL credentials:

```bash
cp .env.example .env
```

Example `.env`:
```env
DB_HOST=127.0.0.1
DB_PORT=5432
DB_NAME=postgres
DB_USER=postgres
DB_PASSWORD=your_secure_password
DB_SCHEMA_RAW=raw
DB_SCHEMA_STAGING=staging
DB_SCHEMA_ANALYTICS=analytics
DATA_DIR=data
```

---

## 6. Running the Pipeline

### Full End-to-End Pipeline
Executes validation, raw ingestion, staging, mart transformation, data quality checks, SQL queries, chart generation, and PDF compilation:
```bash
python pipeline.py
```

### Fast Run (Skipping Ingestion)
If CSVs are already loaded into PostgreSQL raw tables:
```bash
python pipeline.py --skip-ingest
```

### Only Regenerate Visualizations & PDF Report
```bash
python pipeline.py --only-report
```

### Strict Data Quality Mode (Assignment Alarm Mode)
In compliance with the assignment requirement that the pipeline stop with an error when a check fails, the `--strict-dq` flag (or `STRICT_DQ=1` environment variable) causes any check with non-zero failing rows to halt the pipeline immediately with `DataQualityHardFailure`:
```bash
python pipeline.py --strict-dq
```
*Note: In strict mode, the pipeline halts during Stage 2 because `dq_03_payment_reconciliation` flags 260 empirical payment discrepancies present in the raw Kaggle data. Standard mode documents these exceptions in `analytics.dq_audit` and report Page 2 while allowing downstream analytics to proceed.*

---

## 7. Running Automated Tests

Run the complete test suite with `pytest`:
```bash
pytest tests -v
```

The automated test suite (`tests/test_pipeline.py`) contains **24 end-to-end and unit tests** across 5 test classes:
1. `TestValidation`: Missing data directory handling, missing raw CSV files detection, schema missing-columns verification, and valid dataset acceptance.
2. `TestDataQualitySuite`: Missing SQL check handling, invalid SQL syntax error trap, hard-failure pipeline halting enforcement, strict-mode alarm halt on payment reconciliation exceptions, and execution of the full 6-rule DQ suite against raw tables.
3. `TestMartGrainAndFanOut`: Exactly 1 row per order in `analytics.orders_mart`, primary key non-null enforcement, and mathematical proof of zero revenue fan-out (`|mart_revenue - staging_revenue| < 0.01 BRL`).
4. `TestAnalyticalSQLQueries`: File existence checks, consecutive monthly revenue calendar continuity (Q1), top-3 categories per customer state (Q2), dedicated total delivered revenue top-15 categories across all states (Q2b for Chart 2), 7-day rolling daily order volume with zero-order date filling (Q3), repeat purchase rate using persistent `customer_unique_id` (Q4), delivery delay correlation across review scores (Q5), MoM growth rounding consistency (ROUND_HALF_UP), and Q4 date-filter enforcement (verifying Q4 output matches date-bounded inline SQL).
5. `TestMetricConsistencyAndReportValidation`: Cross-layer mathematical consistency of the North Star Metric (91.89% on-time delivery rate), consistency of customer repeat purchase rate (3.06% within Sep 2016 – Aug 2018), and strict rejection of missing query results in PDF compilation.

---

## 8. Executing Individual Analytical SQL Queries

Execute any analytical SQL query directly via Python:
```python
from src.run_queries import run_query
from src.config import SQL_DIR

df = run_query(SQL_DIR / "q01_monthly_revenue.sql")
print(df)
```

Or execute via `psql`:
```bash
psql -h 127.0.0.1 -U postgres -d postgres -f sql/q01_monthly_revenue.sql
```

---

## 9. Data Quality Policies & Exceptions

All data quality results are audited in `analytics.dq_audit`:

| Check File | Description | Severity | Treatment Policy |
|---|---|---|---|
| `dq_01_order_id.sql` | Null or duplicate order IDs | **HARD FAIL** | Halts pipeline immediately if duplicates or nulls occur. |
| `dq_02_delivery_dates.sql` | Delivery timestamp < Purchase timestamp | **SOFT (EXCEPTION)** | Preserved in mart with actual timestamps; filtered in delivery KPI queries. |
| `dq_03_payment_reconciliation.sql` | Payment total vs (Item price + Freight) | **SOFT (EXCEPTION)** | At the SQL file's >R$0.05 threshold: 260 orders (246 credit card, 7 debit card, 7 credit card+voucher). A tighter >R$0.01 threshold detects 303 orders. Source data lacks fee/discount itemization; all records retained intact. |
| `dq_04_customer_integrity.sql` | Missing customer FK reference | **HARD FAIL** | Halts pipeline immediately if orphaned orders exist. |
| `dq_05_review_scores.sql` | Review scores outside 1–5 range | **SOFT** | Staging layer enforces `BETWEEN 1 AND 5`; verified 0 defects. |
| `dq_06_order_item_integrity.sql` | Orphaned items / Negative prices | **SOFT** | Verified 0 defects. |

---

## 10. Metric Definitions Framework

### North Star Metric: On-Time Delivery Rate
- **Definition**: Percentage of delivered customer orders that arrived on or before the estimated delivery date.
- **Formula**: `(Orders with delivered_customer_timestamp <= estimated_delivery_timestamp) / (Delivered Orders with both actual and estimated timestamps non-null) * 100`
- **Eligible Population**: 96,470 delivered orders with both `delivered_customer_timestamp` and `estimated_delivery_timestamp` non-null.
- **Current Marketplace Value**: **91.89%** (88,644 on-time) with a directly calculated **8.11% late-delivery rate** (7,826 late).

### Supporting Metrics
1. **Average Review Score**: `AVG(review_score)` across all reviewed orders (**4.09 / 5.0**). In delivery delay analysis (Query 5), **95,824 delivered orders have valid customer reviews** (out of 96,470 eligible deliveries); 646 delivered orders have null review scores.
2. **Cancellation Rate**: `(Canceled Orders) / (Total Orders) * 100` (**0.63%** across 99,441 total orders).
3. **Overall Repeat-Purchase Rate**: `(Unique Customers with >= 2 Eligible Orders) / (Total Unique Customers) * 100` (**3.06%** — 2,923 repeat buyers out of 95,560 unique buyers with non-canceled orders within the Sep 2016 – Aug 2018 observation window).

### Observation Periods
- **Overall Order Activity**: September 2016 through October 2018 (99,441 total orders).
- **Delivered Commercial Operations**: September 2016 through August 2018 (96,478 delivered orders; 96,470 with non-null estimated and actual delivery timestamps). Only canceled/shipped orders occur in September–October 2018.
- **Daily Order Volume Series**: Full calendar range from September 4, 2016 through October 17, 2018 (774 consecutive calendar days with zero-order dates filled).

---

## 11. PDF Report Structure

The generated PDF (`reports/olist_weekly_business_review.pdf`) is strictly 5 pages:
- **Page 1**: Executive Summary, Pipeline Architecture, Dataset Overview, North Star Metric & Supporting Framework.
- **Page 2**: Data Quality Audit Ledger, Defect Summary, and Quality Policies.
- **Page 3**: SQL Analytics Deep-Dive (MoM Revenue, State Category Rankings, Overall Repeat-Purchase Analysis).
- **Page 4**: Four High-Resolution Visualizations in 2x2 Grid.
- **Page 5**: 1-Page Executive Memorandum to VP of Operations with empirical evidence, operational recommendations, measurable success criteria, and caveats.

---

## 12. Apache Airflow Orchestration (Optional)

The pipeline includes an Airflow DAG in `dags/olist_wbr_dag.py`:
- **DAG ID**: `olist_weekly_business_review`
- **Schedule**: Daily (`0 6 * * *` — every day at 06:00 UTC, meeting Part A bonus requirement)
- **Task Sequence**: `start >> validate_and_ingest_raw >> run_raw_data_quality_checks >> staging_and_mart_transform >> execute_analytical_queries >> generate_visualizations >> compile_pdf_report >> end`
