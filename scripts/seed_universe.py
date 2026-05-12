#!/usr/bin/env python3
"""Populate the tickers table with S&P 500 companies from Wikipedia."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from weekly.config import get_settings
from weekly.db.sqlite import init_sqlite
from weekly.ingestion.fetcher import YFinanceFetcher
from weekly.ingestion.universe import TickerUniverse
from weekly.logging_setup import setup_logging, get_logger


def main() -> None:
    settings = get_settings()
    setup_logging(settings.log_level, settings.log_format)
    log = get_logger("seed_universe")

    init_sqlite(settings.sqlite_url)

    fetcher = YFinanceFetcher(settings)
    universe = TickerUniverse(settings, fetcher)

    log.info("seeding_universe")
    added = universe.refresh_from_sp500()
    log.info("seed_complete", added=added, total=universe.get_active_count())

    symbols = universe.get_active_symbols()
    print(f"\nSeeded {len(symbols)} tickers. First 10: {symbols[:10]}")


if __name__ == "__main__":
    main()
