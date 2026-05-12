import threading
import time
from dataclasses import dataclass, field
from datetime import date, datetime

import pandas as pd
import structlog

from weekly.config import Settings
from weekly.db.duckdb import DuckDBManager
from weekly.db.models import IngestionLog, SchedulerState
from weekly.db.sqlite import session_scope
from weekly.features.registry import FeatureRegistry
from weekly.ingestion.diff import DiffCalculator
from weekly.ingestion.fetcher import YFinanceFetcher
from weekly.ingestion.universe import TickerUniverse

logger = structlog.get_logger(__name__)


@dataclass
class IngestionResult:
    symbol: str
    timeframe: str
    status: str
    rows_fetched: int = 0
    rows_inserted: int = 0
    features_inserted: int = 0
    latest_candle_date: date | None = None
    error: str | None = None
    duration: float = 0.0


@dataclass
class FullUpdateResult:
    trigger_type: str
    results: list[IngestionResult] = field(default_factory=list)
    started_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: datetime | None = None

    @property
    def total(self) -> int:
        return len(self.results)

    @property
    def success_count(self) -> int:
        return sum(1 for r in self.results if r.status == "success")

    @property
    def failed_count(self) -> int:
        return sum(1 for r in self.results if r.status == "failed")

    @property
    def skipped_count(self) -> int:
        return sum(1 for r in self.results if r.status == "skipped")


class IngestionEngine:
    def __init__(
        self,
        fetcher: YFinanceFetcher,
        diff: DiffCalculator,
        universe: TickerUniverse,
        duckdb_manager: DuckDBManager,
        settings: Settings,
    ) -> None:
        self._fetcher = fetcher
        self._diff = diff
        self._universe = universe
        self._duckdb = duckdb_manager
        self._settings = settings
        self._running = threading.Event()
        self._feature_registry = FeatureRegistry.get_instance()

    @property
    def is_running(self) -> bool:
        return self._running.is_set()

    def ingest_ticker(self, symbol: str, timeframe: str) -> IngestionResult:
        start_time = time.monotonic()
        result = IngestionResult(symbol=symbol, timeframe=timeframe, status="started")

        try:
            fetch_start, fetch_end = self._diff.calculate_fetch_range(
                symbol, timeframe, self._settings.history_years
            )

            if fetch_start >= fetch_end:
                result.status = "skipped"
                result.duration = time.monotonic() - start_time
                return result

            df = self._fetcher.fetch_history(symbol, fetch_start, fetch_end, timeframe)
            result.rows_fetched = len(df)

            if df.empty:
                result.status = "skipped"
                result.duration = time.monotonic() - start_time
                return result

            rows_inserted = self._diff.insert_candles(symbol, timeframe, df)
            result.rows_inserted = rows_inserted

            features_df = self._compute_features(symbol, timeframe)
            if not features_df.empty:
                result.features_inserted = self._diff.insert_features(
                    symbol, timeframe, features_df
                )

            result.latest_candle_date = df["date"].max()
            result.status = "success"

            if self._settings.debug_csv:
                self._dump_csv(symbol, timeframe, df)

        except Exception as e:
            result.status = "failed"
            result.error = str(e)
            logger.error(
                "ingestion_failed", symbol=symbol, timeframe=timeframe, error=str(e)
            )
        finally:
            result.duration = time.monotonic() - start_time
            self._log_ingestion(result)

        return result

    def _compute_features(self, symbol: str, timeframe: str) -> pd.DataFrame:
        table = "daily_candles" if timeframe == "daily" else "weekly_candles"
        with self._duckdb.read_connection() as conn:
            df = conn.execute(
                f"SELECT date, open, high, low, close, adj_close, volume "
                f"FROM {table} WHERE symbol = ? ORDER BY date",
                [symbol],
            ).fetchdf()

        if df.empty:
            return pd.DataFrame()

        return self._feature_registry.compute_all(df)

    def run_full_update(
        self,
        symbols: list[str] | None = None,
        timeframes: list[str] | None = None,
        trigger_type: str = "manual",
    ) -> FullUpdateResult:
        if self._running.is_set():
            logger.warning("ingestion_already_running")
            return FullUpdateResult(trigger_type=trigger_type)

        self._running.set()
        update_result = FullUpdateResult(trigger_type=trigger_type)

        try:
            if symbols is None:
                symbols = self._universe.get_active_symbols()
            if timeframes is None:
                timeframes = ["daily", "weekly"]

            total = len(symbols) * len(timeframes)
            logger.info(
                "ingestion_started",
                trigger=trigger_type,
                tickers=len(symbols),
                timeframes=timeframes,
                total_jobs=total,
            )

            for i, symbol in enumerate(symbols):
                for timeframe in timeframes:
                    result = self.ingest_ticker(symbol, timeframe)
                    update_result.results.append(result)
                    if (i + 1) % 50 == 0:
                        logger.info(
                            "ingestion_progress",
                            completed=i + 1,
                            total_tickers=len(symbols),
                        )

            update_result.completed_at = datetime.utcnow()
            self._log_scheduler_state(update_result)

            logger.info(
                "ingestion_completed",
                trigger=trigger_type,
                total=update_result.total,
                success=update_result.success_count,
                failed=update_result.failed_count,
                skipped=update_result.skipped_count,
            )

        finally:
            self._running.clear()

        return update_result

    def _log_ingestion(self, result: IngestionResult) -> None:
        try:
            with session_scope() as session:
                log = IngestionLog(
                    symbol=result.symbol,
                    timeframe=result.timeframe,
                    status=result.status,
                    rows_fetched=result.rows_fetched,
                    rows_inserted=result.rows_inserted,
                    latest_candle_date=result.latest_candle_date,
                    error_message=result.error,
                    duration_seconds=result.duration,
                    started_at=datetime.utcnow(),
                    completed_at=datetime.utcnow() if result.status != "started" else None,
                )
                session.add(log)
        except Exception as e:
            logger.error("failed_to_log_ingestion", error=str(e))

    def _log_scheduler_state(self, update: FullUpdateResult) -> None:
        try:
            with session_scope() as session:
                state = SchedulerState(
                    job_name="full_update",
                    trigger_type=update.trigger_type,
                    status="completed",
                    tickers_total=update.total,
                    tickers_success=update.success_count,
                    tickers_failed=update.failed_count,
                    started_at=update.started_at,
                    completed_at=update.completed_at,
                )
                session.add(state)
        except Exception as e:
            logger.error("failed_to_log_scheduler_state", error=str(e))

    def _dump_csv(self, symbol: str, timeframe: str, df: pd.DataFrame) -> None:
        csv_dir = self._settings.data_dir / "debug_csv"
        csv_dir.mkdir(parents=True, exist_ok=True)
        path = csv_dir / f"{symbol}_{timeframe}.csv"
        df.to_csv(path, index=False)
