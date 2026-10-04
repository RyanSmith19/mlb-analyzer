"""SQLite-compatible storage for unmodified MLB API responses."""

from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, select
from sqlalchemy.dialects.postgresql import insert as postgresql_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db.models import MlbPayload


def prepare_database_path(database_url: str) -> None:
    url = make_url(database_url)
    if url.get_backend_name() == "sqlite" and url.database not in (None, ":memory:"):
        Path(url.database).parent.mkdir(parents=True, exist_ok=True)


def upgrade_database(database_url: str) -> None:
    config = Config()
    config.set_main_option("script_location", str(Path(__file__).resolve().parent / "migrations"))
    config.attributes["database_url"] = database_url
    command.upgrade(config, "head")


class MlbSnapshotRepository:
    def __init__(self, database_url: str) -> None:
        self.engine = create_engine(database_url)
        if self.engine.dialect.name not in {"sqlite", "postgresql"}:
            raise ValueError("Snapshot storage supports SQLite and PostgreSQL")

    def put(self, kind: str, resource_key: str, payload: bytes) -> None:
        insert = sqlite_insert if self.engine.dialect.name == "sqlite" else postgresql_insert
        statement = insert(MlbPayload).values(
            kind=kind,
            resource_key=resource_key,
            payload=payload,
            fetched_at=datetime.now(timezone.utc),
        )
        statement = statement.on_conflict_do_update(
            index_elements=[MlbPayload.kind, MlbPayload.resource_key],
            set_={"payload": statement.excluded.payload, "fetched_at": statement.excluded.fetched_at},
        )
        with self.engine.begin() as connection:
            connection.execute(statement)

    def get(self, kind: str, resource_key: str) -> bytes | None:
        with Session(self.engine) as session:
            record = session.scalar(select(MlbPayload).filter_by(kind=kind, resource_key=resource_key))
            return record.payload if record is not None else None


@lru_cache
def get_snapshot_repository() -> MlbSnapshotRepository:
    database_url = get_settings().database_url
    upgrade_database(database_url)
    return MlbSnapshotRepository(database_url)
