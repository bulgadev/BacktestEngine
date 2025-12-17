import sys
import os
from data_fetcher import DataFetcher
from datetime import datetime, timedelta
import pandas as pd

def test_dukascopy_fetch():
    print("Testing Dukascopy Data Fetching (EURUSD 10 days M1)...")
    
    # Define a recent period
    end_date = datetime.now()
    start_date = end_date - timedelta(days=10)
    
    try:
        # Force fetch_data to use '1m' and 'EURUSD'
        # Note: DataFetcher methods are instance or static? Static in my implementation.
        # But wait, did I make them static? Yes.
        
        # Also need to ensure we don't just use cache if I just ran it.
        # But I haven't run it yet.
        
        print(f"Fetching from {start_date.date()} to {end_date.date()}")
        df = DataFetcher.fetch_data('EURUSD', period='10d', interval='1m', use_cache=False)
        
        print("\nFetch Successful!")
        print(f"Rows: {len(df)}")
        print("Head:")
        print(df.head())
        print("Tail:")
        print(df.tail())
        
        # Verify columns
        expected_cols = ['Open', 'High', 'Low', 'Close']
        for col in expected_cols:
            if col not in df.columns:
                print(f"FAIL: Missing column {col}")
                return
        
        print("PASS: Data structure is correct.")
        
    except Exception as e:
        print(f"FAIL: Fetch raised exception: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    # Ensure data dir
    os.makedirs("data", exist_ok=True)
    test_dukascopy_fetch()
