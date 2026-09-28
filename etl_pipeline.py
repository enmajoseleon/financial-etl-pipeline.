import duckdb
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
import os

DB_PATH = "data/warehouse.duckdb"
DEFAULT_START_DATE = "2020-01-01"
TICKERS = ["SPY", "QQQ", "AAPL", "MSFT", "NVDA", "GLD", "XOM"]

def get_db_connection(db_path: str = DB_PATH):
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    return duckdb.connect(db_path)

def init_bronze_table(con):
    con.execute("""
        CREATE TABLE IF NOT EXISTS bronze_market_data (
            ticker VARCHAR,
            date DATE,
            open DOUBLE,
            high DOUBLE,
            low DOUBLE,
            close DOUBLE,
            adj_close DOUBLE,
            volume BIGINT,
            extracted_at TIMESTAMP,
            PRIMARY KEY (ticker, date)
        )
    """)

def get_last_ingested_date(con, ticker: str) -> str:
    result = con.execute("""
        SELECT MAX(date) 
        FROM bronze_market_data 
        WHERE ticker = ?
    """, [ticker]).fetchone()[0]
    
    if result is None:
        return DEFAULT_START_DATE
    
    next_date = pd.to_datetime(result) + timedelta(days=1)
    return next_date.strftime("%Y-%m-%d")

def fetch_and_load_ticker_data(con, ticker: str):
    start_date = get_last_ingested_date(con, ticker)
    today = datetime.now().strftime("%Y-%m-%d")
    
    if start_date >= today:
        print(f"[SKIP] {ticker}: Already up to date ({start_date}).")
        return

    print(f"[FETCH] Downloading {ticker} from {start_date} to {today}...")
    
    # Download market data
    df = yf.download(ticker, start=start_date, end=today, progress=False)
    
    if df.empty:
        print(f"[INFO] No new data available for {ticker}.")
        return

    df = df.reset_index()
    
    # Flatten MultiIndex columns if returned by newer yfinance versions
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [col[0] for col in df.columns]

    # Normalize column names to lowercase and replace spaces
    df.columns = [str(c).lower().replace(" ", "_") for c in df.columns]

    # Ensure adj_close exists (fallback to close if missing)
    if "adj_close" not in df.columns:
        if "adj_close" in df.columns:
            df["adj_close"] = df["adj_close"]
        else:
            df["adj_close"] = df["close"]

    # Add ingestion metadata
    df["ticker"] = ticker
    df["extracted_at"] = datetime.now()
    df["date"] = pd.to_datetime(df["date"]).dt.date

    # Select required columns only
    df_to_insert = df[["ticker", "date", "open", "high", "low", "close", "adj_close", "volume", "extracted_at"]]

    # Incremental insert into DuckDB
    con.execute("""
        INSERT INTO bronze_market_data 
        SELECT * FROM df_to_insert
    """)
    
    print(f"[SUCCESS] {len(df_to_insert)} rows inserted for {ticker}.")

def export_gold_parquet(con):
    # Export Gold dataset to Parquet for GitHub Actions artifact upload
    con.execute("""
        COPY (
            SELECT * FROM bronze_market_data
        ) TO 'gold_market_analytics.parquet' (FORMAT PARQUET)
    """)
    print("[SUCCESS] Gold dataset exported to gold_market_analytics.parquet")

def run_ingestion():
    con = get_db_connection()
    try:
        init_bronze_table(con)
        for ticker in TICKERS:
            fetch_and_load_ticker_data(con, ticker)
        
        # Export Gold layer artifact
        export_gold_parquet(con)
    finally:
        con.close()

if __name__ == "__main__":
    run_ingestion()