# Trading Research Platform (Daily + Weekly)

## Quick start

```bash
source .venv/bin/activate
python3.12 scripts/seed_universe.py          # populate S&P 500 tickers
python3.12 scripts/backfill.py --symbols AAPL MSFT  # backfill specific tickers
python3.12 scripts/backfill.py               # backfill all active tickers
uvicorn weekly.main:app --reload             # start dashboard at http://localhost:8000
```

## Architecture

- **DuckDB** (`data/analytics.duckdb`): candle data + computed features (read-heavy analytics)
- **SQLite** (`data/metadata.sqlite`): ticker metadata, ingestion logs, scheduler state
- **APScheduler**: twice-daily cron jobs (post-close 5pm ET, pre-open 1:30am ET)

## Key modules

- `src/weekly/config.py` — all settings via `WEEKLY_*` env vars
- `src/weekly/db/` — database layer (DuckDB + SQLite)
- `src/weekly/ingestion/` — yfinance fetcher, diff calculator, universe, engine
- `src/weekly/features/` — feature engine with decorator-based registration
- `src/weekly/scheduler/` — APScheduler job management
- `src/weekly/api/` — FastAPI routes + dashboard template

## Adding a new feature

Create a class in `src/weekly/features/`, inherit from `FeatureCalculator`, apply `@register_feature`.
Import it in `src/weekly/features/__init__.py`. That's it.

## Commands

- `ruff check src/` — lint
- `mypy src/` — type check
- `pytest` — tests
