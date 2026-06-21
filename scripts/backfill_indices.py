"""One-time backfill: recompute every historical day in data/market_indices.json
using the current formula in update_indices.py, replacing old-formula values.

Use this after a formula revision (like the Phase 2 Growth/Inflation rework)
so the entire chart history is consistent, instead of waiting for old data to
gradually age out of the dashboard's trailing windows.

Run:
    FRED_API_KEY=<your key> python scripts/backfill_indices.py

This OVERWRITES data/market_indices.json with a freshly recomputed history
(every valid trading day in the ~3-year fetch window). Review the diff before
committing.
"""
import json
import os

from fredapi import Fred

from update_indices import (
    DATA_PATH,
    compute_index_dataframe,
    market_data_to_record,
    row_to_market_data,
)

FRED_API_KEY = os.environ.get('FRED_API_KEY')


def backfill():
    if not FRED_API_KEY:
        print("Error: FRED_API_KEY environment variable not set.")
        return False

    fred = Fred(api_key=FRED_API_KEY)
    valid_df = compute_index_dataframe(fred)

    if valid_df is None:
        print("Error: compute_index_dataframe returned no data.")
        return False

    records = []
    for idx, row in valid_df.iterrows():
        date_str = idx.strftime("%Y-%m-%d")
        market_data = row_to_market_data(row)
        records.append(market_data_to_record(date_str, market_data))

    with open(DATA_PATH, 'w', encoding='utf-8') as f:
        json.dump(records, f, separators=(',', ':'))

    print(f"Backfilled {len(records)} records ({records[0][0]} to {records[-1][0]}) to {DATA_PATH}")
    return True


if __name__ == "__main__":
    try:
        if not backfill():
            exit(1)
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"Backfill failed: {e}")
        exit(1)
