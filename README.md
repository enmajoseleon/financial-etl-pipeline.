# Automated Financial Data Pipeline (Medallion Architecture)

An automated, production-ready ETL pipeline designed to incrementally extract, transform, and model daily end-of-day market data using a **Medallion Architecture** (Bronze, Silver, Gold). Powered by **Python**, **DuckDB**, and **Pandas**, and scheduled for automated execution via **GitHub Actions**.

## Architecture & Data Lineage

The pipeline runs on a scheduled cron job every weekday at market close (21:00 UTC) to fetch and process EOD indicators for major market assets (`SPY`, `QQQ`, `AAPL`, `MSFT`, `NVDA`, `GLD`, `XOM`).

```
┌─────────────────┐      ┌───────────────────────────┐      ┌───────────────────────────┐      ┌───────────────────────────┐
│                 │      │       BRONZE LAYER        │      │       SILVER LAYER        │      │        GOLD LAYER         │
│  yfinance API   │ ───► │  Raw Market Ingestion     │ ───► │  Cleaned & Standardized   │ ───► │   Analytics & Features    │
│  (Data Source)  │      │  (DuckDB Append-Only)     │      │  (Deduplicated & Typed)   │      │   (Aggregations & Metrics)│
└─────────────────┘      └───────────────────────────┘      └───────────────────────────┘      └───────────────────────────┘
                                                                                                             │
                                                                                                             ▼
                                                                                              ┌─────────────────────────────┐
                                                                                              │ gold_market_analytics.parquet│
                                                                                              │  (GitHub Actions Artifact)  │
                                                                                              └─────────────────────────────┘
```

## Key Features & Technical Highlights

* **Watermark-based Incremental Ingestion:** Dynamically queries DuckDB for `MAX(date)` per ticker to extract only new records, preventing duplicate API calls and enforcing idempotency.

* **Embedded Data Warehousing:** Utilizes DuckDB for fast, columnar in-process OLAP execution without external server overhead.

* **Medallion Data Layering:**

  * **Bronze:** Ingests raw multi-ticker OHLCV market payloads.

  * **Silver:** Normalizes schema structures, flattens MultiIndex columns, casts data types, and sanitizes field names.

  * **Gold:** Constructs analytical models, pre-calculates target indicators, and outputs downstream-ready Parquet files.

* **CI/CD & Automated Orchestration:** Fully containerized runner setup on GitHub Actions with automated schedule triggers (`cron: '0 21 * * 1-5'`) and `workflow_dispatch` manual capabilities.

* **Artifact Publishing:** Automatically packages and exposes the final `gold_market_analytics.parquet` file as a downloadable workflow artifact upon every run.

## Tech Stack

| Domain | Technology | 
| ----- | ----- | 
| **Language** | Python 3.10 | 
| **Data Processing** | DuckDB, Pandas, PyArrow | 
| **Data Extraction** | yfinance API | 
| **CI/CD & Orchestration** | GitHub Actions, GitHub CLI (`gh`) | 
| **Storage Formats** | DuckDB (`.duckdb`), Apache Parquet (`.parquet`) | 

## Repository Structure

```
.
├── .github/
│   └── workflows/
│       └── etl_pipeline.yml     # GitHub Actions workflow definition
├── data/
│   └── warehouse.duckdb         # Local DuckDB database storage
├── etl_pipeline.py              # Main ETL script implementing Medallion layers
├── requirements.txt             # Python dependencies
└── README.md                    # Project documentation
```

## Getting Started Locally

### Prerequisites

* Python 3.10+
* Git

### Installation & Execution

1. **Clone the repository:**

   ```bash
   git clone https://github.com/enmajoseleon/financial-etl-pipeline.git
   cd financial-etl-pipeline
   ```

2. **Install dependencies:**

   ```bash
   pip install -r requirements.txt
   ```

3. **Run the ETL Pipeline:**

   ```bash
   python etl_pipeline.py
   ```

Upon execution, the script will update `data/warehouse.duckdb` and generate the exported `gold_market_analytics.parquet` file in the root directory.

## Triggering via GitHub CLI

To manually trigger and monitor the remote pipeline using the GitHub CLI:

```bash
# Dispatch workflow execution
gh workflow run etl_pipeline.yml -R enmajoseleon/financial-etl-pipeline

# Monitor live run state
gh run watch -R enmajoseleon/financial-etl-pipeline
```