"""
Compute daily and cumulative returns for index, given index levels.

"""

from datetime import date
from typing import Dict, List

import pandas as pd
from pydantic import BaseModel

from .models import EWIIndex100


class Return(BaseModel):
    daily_return: float
    cumulative_return: float


def compute_returns(
    index_series: List[EWIIndex100], start_date: date
) -> Dict[date, Return]:
    """
    Given a series of SP100 covering [t1-1, t2], compute:
      - daily returns: (V_t - V_{t-1}) / V_{t-1}
      - cumulative returns: (V_t - ref period value) / ref period value

    Returns { date: Return(daily_return, cumulative_return) }
    """

    if len(index_series) < 2:
        raise ValueError("At least 2 index points are required (need t1-1 and t2).")

    index_series = sorted(index_series, key=lambda x: x.date)

    base_date = index_series[0].base_date
    today = date.today()

    t1 = index_series[1].date
    t2 = index_series[-1].date

    if t1 < base_date:
        raise ValueError(f"Start date t1 ({t1}) must be >= base date ({base_date}).")
    if t2 > today:
        raise ValueError(f"End date t2 ({t2}) must be <= today ({today}).")

    df = pd.DataFrame(
        {
            "date": [i.date for i in index_series],
            "index_value": [i.value for i in index_series],
        }
    )

    df["daily_return"] = df["index_value"].pct_change()

    window_base_idx = 0 if df.iloc[0]["date"] == start_date else 1
    window_base = df.iloc[window_base_idx]["index_value"]
    df["cumulative_return"] = (df["index_value"] - window_base) / window_base

    # Drop t1-1 for final output
    df = df.iloc[1:].reset_index(drop=True)

    return {
        row["date"]: Return(
            daily_return=None if pd.isna(row["daily_return"]) else row["daily_return"],
            cumulative_return=row["cumulative_return"],
        )
        for _, row in df.iterrows()
    }
