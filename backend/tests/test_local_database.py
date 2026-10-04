from datetime import date

from fastapi.testclient import TestClient
from sqlalchemy import inspect, select
from sqlalchemy.orm import Session

from app.api.dependencies import get_mlb_stats_client
from app.db.models import MlbPayload
from app.db.snapshots import MlbSnapshotRepository, get_snapshot_repository, upgrade_database
from app.main import app
from app.services.games import GameService


class StubSource:
    schedule_payload = b'{"dates": [], "source": "live"}'
    game_payload = b'{"gamePk":849830,"gameData":{}}'

    def get_schedule_raw(self, game_date: date) -> bytes:
        return self.schedule_payload

    def get_game_raw(self, game_pk: int) -> bytes:
        return self.game_payload


def test_migration_creates_local_schema_and_repeated_fetches_replace_snapshots(tmp_path) -> None:
    database_url = f"sqlite:///{tmp_path / 'nested' / 'mlb.sqlite3'}"
    upgrade_database(database_url)
    upgrade_database(database_url)
    repository = MlbSnapshotRepository(database_url)
    source = StubSource()
    service = GameService(source, repository)

    assert {"mlb_payloads", "statcast_pitches", "players", "teams", "games", "appearances", "profile_snapshots", "ingestion_runs"} <= set(inspect(repository.engine).get_table_names())
    assert service.raw_schedule(date(2026, 10, 3)) == source.schedule_payload
    assert service.raw_game(849830) == source.game_payload

    source.game_payload = b'{ "gamePk": 849830, "updated": true }'
    assert service.raw_game(849830) == source.game_payload

    reopened = MlbSnapshotRepository(database_url)
    assert reopened.get("schedule", "2026-10-03") == source.schedule_payload
    assert reopened.get("game", "849830") == source.game_payload
    with Session(repository.engine) as session:
        assert len(session.scalars(select(MlbPayload)).all()) == 2


def test_upstream_failure_does_not_replace_stored_response(tmp_path) -> None:
    database_url = f"sqlite:///{tmp_path / 'mlb.sqlite3'}"
    upgrade_database(database_url)
    repository = MlbSnapshotRepository(database_url)

    class FailingSource(StubSource):
        def get_game_raw(self, game_pk: int) -> bytes:
            raise RuntimeError("upstream unavailable")

    repository.put("game", "849830", b"previous")
    service = GameService(FailingSource(), repository)
    try:
        service.raw_game(849830)
    except RuntimeError:
        pass
    else:
        raise AssertionError("upstream failure should propagate")
    assert repository.get("game", "849830") == b"previous"


def test_raw_http_route_persists_unmodified_payload(tmp_path) -> None:
    database_url = f"sqlite:///{tmp_path / 'mlb.sqlite3'}"
    upgrade_database(database_url)
    repository = MlbSnapshotRepository(database_url)
    source = StubSource()
    app.dependency_overrides[get_mlb_stats_client] = lambda: source
    app.dependency_overrides[get_snapshot_repository] = lambda: repository
    try:
        response = TestClient(app).get("/raw/mlb-stats/games/849830")
        assert response.status_code == 200
        assert response.content == source.game_payload
        assert repository.get("game", "849830") == source.game_payload
    finally:
        app.dependency_overrides.pop(get_mlb_stats_client, None)
        app.dependency_overrides.pop(get_snapshot_repository, None)
