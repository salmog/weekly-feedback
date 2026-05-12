import os
from datetime import date, datetime

import structlog
from fastapi import APIRouter, BackgroundTasks, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from weekly.api.schemas import (
    DBStatus,
    DashboardData,
    LastUpdate,
    ManualUpdateRequest,
    ManualUpdateResponse,
    SchedulerJob,
    StaleTicker,
)
from weekly.db.models import SchedulerState
from weekly.db.sqlite import session_scope
from weekly.features.registry import FeatureRegistry

logger = structlog.get_logger(__name__)

router = APIRouter()
templates = Jinja2Templates(
    directory=os.path.join(os.path.dirname(__file__), "templates")
)


def _get_db_status(request: Request) -> DBStatus:
    duckdb_mgr = request.app.state.duckdb
    settings = request.app.state.settings
    universe = request.app.state.universe

    sqlite_path = settings.data_dir / "metadata.sqlite"
    duckdb_path = settings.duckdb_path

    sqlite_size = sqlite_path.stat().st_size / (1024 * 1024) if sqlite_path.exists() else 0.0
    duckdb_size = duckdb_path.stat().st_size / (1024 * 1024) if duckdb_path.exists() else 0.0

    with duckdb_mgr.read_connection() as conn:
        daily_count = conn.execute("SELECT COUNT(*) FROM daily_candles").fetchone()[0]
        weekly_count = conn.execute("SELECT COUNT(*) FROM weekly_candles").fetchone()[0]
        daily_feat_count = conn.execute("SELECT COUNT(*) FROM daily_features").fetchone()[0]
        weekly_feat_count = conn.execute("SELECT COUNT(*) FROM weekly_features").fetchone()[0]

        oldest = conn.execute("SELECT MIN(date) FROM daily_candles").fetchone()[0]
        newest = conn.execute("SELECT MAX(date) FROM daily_candles").fetchone()[0]

    return DBStatus(
        sqlite_size_mb=round(sqlite_size, 2),
        duckdb_size_mb=round(duckdb_size, 2),
        total_tickers=universe.get_total_count(),
        active_tickers=universe.get_active_count(),
        daily_candle_count=daily_count,
        weekly_candle_count=weekly_count,
        daily_feature_count=daily_feat_count,
        weekly_feature_count=weekly_feat_count,
        oldest_daily_date=oldest,
        newest_daily_date=newest,
    )


def _get_last_update() -> LastUpdate | None:
    with session_scope() as session:
        state = (
            session.query(SchedulerState)
            .order_by(SchedulerState.started_at.desc())
            .first()
        )
        if not state:
            return None
        return LastUpdate(
            job_name=state.job_name,
            trigger_type=state.trigger_type,
            status=state.status,
            tickers_total=state.tickers_total,
            tickers_success=state.tickers_success,
            tickers_failed=state.tickers_failed,
            started_at=state.started_at,
            completed_at=state.completed_at,
        )


def _get_stale_tickers(request: Request, threshold_days: int = 3) -> list[StaleTicker]:
    duckdb_mgr = request.app.state.duckdb
    today = date.today()
    stale: list[StaleTicker] = []

    for timeframe, table in [("daily", "daily_candles"), ("weekly", "weekly_candles")]:
        with duckdb_mgr.read_connection() as conn:
            rows = conn.execute(
                f"SELECT symbol, MAX(date) as latest FROM {table} GROUP BY symbol"
            ).fetchall()
        for symbol, latest in rows:
            if latest is None:
                continue
            if isinstance(latest, datetime):
                latest = latest.date()
            days_stale = (today - latest).days
            if days_stale > threshold_days:
                stale.append(
                    StaleTicker(
                        symbol=symbol,
                        timeframe=timeframe,
                        latest_candle_date=latest,
                        days_stale=days_stale,
                    )
                )

    stale.sort(key=lambda s: s.days_stale, reverse=True)
    return stale


@router.get("/", response_class=HTMLResponse)
async def dashboard(request: Request) -> HTMLResponse:
    data = _build_dashboard_data(request)
    return templates.TemplateResponse(request, "dashboard.html", {"data": data})


@router.get("/api/status", response_model=DashboardData)
async def get_status(request: Request) -> DashboardData:
    return _build_dashboard_data(request)


@router.get("/api/db-status", response_model=DBStatus)
async def get_db_status(request: Request) -> DBStatus:
    return _get_db_status(request)


@router.get("/api/stale-tickers", response_model=list[StaleTicker])
async def get_stale_tickers(request: Request, threshold_days: int = 3) -> list[StaleTicker]:
    return _get_stale_tickers(request, threshold_days)


@router.post("/api/update", response_model=ManualUpdateResponse)
async def trigger_manual_update(
    req: ManualUpdateRequest,
    request: Request,
    background_tasks: BackgroundTasks,
) -> ManualUpdateResponse:
    engine = request.app.state.ingestion_engine
    if engine.is_running:
        return ManualUpdateResponse(message="Ingestion already running", started=False)

    background_tasks.add_task(
        engine.run_full_update,
        symbols=req.symbols,
        timeframes=req.timeframes,
        trigger_type="manual",
    )
    return ManualUpdateResponse(message="Ingestion started", started=True)


def _build_dashboard_data(request: Request) -> DashboardData:
    engine = request.app.state.ingestion_engine
    scheduler = request.app.state.scheduler

    scheduler_jobs = [
        SchedulerJob(id=j["id"], name=j["name"], next_run=j["next_run"])
        for j in scheduler.get_jobs_info()
    ]

    registry = FeatureRegistry.get_instance()

    return DashboardData(
        db_status=_get_db_status(request),
        last_update=_get_last_update(),
        stale_tickers=_get_stale_tickers(request),
        scheduler_jobs=scheduler_jobs,
        ingestion_running=engine.is_running,
        registered_features=registry.list_names(),
    )
