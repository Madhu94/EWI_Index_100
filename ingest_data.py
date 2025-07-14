"""
Script to query price and market cap data and store it in database

$ingest_data.py "2025-06-02:2025-06-06"

"""

#!/usr/bin/python3
import argparse
from datetime import datetime, timedelta

from sqlalchemy import Table, delete, insert

from index100.daq import MarketDataFetcher
from index100.db import get_engine, get_metadata
from index100.utils import is_valid_index_date


def save_marketdata(start_date: str, end_date: str):
    """
    Calls PriceFetcher to get price and shares outstanding data,
    and stores in database.

    Idempotent, later calls replace data of earlier calls.

    """
    engine = get_engine()
    metadata = get_metadata()
    marketdata_table = Table("marketdata", metadata, autoload_with=engine)

    pf = MarketDataFetcher()

    with engine.begin() as conn:  # single transaction
        current_date = datetime.strptime(start_date, "%Y-%m-%d").date()
        final_date = datetime.strptime(end_date, "%Y-%m-%d").date()

        while current_date <= final_date:
            if is_valid_index_date(current_date):
                print(f"Processing {current_date}...")

                # Fetch fresh marketdata
                rows = pf.fetch(current_date)

                if not rows:
                    current_date += timedelta(days=1)
                    continue

                # Delete old data for this date
                del_stmt = delete(marketdata_table).where(
                    marketdata_table.c.date == current_date
                )
                conn.execute(del_stmt)

                # Insert new data
                conn.execute(insert(marketdata_table), rows)

                print(f"Saved {len(rows)} rows for {current_date}.")
            current_date += timedelta(days=1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Fetch and save market data for date range."
    )
    parser.add_argument(
        "date_range", type=str, help="Date range in format Y-M-D:Y-M-D(inclusive)."
    )
    args = parser.parse_args()

    if ":" in args.date_range:
        start_date, end_date = args.date_range.split(":")
    else:
        start_date = end_date = args.date_range

    save_marketdata(start_date, end_date)
