"""
Initialize the FastAPI ASGI App, add routes.

"""

import json
from datetime import date
from datetime import date as DateType
from io import BytesIO
from typing import Dict, List

import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import StreamingResponse

from index100.composer import compose_index
from index100.db import (get_index_settings, load_changes_for_dates,
                         load_index_for_dates, persist_changes, persist_index)
from index100.models import Change, EWIIndex100
from index100.redis import bulk_read, bulk_write, changes_key, index_key
from index100.returns import Return, compute_returns
from index100.utils import get_next_date, get_prev_date, is_valid_index_date

app = FastAPI()


def expand_dates(start_date: date, end_date: date) -> List[date]:
    """
    Expand start and end date into a list of business dates (inclusive),
    skipping weekends, using get_next_date and get_prev_date for consistency,
    and excluding start_date if it’s not a valid index date.

    """
    dates = []
    current_date = start_date

    while current_date <= end_date:
        if current_date.weekday() < 5 and is_valid_index_date(current_date):
            dates.append(current_date)
        current_date = get_next_date(current_date)

    return dates


def compose_and_persist_index_range(start_date: DateType, end_date: DateType) -> None:
    """
    Compose index for each valid date in [start_date, end_date] (inclusive)
    and persist the indexes and changes in the database.

    Uses expand_dates to skip weekends and invalid dates.
    This operation is idempotent.

    """

    for current_date in expand_dates(start_date, end_date):
        index, changes = compose_index(current_date)
        persist_index(index)
        persist_changes(changes)


@app.post("/build-index")
async def compose_index_for_dates(
    start_date: date = Query(..., description="Start date in YYYY-MM-DD"),
    end_date: date = Query(..., description="End date in YYYY-MM-DD"),
):
    """
    Create and persist index for each date in range [start date, end date]
    (inclusive). Index is also adjusted and rebalanced.

    Changes in composition ae also computed and persisted for all
    days except base date.

    """

    try:
        compose_and_persist_index_range(start_date, end_date)
        return {
            "status": "ok",
            "message": f"Indexes and changes composed for {start_date} to {end_date}",
        }
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/index-composition/", response_model=Dict[date, EWIIndex100])
async def get_indexes(
    start_date: date = Query(..., description="Start date (YYYY-MM-DD)"),
    end_date: date = Query(..., description="End date (YYYY-MM-DD)"),
) -> Dict[date, EWIIndex100]:
    """
    Returns a dict of { date: Index} for the given date range.
    This would contain the index level, divisor, all the members.

    Manages Redis as a read through cache to the database.

    """
    dates = expand_dates(start_date, end_date)
    keys = [index_key(d) for d in dates]

    # Try look up in redis
    redis_results = await bulk_read(keys)

    found: Dict[date, EWIIndex100] = {}
    missing_dates: List[date] = []

    for date_obj, key in zip(dates, keys):
        data = redis_results.get(key)
        if data:
            print("Cache found...", data, date_obj, key)
            found[date_obj] = EWIIndex100.model_validate_json(data)
        else:
            print("Cache miss...", data, date_obj, key)
            missing_dates.append(date_obj)

    # Load missing from DB if needed
    if missing_dates:
        db_results = load_index_for_dates(missing_dates)

        # Write missing to Redis
        kv_pairs = {
            index_key(d): sp100.model_dump_json() for d, sp100 in db_results.items()
        }
        await bulk_write(kv_pairs)

        # Write back
        found.update(db_results)
    return found


@app.get("/composition-changes/", response_model=Dict[date, List[Change]])
async def get_changes(
    start_date: date = Query(..., description="Start date (YYYY-MM-DD)"),
    end_date: date = Query(..., description="End date (YYYY-MM-DD)"),
) -> Dict[date, List[Change]]:
    """
    Returns index composition changes for each date in the
    date range [start date, end date] (inclusive).

    Manages Redis as a read through cache to the database.

    """
    dates = expand_dates(start_date, end_date)
    keys = [changes_key(d) for d in dates]

    # Read from Redis
    redis_results = await bulk_read(keys)

    found: Dict[date, List[Change]] = {}
    missing_dates: List[date] = []

    for date_obj, key in zip(dates, keys):
        data = redis_results.get(key)
        if data:
            found[date_obj] = [Change.model_validate(item) for item in json.loads(data)]
        else:
            missing_dates.append(date_obj)

    # Load missing from DB if needed
    if missing_dates:
        db_results = load_changes_for_dates(missing_dates)

        # Write missing back to Redis
        kv_pairs = {
            changes_key(d): json.dumps(
                [c.model_dump(mode="json") for c in changes_list]
            )
            for d, changes_list in db_results.items()
        }
        await bulk_write(kv_pairs)

        found.update(db_results)

    return found


def expand_dates_for_returns(start_date: date, end_date: date) -> List[date]:
    """
    Expands to [t1-1, t2].

    """
    return [get_prev_date(start_date)] + expand_dates(start_date, end_date)


@app.get("/index-performance/", response_model=Dict[date, Return])
async def get_index_returns(
    start_date: date = Query(...), end_date: date = Query(...)
) -> Dict[date, Return]:
    """
    Returns daily and cumulative returns for index in [start_date, end_date]
    (inclusive).


    """

    # Expand the date range
    dates = expand_dates_for_returns(start_date, end_date)
    base_date = date.fromisoformat(get_index_settings()["base_date"])
    dates = [d for d in dates if d >= base_date]
    keys = [index_key(d) for d in dates]

    # Try to bulk read index data from redis
    redis_results = await bulk_read(keys)

    found: Dict[date, EWIIndex100] = {}
    missing_dates: List[date] = []

    for d, key in zip(dates, keys):
        data = redis_results.get(key)
        if data:
            found[d] = EWIIndex100.model_validate_json((data))
        else:
            missing_dates.append(d)

    # Load missing from DB
    if missing_dates:
        db_results = load_index_for_dates(missing_dates)

        # Write back to Redis
        kv_pairs = {
            index_key(d): json.dumps(db_results[d].model_dump(mode="json"))
            for d in db_results
        }
        await bulk_write(kv_pairs)

        found.update(db_results)

    # Final index series
    index_series = [found[d] for d in sorted(found)]

    # Compute returns
    return compute_returns(index_series, start_date)


@app.post("/export-data/")
async def export_index_report(
    start_date: date = Query(..., description="Start date in YYYY-MM-DD"),
    end_date: date = Query(..., description="End date in YYYY-MM-DD"),
):
    """
    Generates an Excel file with index performance, composition, and changes for the past 3 business days.
    """

    # Use expand_dates_for_returns for t-1 coverage
    dates = expand_dates_for_returns(start_date, end_date)
    base_date = date.fromisoformat(get_index_settings()["base_date"])
    dates = [d for d in dates if d >= base_date]

    index_data: Dict[date, EWIIndex100] = load_index_for_dates(dates)
    changes_data: Dict[date, List[Change]] = load_changes_for_dates(
        expand_dates(start_date, end_date)
    )

    index_series = [index_data[d] for d in sorted(index_data)]
    returns = compute_returns(index_series, start_date)

    # Index Returns Sheet
    returns_rows = []
    for d in sorted(returns):
        index_obj = index_data[d]
        ret = returns[d]
        returns_rows.append(
            {
                "Date": d.isoformat(),
                "Index Level": index_obj.value,
                "Divisor": index_obj.divisor,
                "Daily Return": ret.daily_return,
                "Cumulative Return": ret.cumulative_return,
            }
        )
    df_returns = pd.DataFrame(returns_rows)

    # Composition Sheet
    composition_rows = []
    for d in sorted(index_data):
        if d < start_date:
            continue  # skip t-1 in composition
        index = index_data[d]
        for member in index.members:
            composition_rows.append(
                {
                    "Date": d.isoformat(),
                    "Stock": member.stock.stock,
                    "Notional Num Shares": member.notional_num_shares,
                    "Market Cap": member.market_cap,
                }
            )
    df_composition = pd.DataFrame(composition_rows)

    # Changes Sheet
    changes_rows = []
    for d, changes in sorted(changes_data.items()):
        for change in changes:
            changes_rows.append(
                {
                    "Date": d.isoformat(),
                    "Operation": change.kind,
                    "Stock": change.stock.stock,
                }
            )
    df_changes = pd.DataFrame(changes_rows)

    # Write Excel
    output = BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        df_returns.to_excel(writer, sheet_name="Index Returns", index=False)
        df_composition.to_excel(writer, sheet_name="Composition", index=False)
        df_changes.to_excel(writer, sheet_name="Changes", index=False)

    output.seek(0)
    filename = f"index_report_{start_date}_{end_date.isoformat()}.xlsx"
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
