from datetime import date
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import get_mlb_stats_client
from app.clients.mlb_stats import MLBStatsError
from app.main import app


SCHEDULE_FIXTURE = Path(__file__).parent / "fixtures" / "mlb_schedule.json"


class StubStatsClient:
    def __init__(self, payload: bytes = b"", error: MLBStatsError | None = None) -> None:
        self.payload = payload
        self.error = error
        self.requested_dates: list[date] = []

    def get_schedule_raw(self, game_date: date) -> bytes:
        self.requested_dates.append(game_date)
        if self.error is not None:
            raise self.error
        return self.payload


@pytest.fixture
def schedule_json() -> bytes:
    return SCHEDULE_FIXTURE.read_bytes()


@pytest.fixture
def route_client():
    stats_client = StubStatsClient()
    app.dependency_overrides[get_mlb_stats_client] = lambda: stats_client
    try:
        with TestClient(app) as client:
            yield client, stats_client
    finally:
        app.dependency_overrides.pop(get_mlb_stats_client, None)


def test_games_returns_status_teams_scores_and_probable_pitchers(route_client, schedule_json: bytes) -> None:
    client, stats_client = route_client
    stats_client.payload = schedule_json

    response = client.get("/games?date=2026-07-01")

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/json"
    assert response.json()["date"] == "2026-07-01"
    assert response.json()["games"][1] == {
        "game_id": 1002,
        "game_date": "2026-07-01T20:10:00Z",
        "status": "Final",
        "start_time_tbd": False,
        "away": {
            "team_id": 10,
            "name": "Away Club",
            "score": 4,
            "probable_pitcher_name": "Away Starter",
        },
        "home": {
            "team_id": 11,
            "name": "Home Club",
            "score": 2,
            "probable_pitcher_name": "Home Starter",
        },
    }
    assert stats_client.requested_dates == [date(2026, 7, 1)]


@pytest.mark.parametrize("payload", [b'{"dates": []}', b'{"dates": [{"date": "2026-07-01", "games": []}]}'])
def test_games_returns_empty_list_for_empty_schedule(route_client, payload: bytes) -> None:
    client, stats_client = route_client
    stats_client.payload = payload

    response = client.get("/games?date=2026-07-01")

    assert response.status_code == 200
    assert response.json() == {"date": "2026-07-01", "games": []}


def test_games_filters_multiple_dates_and_sorts_by_time_then_id(route_client, schedule_json: bytes) -> None:
    client, stats_client = route_client
    stats_client.payload = schedule_json

    response = client.get("/games?date=2026-07-01")

    assert response.status_code == 200
    games = response.json()["games"]
    assert [game["game_id"] for game in games] == [1001, 1002, 1003]
    assert games[0]["status"] == "Preview"
    assert games[0]["start_time_tbd"] is True
    assert games[1]["start_time_tbd"] is False
    assert games[0]["away"]["score"] is None
    assert games[0]["away"]["probable_pitcher_name"] is None
    assert client.get("/games?date=2026-07-02").json()["games"][0]["game_id"] == 2001
    assert stats_client.requested_dates == [date(2026, 7, 1), date(2026, 7, 2)]


@pytest.mark.parametrize("payload", [b"not json", b'{}', b'{"dates": [{"date": "2026-07-01", "games": [{"gamePk": 1}]}]}'])
def test_games_returns_502_for_malformed_upstream_schedule(route_client, payload: bytes) -> None:
    client, stats_client = route_client
    stats_client.payload = payload

    response = client.get("/games?date=2026-07-01")

    assert response.status_code == 502
    assert response.json() == {"detail": "MLB Stats API returned an unexpected schedule format"}


def test_games_returns_502_for_upstream_error(route_client) -> None:
    client, stats_client = route_client
    stats_client.error = MLBStatsError("MLB Stats API is unavailable")

    response = client.get("/games?date=2026-07-01")

    assert response.status_code == 502
    assert response.json() == {"detail": "MLB Stats API is unavailable"}
    assert stats_client.requested_dates == [date(2026, 7, 1)]


def test_games_rejects_invalid_date_without_calling_upstream(route_client) -> None:
    client, stats_client = route_client

    response = client.get("/games?date=not-a-date")

    assert response.status_code == 422
    assert stats_client.requested_dates == []
