"""
Module to fetch

"""

import os
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from typing import Dict, List

import requests

# TODO: Move to a secrets storage system.
FMP_API_KEY = os.environ["API_KEY"]
UNIVERSE = ["AAPL", "MSFT", "GOOG", "V", "NVDA", "RBRK", "META", "AMZN", "JPM", "UNH"]


class MarketDataFetcher:
    def __init__(self):
        self.api_key = FMP_API_KEY
        self.universe = UNIVERSE
        self.chunk_size = 5  # FMP free tier limit

    def fetch(self, target_date: date) -> List[Dict]:
        """
        Fetch historical prices and latest market cap for all tickers in universe.
        Chunked to work within FMP free tier limits.
        Returns: List of rows {date, stock, price, shares_outstanding}
        """
        prices = self._get_prices_chunked(target_date)
        market_caps = self._get_market_caps_chunked()

        rows = []
        for ticker in self.universe:
            price = prices.get(ticker)
            market_cap = market_caps.get(ticker)

            if price is None or market_cap is None:
                print(f"Skipping {ticker} due to missing data.")
                continue

            shares_outstanding = market_cap / price if price else 0
            rows.append(
                {
                    "date": target_date,
                    "stock": ticker,
                    "price": price,
                    "shares_outstanding": shares_outstanding,
                }
            )

        return rows

    def _get_prices_chunked(self, target_date: date) -> Dict[str, float]:
        """
        Fetch historical prices, handling batch chunking.
        """
        prices = {}
        with ThreadPoolExecutor() as executor:
            futures = []
            for i in range(0, len(self.universe), self.chunk_size):
                chunk = self.universe[i : i + self.chunk_size]
                futures.append(
                    executor.submit(self._fetch_prices_batch, chunk, target_date)
                )

            for future in futures:
                prices.update(future.result())
        return prices

    def _fetch_prices_batch(
        self, tickers: List[str], target_date: date
    ) -> Dict[str, float]:
        """
        Calls /historical-price-full for a chunk of tickers.
        """
        symbols_str = ",".join(tickers)
        url = f"https://financialmodelingprep.com/api/v3/historical-price-full/{symbols_str}"
        params = {
            "from": target_date.isoformat(),
            "to": target_date.isoformat(),
            "apikey": self.api_key,
        }
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()

        prices = {}
        for stock in data.get("historicalStockList", []):
            symbol = stock.get("symbol")
            historical = stock.get("historical", [])
            if historical:
                prices[symbol] = historical[0]["close"]
        return prices

    def _get_market_caps_chunked(self) -> Dict[str, float]:
        """
        Fetch latest market cap data using /profile endpoint, chunked.
        """
        market_caps = {}
        with ThreadPoolExecutor() as executor:
            futures = []
            for i in range(0, len(self.universe), self.chunk_size):
                chunk = self.universe[i : i + self.chunk_size]
                futures.append(executor.submit(self._fetch_market_caps_batch, chunk))

            for future in futures:
                market_caps.update(future.result())
        return market_caps

    def _fetch_market_caps_batch(self, tickers: List[str]) -> Dict[str, float]:
        """
        Calls /profile for a chunk of tickers.
        """
        symbols_str = ",".join(tickers)
        url = f"https://financialmodelingprep.com/api/v3/profile/{symbols_str}"
        params = {"apikey": self.api_key}
        response = requests.get(url, params=params)
        response.raise_for_status()
        profiles = response.json()

        market_caps = {}
        for profile in profiles:
            symbol = profile.get("symbol")
            mkt_cap = profile.get("mktCap")
            if symbol and mkt_cap:
                market_caps[symbol] = mkt_cap
        return market_caps
