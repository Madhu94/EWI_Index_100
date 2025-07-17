"""
Module to read and write domain models to the database,
manage sqlite connections, and misc db utilities etc

"""

from datetime import date
from functools import cache
from itertools import groupby
from typing import Dict, List

from sqlalchemy import MetaData, Table, create_engine, insert, select
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.engine import Engine

from .models import Change, EWIIndex100, IndexMember, Stock

# TODO: Move this to settings/configuration
DATABASE_URL = "sqlite:////data/sp100.db"

# Singleton placeholders
_engine: Engine | None = None
_metadata: MetaData | None = None


def get_engine() -> Engine:
    """
    Singleton getter for the SQLAlchemy Engine.
    Lazily initialized.

    """
    global _engine
    if _engine is None:
        _engine = create_engine(DATABASE_URL, echo=False)
    return _engine


def get_metadata() -> MetaData:
    """
    Singleton getter for SQLAlchemy MetaData.
    Lazily initialized.

    """
    global _metadata
    if _metadata is None:
        _metadata = MetaData()
        _metadata.reflect(bind=get_engine())
    return _metadata


def fetch_stocks_for_date(target_date: date) -> List[Stock]:
    """
    Bulk read the market data (price, shares_outstanding) from database,
    for a given target date.

    """
    engine = get_engine()
    metadata = get_metadata()

    marketdata = Table("marketdata", metadata, autoload_with=engine)

    stmt = select(
        marketdata.c.stock, marketdata.c.price, marketdata.c.shares_outstanding
    ).where(marketdata.c.date == target_date)

    with engine.begin() as conn:
        result = conn.execute(stmt)
        rows = result.fetchall()

    stocks = [
        Stock(
            stock=row.stock, price=row.price, shares_outstanding=row.shares_outstanding
        )
        for row in rows
    ]

    return stocks


@cache
def get_index_settings() -> Dict[str, str]:
    """
    Pulls index settings once and caches them in memory.

    """
    engine = get_engine()
    metadata = get_metadata()
    settings = Table("settings", metadata, autoload_with=engine)

    with engine.begin() as conn:
        rows = conn.execute(select(settings.c.key, settings.c.value)).fetchall()
        return {row.key: row.value for row in rows}


def load_index_for_dates(dates: List[date]) -> Dict[date, EWIIndex100]:
    """
    Reads index levels and member data for multiple dates.
    Uses cached get_index_settings for base_date/base_value.
    Joins members with marketdata to get price and shares_outstanding.
    """
    engine = get_engine()
    metadata = get_metadata()

    indexlevels = Table("indexlevels", metadata, autoload_with=engine)
    members = Table("members", metadata, autoload_with=engine)
    marketdata = Table("marketdata", metadata, autoload_with=engine)

    settings_map = get_index_settings()
    base_date_str = settings_map.get("base_date")
    base_value_str = settings_map.get("base_value")

    if not base_date_str or not base_value_str:
        raise ValueError("Base date or base value is missing in settings table.")

    base_date = date.fromisoformat(base_date_str)
    base_value = float(base_value_str)

    indexes: Dict[date, EWIIndex100] = {}

    with engine.begin() as conn:
        # Index levels
        result = conn.execute(
            select(indexlevels.c.date, indexlevels.c.divisor).where(
                indexlevels.c.date.in_(dates)
            )
        ).fetchall()
        indexlevels_map = {r.date: r.divisor for r in result}

        result = conn.execute(
            select(
                members.c.date,
                members.c.stock,
                marketdata.c.price,
                marketdata.c.shares_outstanding,
                members.c.notional_num_shares,
            )
            .select_from(
                members.join(
                    marketdata,
                    (members.c.date == marketdata.c.date)
                    & (members.c.stock == marketdata.c.stock),
                )
            )
            .where(members.c.date.in_(dates))
        ).fetchall()

    grouped_members = {}
    result_sorted = sorted(result, key=lambda r: r.date)
    for k, g in groupby(result_sorted, key=lambda r: r.date):
        grouped_members[k] = list(g)

    for target_date in dates:
        if target_date not in indexlevels_map:
            raise ValueError(f"No index level for {target_date}")
        if target_date not in grouped_members:
            raise ValueError(f"No index members for {target_date}")

        effective_divisor = 1
        if target_date != base_date:
            effective_divisor = indexlevels_map[target_date]

        index_members = []
        for row in grouped_members[target_date]:
            stock = Stock(
                stock=row.stock,
                price=row.price,
                shares_outstanding=row.shares_outstanding,
            )
            member = IndexMember(
                stock=stock, notional_num_shares=row.notional_num_shares
            )
            index_members.append(member)

        indexes[target_date] = EWIIndex100(
            date=target_date,
            base_date=base_date,
            base_value=base_value,
            divisor=effective_divisor,
            members=index_members,
        )

    return indexes


def load_changes_for_dates(dates: List[date]) -> Dict[date, List[Change]]:
    """
    Loads changes in index composition for a list of dates from the database.
    Returns { date: [Change, Change, ...] }

    """
    engine = get_engine()
    metadata = get_metadata()

    changes_table = Table("changes", metadata, autoload_with=engine)
    marketdata = Table("marketdata", metadata, autoload_with=engine)

    changes_by_date: Dict[date, List[Change]] = {}

    with engine.begin() as conn:
        # Bulk fetch index composition changes.
        # Join with price data to enrich the stock.
        result = conn.execute(
            select(
                changes_table.c.date,
                changes_table.c.kind,
                changes_table.c.stock,
                marketdata.c.price,
                marketdata.c.shares_outstanding,
            )
            .select_from(
                changes_table.join(
                    marketdata,
                    (changes_table.c.date == marketdata.c.date)
                    & (changes_table.c.stock == marketdata.c.stock),
                )
            )
            .where(changes_table.c.date.in_(dates))
        ).fetchall()

    # Group by date, compose into domain models.
    for row in result:
        row_date = row.date
        stock = Stock(
            stock=row.stock, price=row.price, shares_outstanding=row.shares_outstanding
        )
        change = Change(date=row_date, kind=row.kind, stock=stock)
        changes_by_date.setdefault(row_date, []).append(change)

    return changes_by_date


def persist_index(index: EWIIndex100):
    """
    Stores the index level and members data.
    Does NOT write price or shares_outstanding to marketdata —
    assumes marketdata is managed separately.

    """
    engine = get_engine()
    metadata = get_metadata()

    indexlevels = Table("indexlevels", metadata, autoload_with=engine)
    members_table = Table("members", metadata, autoload_with=engine)

    with engine.begin() as conn:
        # Insert/replace index level
        stmt = (
            sqlite_insert(indexlevels)
            .values(
                date=index.date,
                level=index.value,
                divisor=index.divisor,
            )
            .prefix_with("OR REPLACE")
        )
        conn.execute(stmt)

        # Insert/replace members — only notional_num_shares
        member_rows = [
            {
                "date": index.date,
                "stock": member.stock.stock,
                "notional_num_shares": member.notional_num_shares,
            }
            for member in index.members
        ]

        stmt_members = sqlite_insert(members_table).prefix_with("OR REPLACE")
        conn.execute(stmt_members, member_rows)


def persist_changes(changes: List[Change]) -> None:
    """
    Takes list of Change models, representing changes to index compositions,
    and stores the data in the changes table.

    This is an idempotent operation which can be run many times, each
    run refreshes the data in the table.

    """
    if not changes:
        return

    engine = get_engine()
    metadata = get_metadata()
    changes_table = metadata.tables["changes"]

    rows = []
    for c in changes:
        rows.append(
            {
                "date": c.date,
                "kind": c.kind.value if hasattr(c.kind, "value") else str(c.kind),
                "stock": c.stock.stock,
            }
        )

    stmt = insert(changes_table).prefix_with("OR REPLACE")

    with engine.begin() as conn:
        conn.execute(stmt, rows)
