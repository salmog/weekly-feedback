from datetime import datetime
from io import StringIO

import httpx
import pandas as pd
import structlog
from sqlalchemy.orm import Session

from weekly.config import Settings
from weekly.db.models import Ticker
from weekly.db.sqlite import session_scope
from weekly.ingestion.fetcher import YFinanceFetcher

logger = structlog.get_logger(__name__)

SP500_WIKI_URL = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"


class TickerUniverse:
    def __init__(self, settings: Settings, fetcher: YFinanceFetcher | None = None) -> None:
        self._settings = settings
        self._fetcher = fetcher

    def get_active_symbols(self) -> list[str]:
        with session_scope() as session:
            tickers = session.query(Ticker).filter(Ticker.is_active.is_(True)).all()
            return [t.symbol for t in tickers]

    def get_active_count(self) -> int:
        with session_scope() as session:
            return session.query(Ticker).filter(Ticker.is_active.is_(True)).count()

    def get_total_count(self) -> int:
        with session_scope() as session:
            return session.query(Ticker).count()

    def add_ticker(self, symbol: str, session: Session | None = None) -> Ticker:
        def _add(s: Session) -> Ticker:
            existing = s.query(Ticker).filter(Ticker.symbol == symbol).first()
            if existing:
                existing.is_active = True
                existing.updated_at = datetime.utcnow()
                return existing
            ticker = Ticker(symbol=symbol.upper())
            s.add(ticker)
            return ticker

        if session:
            return _add(session)
        with session_scope() as s:
            return _add(s)

    def deactivate_ticker(self, symbol: str) -> None:
        with session_scope() as session:
            ticker = session.query(Ticker).filter(Ticker.symbol == symbol).first()
            if ticker:
                ticker.is_active = False
                ticker.updated_at = datetime.utcnow()

    def seed_from_list(self, symbols: list[str]) -> int:
        """Seed tickers from an explicit list of symbols."""
        added = 0
        with session_scope() as session:
            for sym in symbols:
                sym = sym.strip().upper()
                if not sym:
                    continue
                existing = session.query(Ticker).filter(Ticker.symbol == sym).first()
                if not existing:
                    session.add(Ticker(symbol=sym))
                    added += 1
                elif not existing.is_active:
                    existing.is_active = True
                    existing.updated_at = datetime.utcnow()
                    added += 1
        logger.info("seeded_from_list", total=len(symbols), added=added)
        return added

    def refresh_from_sp500(self) -> int:
        """Fetch S&P 500 list from Wikipedia and populate tickers table."""
        logger.info("refreshing_universe_from_sp500")
        try:
            resp = httpx.get(
                SP500_WIKI_URL,
                headers={"User-Agent": "WeeklyTradingResearch/0.1"},
                follow_redirects=True,
                timeout=15,
            )
            resp.raise_for_status()
            tables = pd.read_html(StringIO(resp.text))
            sp500_df = tables[0]
            symbols = sp500_df["Symbol"].str.replace(".", "-", regex=False).tolist()
        except Exception as e:
            logger.error("sp500_fetch_failed", error=str(e))
            return 0

        added = 0
        with session_scope() as session:
            for sym in symbols:
                existing = session.query(Ticker).filter(Ticker.symbol == sym).first()
                if not existing:
                    session.add(Ticker(symbol=sym))
                    added += 1
                elif not existing.is_active:
                    existing.is_active = True
                    existing.updated_at = datetime.utcnow()
                    added += 1

        logger.info("universe_refreshed", total_symbols=len(symbols), new_added=added)
        return added

    def enrich_ticker_info(self, symbol: str) -> None:
        """Fetch and store company info for a ticker via yfinance."""
        if not self._fetcher:
            return
        info = self._fetcher.fetch_ticker_info(symbol)
        if not info:
            return
        with session_scope() as session:
            ticker = session.query(Ticker).filter(Ticker.symbol == symbol).first()
            if ticker:
                if info.get("company_name"):
                    ticker.company_name = info["company_name"]
                if info.get("sector"):
                    ticker.sector = info["sector"]
                if info.get("industry"):
                    ticker.industry = info["industry"]
                if info.get("market_cap"):
                    ticker.market_cap = info["market_cap"]
                ticker.updated_at = datetime.utcnow()
