from collections.abc import Generator
from contextlib import contextmanager

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from weekly.db.models import Base

_engine: Engine | None = None
_session_factory: sessionmaker[Session] | None = None


def _set_sqlite_pragmas(dbapi_conn, connection_record):  # noqa: ANN001
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.execute("PRAGMA synchronous=NORMAL")
    cursor.close()


def init_sqlite(url: str) -> Engine:
    global _engine, _session_factory
    _engine = create_engine(url, echo=False, pool_pre_ping=True)
    event.listen(_engine, "connect", _set_sqlite_pragmas)
    Base.metadata.create_all(_engine)
    _session_factory = sessionmaker(bind=_engine)
    return _engine


def get_engine() -> Engine:
    if _engine is None:
        raise RuntimeError("SQLite not initialized — call init_sqlite() first")
    return _engine


def get_session_factory() -> sessionmaker[Session]:
    if _session_factory is None:
        raise RuntimeError("SQLite not initialized — call init_sqlite() first")
    return _session_factory


@contextmanager
def session_scope() -> Generator[Session, None, None]:
    session = get_session_factory()()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
