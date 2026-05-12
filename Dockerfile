FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml .
RUN pip install --no-cache-dir .

COPY . .
RUN pip install --no-cache-dir -e .

RUN mkdir -p /app/data

ENV WEEKLY_DATA_DIR=/app/data
ENV WEEKLY_SQLITE_URL=sqlite:////app/data/metadata.sqlite
ENV WEEKLY_DUCKDB_PATH=/app/data/analytics.duckdb

EXPOSE 8000

CMD ["uvicorn", "weekly.main:app", "--host", "0.0.0.0", "--port", "8000"]
