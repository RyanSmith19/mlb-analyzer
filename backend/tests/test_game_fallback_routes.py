from datetime import date
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import get_game_service
from app.clients.mlb_stats import MLBStatsError
from app.main import app
from app.services.games import GameService


SCHEDULE = (Path(__file__).parent / "fixtures" / "mlb_schedule.json").read_bytes()
GAME = (
    b'{"gamePk":123,"gameData":{'
    b'"datetime":{"dateTime":"2026-07-01T20:10:00Z"},'
    b'"status":{"detailedState":"Preview"},'
    b'"teams":{"away":{"id":135,"name":"San Diego Padres"},'
    b'"home":{"id":111,"name":"Boston Red Sox"}}}}'
)


class Source:
    def __init__(self) -> None:
        self.offline = False

    def get_schedule_raw(self, _game_date: date) -> bytes:
        if self.offline:
            raise MLBStatsError("MLB Stats API is unavailable")
        return SCHEDULE

    def get_game_raw(self, _game_pk: int) -> bytes:
        if self.offline:
            raise MLBStatsError("MLB Stats API is unavailable")
        return GAME


class Snapshots:
    def __init__(self) -> None:
        self.payloads: dict[tuple[str, str], bytes] = {}

    def put(self, kind: str, key: str, payload: bytes) -> None:
        self.payloads[(kind, key)] = payload

    def get(self, kind: str, key: str) -> bytes | None:
        return self.payloads.get((kind, key))


@pytest.fixture
def route_client():
    source = Source()
    snapshots = Snapshots()
    app.dependency_overrides[get_game_service] = lambda: GameService(source, snapshots)
    try:
        with TestClient(app) as client:
            yield client, source, snapshots
    finally:
        app.dependency_overrides.pop(get_game_service, None)


@pytest.mark.parametrize(
    "path,kind,key,payload",
    [
        ("/games?date=2026-07-01", "schedule", "2026-07-01", SCHEDULE),
        ("/games/123", "game", "123", GAME),
        ("/raw/mlb-stats/schedule?date=2026-07-01", "schedule", "2026-07-01", SCHEDULE),
        ("/raw/mlb-stats/games/123", "game", "123", GAME),
    ],
)
def test_routes_report_live_and_stored_sources(route_client, path, kind, key, payload) -> None:
    client, source, snapshots = route_client

    live = client.get(path)
    assert live.status_code == 200
    assert live.headers["X-Data-Source"] == "live"
    assert snapshots.payloads[(kind, key)] == payload

    source.offline = True
    stored = client.get(path)
    assert stored.status_code == 200
    assert stored.headers["X-Data-Source"] == "stored"
    if path.startswith("/raw/"):
        assert live.content == stored.content == payload
    else:
        assert live.json() == stored.json()


@pytest.mark.parametrize(
    "path",
    [
        "/games?date=2026-07-01",
        "/games/123",
        "/raw/mlb-stats/schedule?date=2026-07-01",
        "/raw/mlb-stats/games/123",
    ],
)
def test_routes_keep_502_when_no_snapshot_exists(route_client, path) -> None:
    client, source, _snapshots = route_client
    source.offline = True

    response = client.get(path)
    assert response.status_code == 502
    assert response.json() == {"detail": "MLB Stats API is unavailable"}
