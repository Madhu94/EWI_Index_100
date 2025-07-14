"""
Contains Pydantic models representing the entities - the Index,
each Stock, Index Member (stock + weight), a Change in the composition
of the index

"""

from datetime import date
from enum import Enum
from typing import ClassVar, List, Optional

from pydantic import BaseModel, model_validator

from .constants import INDEX_SIZE


class Stock(BaseModel):
    """
    Represents a single stock ticker and its properties.
    The Stock may/may not be part of the Index

    """

    stock: str  # Ticker name
    price: float
    shares_outstanding: float

    @property
    def market_cap(self) -> float:
        return self.price * self.shares_outstanding

    # We want comparison only based on the stock tickers
    def __hash__(self) -> int:
        return hash(self.stock)

    def __eq__(self, other) -> bool:
        if isinstance(other, Stock):
            return self.stock == other.stock
        return False

    class Config:  # Freeze the object to make it hashable
        frozen = True


class IndexMember(BaseModel):
    """
    Represents a member of the index - this would constitute a stock and a
    notional number of shares of the stock.

    """

    stock: Stock
    notional_num_shares: float

    @property
    def market_cap(self) -> float:
        return self.stock.market_cap

    class Config:
        frozen = True  # Freeze the object to make it hashable


class EWIIndex100(BaseModel):
    """ """

    # TODO: This is a temporary workaround for the purpose
    # of ovecoming rate limits. This should be set to 100. Issue documented in README.
    MAX_MEMBERS: ClassVar[int] = INDEX_SIZE

    date: date
    base_date: date
    base_value: float
    _divisor: Optional[float] = 1
    members: List[IndexMember]

    @model_validator(mode="after")
    def validate_all(self):
        if self.date < self.base_date:
            raise ValueError(f"Date {self.date} must be >= base_date {self.base_date}")

        if self.date != self.base_date and self._divisor is None:
            # rely on caller to pass in the divisor of previous date here or the divisor post adjustment.
            raise ValueError(
                "Effective divisor must be provided for dates other than base_date"
            )

        if len(self.members) != self.MAX_MEMBERS:
            raise ValueError(
                f"SP100 must have exactly {self.MAX_MEMBERS} member stocks"
            )

        return self

    @property
    def divisor(self):
        return self._divisor

    @divisor.setter
    def divisor(self, val) -> float:
        if self.date == self.base_date:
            total_market_value = sum(
                m.stock.price * m.notional_num_shares for m in self.members
            )
            self._divisor = total_market_value / self.base_value
        else:
            assert val is not None
            self._divisor = val

    @property
    def value(self) -> float:
        """
        Represents the index level.

        """
        total_market_value = sum(
            m.stock.price * m.notional_num_shares for m in self.members
        )
        return total_market_value / self.divisor


class IndexOperation(str, Enum):
    """
    Represents the kind of change that can happen to an index composition.

    We can do one of the following:

    * ADD - a new stock is added to the index, when its market cap is among
    the top 100 stocks by market cap.
    * REMOVE - a stock which is part of the index is removed, when its market
    cap is no longer among the top 100 stocks by market cap
    * REBALANCE - a stock which is part of the index has its notional number
    of shares adjusted so that it contributes an equal notional value to the index

    """

    ADD = "ADD"
    REMOVE = "REMOVE"
    REBALANCE = "REBALANCE"


class Change(BaseModel):
    """
    Represents a single change to the composition of the EWIIndex100.

    This could constitute one of the IndexOperations - ADD, REMOVE, REBALANCE
    along with the date of the change and the stock involved.

    """

    date: date
    kind: IndexOperation
    stock: Stock
