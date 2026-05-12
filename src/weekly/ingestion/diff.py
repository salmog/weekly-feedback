from datetime import date, timedelta

import pandas as pd
import structlog

from weekly.db.duckdb import DuckDBManager

logger = structlog.get_logger(__name__)

CANDLE_TABLES = {"daily": "daily_candles", "weekly": "weekly_candles"}
FEATURE_TABLES = {"daily": "daily_features", "weekly": "weekly_features"}


class DiffCalculator:
    def __init__(self, duckdb_manager: DuckDBManager) -> None:
        self._duckdb = duckdb_manager

    def get_latest_candle_date(self, symbol: str, timeframe: str) -> date | None:
        table = CANDLE_TABLES[timeframe]
        with self._duckdb.read_connection() as conn:
            result = conn.execute(
                f"SELECT MAX(date) FROM {table} WHERE symbol = ?", [symbol]
            ).fetchone()
            if result and result[0]:
                val = result[0]
                if isinstance(val, date):
                    return val
                return pd.Timestamp(val).date()
            return None

    def calculate_fetch_range(
        self, symbol: str, timeframe: str, history_years: int
    ) -> tuple[date, date]:
        latest = self.get_latest_candle_date(symbol, timeframe)
        end = date.today()
        if latest is None:
            start = end - timedelta(days=history_years * 365)
        else:
            start = latest + timedelta(days=1)
        return start, end

    def needs_fetch(self, symbol: str, timeframe: str, history_years: int) -> bool:
        start, end = self.calculate_fetch_range(symbol, timeframe, history_years)
        return start < end

    def insert_candles(self, symbol: str, timeframe: str, df: pd.DataFrame) -> int:
        if df.empty:
            return 0
        table = CANDLE_TABLES[timeframe]
        with self._duckdb.write_connection() as conn:
            conn.execute(f"DELETE FROM {table} WHERE symbol = ? AND date >= ? AND date <= ?", [
                symbol,
                df["date"].min(),
                df["date"].max(),
            ])
            count = len(df)
            conn.execute(
                f"INSERT INTO {table} SELECT * FROM df"  # noqa: S608
            )
            logger.info("candles_inserted", symbol=symbol, timeframe=timeframe, rows=count)
            return count

    def insert_features(self, symbol: str, timeframe: str, features_df: pd.DataFrame) -> int:
        if features_df.empty:
            return 0
        table = FEATURE_TABLES[timeframe]
        features_df = features_df.dropna(subset=["value"])
        if features_df.empty:
            return 0
        features_df = features_df.copy()
        features_df["symbol"] = symbol
        insert_df = features_df[["symbol", "date", "feature_name", "value"]]

        with self._duckdb.write_connection() as conn:
            min_date = insert_df["date"].min()
            max_date = insert_df["date"].max()
            conn.execute(
                f"DELETE FROM {table} WHERE symbol = ? AND date >= ? AND date <= ?",
                [symbol, min_date, max_date],
            )
            conn.execute(f"INSERT INTO {table} SELECT * FROM insert_df")  # noqa: S608
            return len(insert_df)
