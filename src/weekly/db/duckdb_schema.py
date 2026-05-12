import duckdb

DAILY_CANDLES_DDL = """
CREATE TABLE IF NOT EXISTS daily_candles (
    symbol VARCHAR NOT NULL,
    date DATE NOT NULL,
    open DOUBLE,
    high DOUBLE,
    low DOUBLE,
    close DOUBLE,
    adj_close DOUBLE,
    volume BIGINT,
    dividends DOUBLE DEFAULT 0,
    splits DOUBLE DEFAULT 0,
    PRIMARY KEY (symbol, date)
);
"""

WEEKLY_CANDLES_DDL = """
CREATE TABLE IF NOT EXISTS weekly_candles (
    symbol VARCHAR NOT NULL,
    date DATE NOT NULL,
    open DOUBLE,
    high DOUBLE,
    low DOUBLE,
    close DOUBLE,
    adj_close DOUBLE,
    volume BIGINT,
    dividends DOUBLE DEFAULT 0,
    splits DOUBLE DEFAULT 0,
    PRIMARY KEY (symbol, date)
);
"""

DAILY_FEATURES_DDL = """
CREATE TABLE IF NOT EXISTS daily_features (
    symbol VARCHAR NOT NULL,
    date DATE NOT NULL,
    feature_name VARCHAR NOT NULL,
    value DOUBLE,
    PRIMARY KEY (symbol, date, feature_name)
);
"""

WEEKLY_FEATURES_DDL = """
CREATE TABLE IF NOT EXISTS weekly_features (
    symbol VARCHAR NOT NULL,
    date DATE NOT NULL,
    feature_name VARCHAR NOT NULL,
    value DOUBLE,
    PRIMARY KEY (symbol, date, feature_name)
);
"""

ALL_DDL = [DAILY_CANDLES_DDL, WEEKLY_CANDLES_DDL, DAILY_FEATURES_DDL, WEEKLY_FEATURES_DDL]


def initialize_duckdb_schema(conn: duckdb.DuckDBPyConnection) -> None:
    for ddl in ALL_DDL:
        conn.execute(ddl)
