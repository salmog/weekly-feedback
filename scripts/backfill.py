#!/usr/bin/env python3
"""Run a full historical backfill for all active tickers."""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from weekly.config import get_settings
from weekly.db.duckdb import DuckDBManager
from weekly.db.sqlite import init_sqlite
from weekly.ingestion.diff import DiffCalculator
from weekly.ingestion.engine import IngestionEngine
from weekly.ingestion.fetcher import YFinanceFetcher
from weekly.ingestion.universe import TickerUniverse
from weekly.logging_setup import setup_logging, get_logger

import weekly.features  # noqa: F401  — triggers feature registration


def main() -> None:
    parser = argparse.ArgumentParser(description="Backfill historical data")
    parser.add_argument("--symbols", nargs="*", help="Specific symbols (default: all active)")
    parser.add_argument("--timeframes", nargs="*", default=["daily", "weekly"], help="Timeframes to backfill")
    args = parser.parse_args()

    settings = get_settings()
    setup_logging(settings.log_level, settings.log_format)
    log = get_logger("backfill")

    init_sqlite(settings.sqlite_url)

    duckdb_mgr = DuckDBManager(settings.duckdb_path)
    duckdb_mgr.initialize()

    fetcher = YFinanceFetcher(settings)
    diff = DiffCalculator(duckdb_mgr)
    universe = TickerUniverse(settings, fetcher)

    engine = IngestionEngine(
        fetcher=fetcher,
        diff=diff,
        universe=universe,
        duckdb_manager=duckdb_mgr,
        settings=settings,
    )

    symbols = args.symbols
    if symbols:
        log.info("backfill_start", symbols=symbols, timeframes=args.timeframes)
    else:
        count = universe.get_active_count()
        log.info("backfill_start", total_active_tickers=count, timeframes=args.timeframes)

    result = engine.run_full_update(
        symbols=symbols,
        timeframes=args.timeframes,
        trigger_type="backfill",
    )

    print(f"\nBackfill complete:")
    print(f"  Total:   {result.total}")
    print(f"  Success: {result.success_count}")
    print(f"  Failed:  {result.failed_count}")
    print(f"  Skipped: {result.skipped_count}")

    if result.failed_count > 0:
        failed = [r for r in result.results if r.status == "failed"]
        print(f"\nFailed tickers:")
        for r in failed[:20]:
            print(f"  {r.symbol} ({r.timeframe}): {r.error}")

    duckdb_mgr.close()


if __name__ == "__main__":
    main()
