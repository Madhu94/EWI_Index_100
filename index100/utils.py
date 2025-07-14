from datetime import date, timedelta

from .db import get_index_settings

# TODO: Proper trading calendar support
MARKET_HOLIDAYS_2025 = {
    date(2025, 1, 1),  # New Year’s Day
    date(2025, 1, 20),  # MLK Day
    date(2025, 2, 17),  # Presidents Day
    date(2025, 4, 18),  # Good Friday
    date(2025, 5, 26),  # Memorial Day
    date(2025, 6, 19),  # Juneteenth
    date(2025, 7, 4),  # Independence Day
    date(2025, 9, 1),  # Labor Day
    date(2025, 11, 27),  # Thanksgiving
    date(2025, 12, 25),  # Christmas Day
}


def get_prev_date(current_date: date) -> date:
    """
    Returns the previous business day, skipping weekends.
    """
    prev = current_date - timedelta(days=1)
    while prev.weekday() >= 5 or prev in MARKET_HOLIDAYS_2025:
        prev -= timedelta(days=1)
    return prev


def get_next_date(current_date: date) -> date:
    """
    Returns the next business day, skipping weekends.
    """
    nxt = current_date + timedelta(days=1)
    while nxt.weekday() >= 5 or nxt in MARKET_HOLIDAYS_2025:
        nxt += timedelta(days=1)
    return nxt


def is_market_date(d: date) -> bool:
    """
    Returns True if the given date is a trading day:
    - Not Saturday/Sunday
    - Not a known US market holiday

    """
    return d.weekday() < 5 and d not in MARKET_HOLIDAYS_2025


def is_valid_index_date(d: date) -> bool:
    """
    True if:
      - It’s a valid market date (weekday, not holiday)
      - AND date >= base_date from settings
    If base_date is missing: return False instead of raising.
    """
    from .db import get_index_settings

    base_date_str = get_index_settings().get("base_date")
    if not base_date_str:
        return False

    base_date = date.fromisoformat(base_date_str)
    return is_market_date(d) and d >= base_date
