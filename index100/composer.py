"""
Contains utilities for picking the constituents of an
index, adjust it, rebalance it, track changes.

This module works entirely using the defined models in models.py
and not concerned with persistance.

"""

from datetime import date
from typing import List, Tuple

from .constants import INDEX_SIZE
from .db import fetch_stocks_for_date, get_index_settings, load_index_for_dates
from .models import Change, EWIIndex100, IndexMember, Stock
from .utils import get_next_date, get_prev_date

"""
Contains utilities for picking the constituents of an
index, adjust it, rebalance it, track changes.

This module works entirely using the defined models in models.py
and not concerned with persistance.

"""

from datetime import date
from typing import List, Tuple


def select_stocks(stocks: List[Stock], count: int = INDEX_SIZE) -> List[Stock]:
    """
    Read all stocks for a day and pick top "count" stocks by market cap.

    """
    return sorted(stocks, key=lambda s: s.market_cap, reverse=True)[:count]


def adjust_index_balanced(
    old_index: EWIIndex100, new_stocks: List[Stock]
) -> EWIIndex100:
    """
    Adjusts the index by replacing the existing members with a new list of stocks,
    while preserving the index level continuity.

    This assumes the input index is already equal-weighted. It asserts that all
    members have the same market value (within tolerance) and uses that value to
    compute notional shares for the new stocks.

    The resulting index is also balanced (equal notional weights), and the divisor
    is adjusted accordingly to keep index value continuous.
    """
    assert len(new_stocks) == len(old_index.members), "Stock count mismatch"

    # Step 1: Assert balance and get target value per stock
    target_values = [
        round(m.stock.price * m.notional_num_shares, 8) for m in old_index.members
    ]
    target_value = target_values[0]
    for v in target_values:
        assert abs(v - target_value) < 1e-6, "Input index is not balanced"

    # Step 2: Compute notional shares for new stocks
    new_members = []
    for stock in new_stocks:
        notional_num_shares = target_value / stock.price
        new_members.append(
            IndexMember(stock=stock, notional_num_shares=notional_num_shares)
        )

    # Step 3: Compute new market value (which should be same as old index value)
    market_value_new = sum(m.stock.price * m.notional_num_shares for m in new_members)

    # Step 4: Adjust divisor to preserve continuity
    new_effective_divisor = market_value_new / old_index.value

    return EWIIndex100(
        date=old_index.date,
        base_date=old_index.base_date,
        base_value=old_index.base_value,
        members=new_members,
        divisor=new_effective_divisor,
    )


def compute_changes(old_index: EWIIndex100, new_index: EWIIndex100) -> List[Change]:
    """
    Compare old and new index and track changes in index composition and weights.
    Computes ADD, REMOVE, and REBALANCE Change rows by comparing old and new index members.

    """
    changes: List[Change] = []

    old_stocks = {m.stock: m for m in old_index.members}
    new_stocks = {m.stock: m for m in new_index.members}

    old_set = set(old_stocks)
    new_set = set(new_stocks)

    added = new_set - old_set
    removed = old_set - new_set

    for stock in added:
        changes.append(Change(date=new_index.date, kind="ADD", stock=stock))

    for stock in removed:
        changes.append(Change(date=new_index.date, kind="REMOVE", stock=stock))

    # For members that exist in both, detect weight changes => REBALANCE
    for stock in old_set & new_set:
        old_member = old_stocks[stock]
        new_member = new_stocks[stock]

        if abs(old_member.notional_num_shares - new_member.notional_num_shares) > 1e-8:
            changes.append(Change(date=new_index.date, kind="REBALANCE", stock=stock))

    return changes


# TODO: Verify logic around fractional shares and weights.
def rebalance_index(index: EWIIndex100) -> EWIIndex100:
    """
    Returns a new Index rebalanced to equal weights.

    This is the current logic:

    - Find the new index market value
    - Find each stock's target notional value
    - (?) Set the weight to be (target value / stock price)

    """
    numerator = sum(m.stock.price * m.notional_num_shares for m in index.members)
    n = len(index.members)
    target_value = numerator / n

    new_members: List[IndexMember] = []

    for member in index.members:
        current_value = member.stock.price * member.notional_num_shares

        if abs(current_value - target_value) < 1e-8:
            # Already equal-weighted
            new_members.append(member)
            continue

        new_notional_num_shares = target_value / member.stock.price

        new_members.append(
            IndexMember(stock=member.stock, notional_num_shares=new_notional_num_shares)
        )

    new_index = EWIIndex100(
        date=index.date,
        divisor=index.divisor,  # stays the same
        members=new_members,
        base_date=index.base_date,
        base_value=index.base_value,
    )

    return new_index


def compose_index(target_date: date) -> Tuple[EWIIndex100, List[Change]]:
    """
    Creates a new index for the given date and computes changes from previous day.
    For base_date: computes notional_num_shares to equal-weight stocks based on price,
    and sets the divisor appropriately.
    """
    settings = get_index_settings()
    base_date = date.fromisoformat(settings["base_date"])
    base_value = float(settings["base_value"])

    stocks = fetch_stocks_for_date(target_date)
    top_stocks = select_stocks(stocks, count=INDEX_SIZE)
    assert (
        len(top_stocks) == INDEX_SIZE
    ), f"Expected {INDEX_SIZE} stocks but got {len(top_stocks)}"

    if target_date == base_date:
        target_weight = base_value / INDEX_SIZE

        members = []
        for s in top_stocks:
            notional_num_shares = target_weight / s.price
            members.append(
                IndexMember(stock=s, notional_num_shares=notional_num_shares)
            )

        divisor = 1.0

        index = EWIIndex100(
            date=target_date,
            base_date=base_date,
            base_value=base_value,
            members=members,
            divisor=divisor,
        )
        return index, []
    else:
        prev_date = get_prev_date(target_date)
        prev_indexes = load_index_for_dates([prev_date])
        assert prev_date in prev_indexes, f"No index data for previous date {prev_date}"

        old_index = prev_indexes[prev_date]
        stocks_map = {s.stock: s for s in stocks}
        # Rebuild index with previous members but new prices
        updated_members = []
        for m in old_index.members:
            stock_id = m.stock.stock
            assert stock_id in stocks_map, f"Stock {stock_id} missing for {target_date}"

            updated_stock = stocks_map[stock_id]
            updated_members.append(
                IndexMember(
                    stock=updated_stock, notional_num_shares=m.notional_num_shares
                )
            )

        shadow_index = EWIIndex100(
            date=target_date,
            base_date=old_index.base_date,
            base_value=old_index.base_value,
            members=updated_members,
            divisor=old_index.divisor,
        )

        balanced_index = rebalance_index(shadow_index)
        new_index = adjust_index_balanced(balanced_index, top_stocks)
        changes = compute_changes(old_index, new_index)
        return new_index, changes
