"""Incremental daily Statcast ingestion orchestration."""

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Mapping, Protocol, Sequence

from app.ingestion.statcast import PitchObservation, parse_statcast_row
from app.ingestion.statcast_source import StatcastSource


class StatcastImportError(RuntimeError):
    pass


@dataclass(frozen=True)
class ImportSummary:
    imported_days: int = 0
    skipped_days: int = 0
    empty_days: int = 0
    inserted: int = 0
    skipped: int = 0
    failed: int = 0


class StatcastStore(Protocol):
    def completed_days(self, start_date: date, end_date: date) -> set[date]: ...
    def start_run(self, day: date) -> int: ...
    def finish_run(self, run_id: int, *, status: str, inserted: int, skipped: int, failed: int) -> None: ...
    def insert_pitches(
        self, rows: Sequence[tuple[PitchObservation, Mapping[str, str | None]]],
    ) -> tuple[int, int]: ...
    def replace_day(
        self, day: date, rows: Sequence[tuple[PitchObservation, Mapping[str, str | None]]],
    ) -> int: ...


class StatcastIngestionService:
    def __init__(self, source: StatcastSource, repository: StatcastStore) -> None:
        self.source = source
        self.repository = repository

    def import_range(self, start_date: date, end_date: date, *, refresh: bool = False) -> ImportSummary:
        if end_date < start_date:
            raise ValueError("end date must be on or after start date")
        completed = set() if refresh else self.repository.completed_days(start_date, end_date)
        imported_days = skipped_days = empty_days = inserted_total = skipped_total = failed_total = 0
        day = start_date
        while day <= end_date:
            if day in completed:
                skipped_days += 1
                day += timedelta(days=1)
                continue
            run_id = self.repository.start_run(day)
            inserted = skipped = failed = 0
            try:
                raw_rows = self.source.fetch(day, day)
                valid_rows = []
                first_error: str | None = None
                ignored = 0
                for row in raw_rows:
                    if not row.get("pitch_type"):
                        ignored += 1
                        continue
                    try:
                        normalized = dict(row)
                        if not normalized.get("launch_speed"):
                            normalized["estimated_woba_using_speedangle"] = None
                        pitch = parse_statcast_row(normalized)
                        if pitch.game_date != day:
                            raise ValueError("Statcast row is outside requested date")
                        valid_rows.append((pitch, row))
                    except ValueError as exc:
                        failed += 1
                        if first_error is None:
                            errors = getattr(exc, "errors", None)
                            first_error = errors()[0]["msg"] if callable(errors) else str(exc)
                if failed:
                    status = "failed"
                    inserted, skipped = self.repository.insert_pitches(valid_rows)
                elif not valid_rows:
                    status = "empty"
                    empty_days += 1
                    skipped = ignored
                elif refresh:
                    status = "complete"
                    inserted = self.repository.replace_day(day, valid_rows)
                    skipped = ignored
                else:
                    status = "complete"
                    inserted, skipped = self.repository.insert_pitches(valid_rows)
                    skipped += ignored
                self.repository.finish_run(
                    run_id, status=status, inserted=inserted, skipped=skipped, failed=failed,
                )
                imported_days += 1
                inserted_total += inserted
                skipped_total += skipped
                failed_total += failed
                if failed:
                    raise StatcastImportError(f"{day}: {failed} invalid Statcast rows; first error: {first_error}")
            except Exception as exc:
                if not isinstance(exc, StatcastImportError):
                    self.repository.finish_run(
                        run_id, status="failed", inserted=inserted, skipped=skipped, failed=max(failed, 1),
                    )
                raise StatcastImportError(f"Statcast import failed for {day}: {exc}") from exc
            day += timedelta(days=1)
        return ImportSummary(imported_days, skipped_days, empty_days, inserted_total, skipped_total, failed_total)
