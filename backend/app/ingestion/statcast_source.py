"""Date-range Statcast sources, independent of storage."""

import csv
from datetime import date, datetime
from numbers import Real
from pathlib import Path
from typing import Mapping, Protocol


StatcastRow = Mapping[str, str | None]


class StatcastSource(Protocol):
    def fetch(self, start_date: date, end_date: date) -> tuple[StatcastRow, ...]: ...


class CsvStatcastSource:
    def __init__(self, path: Path) -> None:
        self.path = path

    def fetch(self, start_date: date, end_date: date) -> tuple[StatcastRow, ...]:
        with self.path.open(newline="", encoding="utf-8") as stream:
            return tuple(
                row for row in csv.DictReader(stream)
                if not row.get("game_date") or start_date.isoformat() <= row["game_date"] <= end_date.isoformat()
            )


class PybaseballStatcastSource:
    def fetch(self, start_date: date, end_date: date) -> tuple[StatcastRow, ...]:
        try:
            from pybaseball import statcast
        except ImportError as exc:
            raise RuntimeError("Install the ingestion extra: uv sync --extra ingestion") from exc

        frame = statcast(
            start_dt=start_date.isoformat(), end_dt=end_date.isoformat(),
            verbose=False, parallel=False,
        )
        if frame.empty:
            return ()
        records = frame.astype(object).where(frame.notna(), None).to_dict(orient="records")
        return tuple({key: _as_text(value, key) for key, value in record.items()} for record in records)


def _as_text(value: object, column: str) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date().isoformat() if column == "game_date" else value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Real) and not isinstance(value, bool) and float(value).is_integer():
        return str(int(value))
    return str(value)
