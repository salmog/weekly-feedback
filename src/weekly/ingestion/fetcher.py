import threading
import time
from datetime import date

import pandas as pd
import structlog
import yfinance as yf
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from weekly.config import Settings

logger = structlog.get_logger(__name__)


class IngestionError(Exception):
    pass


class RateLimiter:
    def __init__(self, calls_per_second: float) -> None:
        self._min_interval = 1.0 / calls_per_second
        self._lock = threading.Lock()
        self._last_call: float = 0.0

    def acquire(self) -> None:
        with self._lock:
            now = time.monotonic()
            elapsed = now - self._last_call
            if elapsed < self._min_interval:
                time.sleep(self._min_interval - elapsed)
            self._last_call = time.monotonic()


class YFinanceFetcher:
    INTERVAL_MAP = {"daily": "1d", "weekly": "1wk"}

    def __init__(self, settings: Settings) -> None:
        self._rate_limiter = RateLimiter(settings.yfinance_rate_limit_per_second)
        self._max_retries = settings.yfinance_max_retries
        self._retry_delay = settings.yfinance_retry_delay

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=2, min=1, max=30),
        retry=retry_if_exception_type((ConnectionError, TimeoutError, OSError)),
    )
    def fetch_history(
        self,
        symbol: str,
        start: date,
        end: date,
        timeframe: str = "daily",
    ) -> pd.DataFrame:
        self._rate_limiter.acquire()
        interval = self.INTERVAL_MAP.get(timeframe)
        if not interval:
            raise IngestionError(f"Unknown timeframe: {timeframe}")

        logger.debug("fetching_history", symbol=symbol, start=str(start), end=str(end), interval=interval)
        ticker = yf.Ticker(symbol)
        df = ticker.history(start=str(start), end=str(end), interval=interval, auto_adjust=False)

        if df.empty:
            logger.warning("no_data_returned", symbol=symbol, start=str(start), end=str(end))
            return pd.DataFrame()

        df = df.reset_index()
        date_col = "Date" if "Date" in df.columns else df.columns[0]
        rename_map = {
            date_col: "date",
            "Open": "open",
            "High": "high",
            "Low": "low",
            "Close": "close",
            "Adj Close": "adj_close",
            "Volume": "volume",
            "Dividends": "dividends",
            "Stock Splits": "splits",
        }
        df = df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns})

        if "date" in df.columns:
            df["date"] = pd.to_datetime(df["date"]).dt.date

        expected = ["date", "open", "high", "low", "close", "volume"]
        missing = [c for c in expected if c not in df.columns]
        if missing:
            raise IngestionError(f"Missing columns for {symbol}: {missing}")

        if "adj_close" not in df.columns:
            df["adj_close"] = df["close"]
        if "dividends" not in df.columns:
            df["dividends"] = 0.0
        if "splits" not in df.columns:
            df["splits"] = 0.0

        df["symbol"] = symbol
        cols = ["symbol", "date", "open", "high", "low", "close", "adj_close", "volume", "dividends", "splits"]
        return df[cols]

    def fetch_ticker_info(self, symbol: str) -> dict:
        self._rate_limiter.acquire()
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info or {}
            return {
                "company_name": info.get("longName") or info.get("shortName"),
                "sector": info.get("sector"),
                "industry": info.get("industry"),
                "market_cap": info.get("marketCap"),
            }
        except Exception as e:
            logger.warning("ticker_info_failed", symbol=symbol, error=str(e))
            return {}
