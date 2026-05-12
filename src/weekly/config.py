from enum import Enum
from functools import lru_cache
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Environment(str, Enum):
    DEVELOPMENT = "development"
    PRODUCTION = "production"
    TESTING = "testing"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="WEEKLY_", env_file=".env", extra="ignore")

    env: Environment = Environment.DEVELOPMENT
    data_dir: Path = Path("./data")
    sqlite_url: str = "sqlite:///./data/metadata.sqlite"
    duckdb_path: Path = Path("./data/analytics.duckdb")

    log_level: str = "INFO"
    log_format: str = "console"

    yfinance_max_retries: int = 3
    yfinance_retry_delay: float = 2.0
    yfinance_rate_limit_per_second: float = 2.0
    history_years: int = 7
    min_market_cap: int = 1_000_000_000

    schedule_after_close_hour: int = 17
    schedule_after_close_minute: int = 0
    schedule_before_open_hour: int = 1
    schedule_before_open_minute: int = 30
    schedule_timezone: str = "US/Eastern"

    fastapi_host: str = "0.0.0.0"
    fastapi_port: int = 8000
    debug_csv: bool = False

    @field_validator("data_dir", mode="before")
    @classmethod
    def ensure_data_dir(cls, v: str | Path) -> Path:
        p = Path(v)
        p.mkdir(parents=True, exist_ok=True)
        return p


@lru_cache
def get_settings() -> Settings:
    return Settings()
