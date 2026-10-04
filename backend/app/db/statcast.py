"""Idempotent pitch storage and per-day ingestion state."""

from datetime import date, datetime, timezone
from typing import Mapping, Sequence

from sqlalchemy import create_engine, delete, select
from sqlalchemy.dialects.postgresql import insert as postgresql_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session

from app.db.models import IngestionRun, StatcastPitchRecord
from app.ingestion.statcast import PitchObservation


class StatcastRepository:
    def __init__(self, database_url: str) -> None:
        self.engine = create_engine(database_url)
        if self.engine.dialect.name not in {"sqlite", "postgresql"}:
            raise ValueError("Statcast storage supports SQLite and PostgreSQL")

    def completed_days(self, start_date: date, end_date: date) -> set[date]:
        return {day for day, status in self.latest_statuses(start_date, end_date).items() if status == "complete"}

    def latest_statuses(self, start_date: date, end_date: date) -> dict[date, str]:
        with Session(self.engine) as session:
            runs = session.execute(select(IngestionRun.start_date, IngestionRun.status).where(
                IngestionRun.source == "statcast",
                IngestionRun.start_date >= start_date,
                IngestionRun.start_date <= end_date,
                IngestionRun.start_date == IngestionRun.end_date,
            ).order_by(IngestionRun.id.desc())).all()
        latest = {}
        for day, status in runs:
            latest.setdefault(day, status)
        return latest

    def start_run(self, day: date) -> int:
        with Session(self.engine) as session:
            run = IngestionRun(
                source="statcast", start_date=day, end_date=day, status="running",
                inserted_count=0, skipped_count=0, failed_count=0,
            )
            session.add(run)
            session.commit()
            return run.id

    def finish_run(
        self, run_id: int, *, status: str, inserted: int, skipped: int, failed: int,
    ) -> None:
        with Session(self.engine) as session:
            run = session.get(IngestionRun, run_id)
            if run is None:
                raise ValueError(f"unknown ingestion run: {run_id}")
            run.status = status
            run.inserted_count = inserted
            run.skipped_count = skipped
            run.failed_count = failed
            run.finished_at = datetime.now(timezone.utc)
            session.commit()

    def insert_pitches(
        self, rows: Sequence[tuple[PitchObservation, Mapping[str, str | None]]],
    ) -> tuple[int, int]:
        if not rows:
            return 0, 0
        with self.engine.begin() as connection:
            inserted = self._insert(connection, rows)
        return inserted, len(rows) - inserted

    def replace_day(
        self, day: date, rows: Sequence[tuple[PitchObservation, Mapping[str, str | None]]],
    ) -> int:
        with self.engine.begin() as connection:
            connection.execute(delete(StatcastPitchRecord).where(StatcastPitchRecord.game_date == day))
            return self._insert(connection, rows)

    def _insert(self, connection, rows: Sequence[tuple[PitchObservation, Mapping[str, str | None]]]) -> int:
        values = [
            {**pitch.model_dump(), "pitcher_hand": pitch.pitcher_hand.value,
             "batter_side": pitch.batter_side.value, "source_fields": dict(source)}
            for pitch, source in rows
        ]
        insert = sqlite_insert if self.engine.dialect.name == "sqlite" else postgresql_insert
        inserted = 0
        for index in range(0, len(values), 25):
            statement = insert(StatcastPitchRecord).values(values[index:index + 25]).on_conflict_do_nothing(
                index_elements=[
                    StatcastPitchRecord.game_id,
                    StatcastPitchRecord.at_bat_number,
                    StatcastPitchRecord.pitch_number,
                ],
            )
            inserted += connection.execute(statement).rowcount
        return inserted
