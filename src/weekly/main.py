from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

from fastapi import FastAPI

from weekly.api.router import router
from weekly.config import get_settings
from weekly.db.duckdb import DuckDBManager
from weekly.db.sqlite import init_sqlite
from weekly.features import FeatureRegistry  # triggers feature registration
from weekly.ingestion.diff import DiffCalculator
from weekly.ingestion.engine import IngestionEngine
from weekly.ingestion.fetcher import YFinanceFetcher
from weekly.ingestion.universe import TickerUniverse
from weekly.logging_setup import get_logger, setup_logging
from weekly.scheduler.jobs import SchedulerManager


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    settings = get_settings()

    setup_logging(settings.log_level, settings.log_format)
    log = get_logger("weekly.main")
    log.info("starting", env=settings.env.value)

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

    scheduler = SchedulerManager(engine, settings)
    scheduler.start()

    app.state.settings = settings
    app.state.duckdb = duckdb_mgr
    app.state.ingestion_engine = engine
    app.state.universe = universe
    app.state.scheduler = scheduler

    registry = FeatureRegistry.get_instance()
    log.info("ready", features=len(registry.list_names()))

    yield

    scheduler.shutdown()
    duckdb_mgr.close()
    log.info("shutdown_complete")


def create_app() -> FastAPI:
    app = FastAPI(
        title="Trading Research Platform",
        version="0.1.0",
        lifespan=lifespan,
    )
    app.include_router(router)
    return app


app = create_app()
