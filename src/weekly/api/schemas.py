from datetime import date, datetime

from pydantic import BaseModel


class DBStatus(BaseModel):
    sqlite_size_mb: float
    duckdb_size_mb: float
    total_tickers: int
    active_tickers: int
    daily_candle_count: int
    weekly_candle_count: int
    daily_feature_count: int
    weekly_feature_count: int
    oldest_daily_date: date | None
    newest_daily_date: date | None


class LastUpdate(BaseModel):
    job_name: str
    trigger_type: str
    status: str
    tickers_total: int | None
    tickers_success: int | None
    tickers_failed: int | None
    started_at: datetime
    completed_at: datetime | None


class StaleTicker(BaseModel):
    symbol: str
    timeframe: str
    latest_candle_date: date
    days_stale: int


class SchedulerJob(BaseModel):
    id: str
    name: str
    next_run: str | None


class DashboardData(BaseModel):
    db_status: DBStatus
    last_update: LastUpdate | None
    stale_tickers: list[StaleTicker]
    scheduler_jobs: list[SchedulerJob]
    ingestion_running: bool
    registered_features: list[str]


class ManualUpdateRequest(BaseModel):
    symbols: list[str] | None = None
    timeframes: list[str] = ["daily", "weekly"]


class ManualUpdateResponse(BaseModel):
    message: str
    started: bool


class FeatureComputeRequest(BaseModel):
    symbols: list[str] | None = None
    timeframes: list[str] = ["daily", "weekly"]
