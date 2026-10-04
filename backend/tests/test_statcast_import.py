from datetime import date, datetime
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db.models import IngestionRun, StatcastPitchRecord
from app.db.snapshots import upgrade_database
from app.db.statcast import StatcastRepository
from app.ingestion.import_statcast import main
from app.ingestion.statcast_source import CsvStatcastSource, PybaseballStatcastSource
from app.services.statcast_ingestion import StatcastImportError, StatcastIngestionService


FIXTURE = Path(__file__).resolve().parents[1] / "app" / "data" / "statcast_pitches.csv"
START = date(2026, 7, 1)
END = date(2026, 7, 2)


def repository(tmp_path) -> StatcastRepository:
    database_url = f"sqlite:///{tmp_path / 'statcast.sqlite3'}"
    upgrade_database(database_url)
    return StatcastRepository(database_url)


def test_csv_import_skips_completed_days_and_refresh_is_idempotent(tmp_path) -> None:
    store = repository(tmp_path)
    service = StatcastIngestionService(CsvStatcastSource(FIXTURE), store)

    assert service.import_range(START, END).inserted == 20
    assert service.import_range(START, END).skipped_days == 2
    refresh = service.import_range(START, END, refresh=True)
    assert refresh.imported_days == 2
    assert refresh.inserted == 20
    assert refresh.skipped == 0

    with Session(store.engine) as session:
        assert session.scalar(select(func.count()).select_from(StatcastPitchRecord)) == 20
        assert session.scalar(select(func.count()).select_from(IngestionRun)) == 4
        pitch = session.scalar(select(StatcastPitchRecord).limit(1))
        assert pitch.source_fields["game_pk"] == str(pitch.game_id)


def test_failed_day_is_recorded_and_retried(tmp_path) -> None:
    store = repository(tmp_path)

    class FailingSource:
        def fetch(self, start_date: date, end_date: date):
            raise OSError("network unavailable")

    with pytest.raises(StatcastImportError, match="network unavailable"):
        StatcastIngestionService(FailingSource(), store).import_range(START, START)
    assert store.completed_days(START, START) == set()

    result = StatcastIngestionService(CsvStatcastSource(FIXTURE), store).import_range(START, START)
    assert result.inserted == 10
    with Session(store.engine) as session:
        runs = session.scalars(select(IngestionRun).order_by(IngestionRun.id)).all()
        assert [(run.status, run.failed_count) for run in runs] == [("failed", 1), ("complete", 0)]


def test_failed_refresh_supersedes_older_success(tmp_path) -> None:
    store = repository(tmp_path)
    fixture_source = CsvStatcastSource(FIXTURE)
    assert StatcastIngestionService(fixture_source, store).import_range(START, START).inserted == 10

    class FailingSource:
        def fetch(self, start_date: date, end_date: date):
            raise OSError("offline")

    with pytest.raises(StatcastImportError):
        StatcastIngestionService(FailingSource(), store).import_range(START, START, refresh=True)
    assert store.completed_days(START, START) == set()
    retry = StatcastIngestionService(fixture_source, store).import_range(START, START)
    assert (retry.imported_days, retry.inserted, retry.skipped) == (1, 10, 0)


def test_failed_refresh_keeps_old_pitches_until_corrected_retry(tmp_path) -> None:
    store = repository(tmp_path)
    assert StatcastIngestionService(CsvStatcastSource(FIXTURE), store).import_range(START, START).inserted == 10
    original = dict(CsvStatcastSource(FIXTURE).fetch(START, START)[0])
    revised = {**original, "pitch_type": "CU", "description": "ball"}
    added = {**original, "pitch_number": "99"}

    class PartialSource:
        def fetch(self, start_date: date, end_date: date):
            return revised, added, {"pitch_type": "FF"}

    with pytest.raises(StatcastImportError):
        StatcastIngestionService(PartialSource(), store).import_range(START, START, refresh=True)
    with Session(store.engine) as session:
        pitches = session.scalars(select(StatcastPitchRecord)).all()
        assert len(pitches) == 10
        assert all(pitch.pitch_number != 99 for pitch in pitches)
        prior = next(pitch for pitch in pitches if pitch.game_id == int(original["game_pk"])
                     and pitch.at_bat_number == int(original["at_bat_number"])
                     and pitch.pitch_number == int(original["pitch_number"]))
        assert prior.pitch_type == original["pitch_type"]

    class CorrectedSource:
        def fetch(self, start_date: date, end_date: date):
            return revised, added

    retry = StatcastIngestionService(CorrectedSource(), store).import_range(START, START)
    assert (retry.inserted, retry.skipped) == (2, 0)
    with Session(store.engine) as session:
        pitches = session.scalars(select(StatcastPitchRecord)).all()
        assert len(pitches) == 2
        assert {pitch.pitch_type for pitch in pitches} == {"CU", original["pitch_type"]}


def test_refresh_replaces_revised_and_removed_pitches(tmp_path) -> None:
    store = repository(tmp_path)
    assert StatcastIngestionService(CsvStatcastSource(FIXTURE), store).import_range(START, START).inserted == 10
    revised = dict(CsvStatcastSource(FIXTURE).fetch(START, START)[0])
    revised["pitch_type"] = "CU"
    revised["description"] = "ball"

    class RevisedSource:
        def fetch(self, start_date: date, end_date: date):
            return (revised,)

    assert StatcastIngestionService(RevisedSource(), store).import_range(START, START, refresh=True).inserted == 1
    with Session(store.engine) as session:
        pitches = session.scalars(select(StatcastPitchRecord)).all()
        assert len(pitches) == 1
        assert pitches[0].pitch_type == "CU"
        assert pitches[0].description == "ball"


def test_empty_days_remain_retryable(tmp_path) -> None:
    store = repository(tmp_path)

    class EmptySource:
        def fetch(self, start_date: date, end_date: date):
            return ()

    result = StatcastIngestionService(EmptySource(), store).import_range(START, START)
    assert (result.empty_days, result.inserted) == (1, 0)
    assert store.completed_days(START, START) == set()
    assert StatcastIngestionService(CsvStatcastSource(FIXTURE), store).import_range(START, START).inserted == 10


def test_missing_pitch_type_is_skipped_without_poisoning_day(tmp_path) -> None:
    store = repository(tmp_path)
    valid = dict(CsvStatcastSource(FIXTURE).fetch(START, START)[0])
    unknown = {**valid, "pitch_number": "99", "pitch_type": ""}

    class Source:
        def fetch(self, start_date: date, end_date: date):
            return valid, unknown

    result = StatcastIngestionService(Source(), store).import_range(START, START)
    assert (result.inserted, result.skipped, result.failed) == (1, 1, 0)
    assert store.completed_days(START, START) == {START}


def test_invalid_rows_leave_date_retryable(tmp_path) -> None:
    store = repository(tmp_path)
    valid = CsvStatcastSource(FIXTURE).fetch(START, START)[0]

    class MixedSource:
        def fetch(self, start_date: date, end_date: date):
            return valid, {"game_date": start_date.isoformat(), "pitch_type": "FF"}

    with pytest.raises(StatcastImportError, match="1 invalid Statcast rows"):
        StatcastIngestionService(MixedSource(), store).import_range(START, START)
    assert store.completed_days(START, START) == set()
    with Session(store.engine) as session:
        run = session.scalar(select(IngestionRun))
        assert (run.status, run.inserted_count, run.failed_count) == ("failed", 0, 1)

    result = StatcastIngestionService(CsvStatcastSource(FIXTURE), store).import_range(START, START)
    assert (result.inserted, result.skipped) == (10, 0)


def test_import_discards_unusable_xwoba_but_preserves_source_value(tmp_path) -> None:
    store = repository(tmp_path)
    row = dict(CsvStatcastSource(FIXTURE).fetch(START, START)[0])
    row["launch_speed"] = ""
    row["estimated_woba_using_speedangle"] = "0.69822"

    class Source:
        def fetch(self, start_date: date, end_date: date):
            return (row,)

    assert StatcastIngestionService(Source(), store).import_range(START, START).inserted == 1
    with Session(store.engine) as session:
        pitch = session.scalar(select(StatcastPitchRecord))
        assert pitch.estimated_woba is None
        assert pitch.source_fields["estimated_woba_using_speedangle"] == "0.69822"


def test_cli_imports_fixture_into_configured_local_database(tmp_path, monkeypatch, capsys) -> None:
    monkeypatch.setenv("MLB_DATABASE_URL", f"sqlite:///{tmp_path / 'cli.sqlite3'}")
    get_settings.cache_clear()
    try:
        assert main(["--start", START.isoformat(), "--end", END.isoformat(), "--csv", str(FIXTURE)]) == 0
        assert '"inserted": 20' in capsys.readouterr().out
    finally:
        get_settings.cache_clear()


def test_pybaseball_adapter_requests_one_day_and_normalizes_rows(monkeypatch) -> None:
    calls = []

    class FakeFrame:
        empty = False

        def astype(self, dtype):
            return self

        def notna(self):
            return self

        def where(self, *_args):
            return self

        def to_dict(self, orient):
            assert orient == "records"
            return [{"game_date": datetime(2026, 7, 1), "game_pk": 123.0, "pitch_type": "FF", "timestamp": datetime(2026, 7, 1, 13, 15)}]

    def fake_statcast(**kwargs):
        calls.append(kwargs)
        return FakeFrame()

    monkeypatch.setitem(sys.modules, "pybaseball", SimpleNamespace(statcast=fake_statcast))
    assert PybaseballStatcastSource().fetch(START, START) == (
        {"game_date": "2026-07-01", "game_pk": "123", "pitch_type": "FF", "timestamp": "2026-07-01T13:15:00"},
    )
    assert calls == [{"start_dt": "2026-07-01", "end_dt": "2026-07-01", "verbose": False, "parallel": False}]
