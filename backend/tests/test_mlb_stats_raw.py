from datetime import date
from email.message import Message
import ssl
from urllib.error import URLError

from fastapi.testclient import TestClient

from app.api.dependencies import get_mlb_stats_client
from app.clients.mlb_stats import MLBStatsClient, MLBStatsError
from app.main import app


class FakeResponse:
    def __init__(self, payload: bytes, content_type: str = "application/json") -> None:
        self.payload = payload
        self.headers = Message()
        self.headers["Content-Type"] = content_type

    def __enter__(self) -> "FakeResponse":
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def read(self) -> bytes:
        return self.payload


def test_client_requests_mlb_schedule_and_returns_unmodified_bytes(monkeypatch) -> None:
    calls = []
    payload = b'{"dates": [{"games": []}], "copyright": "MLB"}'

    def fake_urlopen(request, timeout, context):
        calls.append((request, timeout, context))
        return FakeResponse(payload)

    monkeypatch.setattr("app.clients.mlb_stats.urlopen", fake_urlopen)
    client = MLBStatsClient(timeout=4)

    assert client.get_schedule_raw(date(2026, 7, 1)) == payload
    assert len(calls) == 1
    assert calls[0][0].full_url == "https://statsapi.mlb.com/api/v1/schedule?sportId=1&date=2026-07-01&hydrate=probablePitcher"
    assert calls[0][0].get_header("Accept") == "application/json"
    assert calls[0][1] == 4
    assert isinstance(calls[0][2], ssl.SSLContext)


def test_client_rejects_non_json_and_network_failures(monkeypatch) -> None:
    monkeypatch.setattr("app.clients.mlb_stats.urlopen", lambda *_args, **_kwargs: FakeResponse(b"blocked", "text/html"))
    try:
        MLBStatsClient().get_schedule_raw(date(2026, 7, 1))
    except MLBStatsError as exc:
        assert "did not return JSON" in str(exc)
    else:
        raise AssertionError("non-JSON response accepted")

    def fail_urlopen(*_args, **_kwargs):
        raise URLError("offline")

    monkeypatch.setattr("app.clients.mlb_stats.urlopen", fail_urlopen)
    try:
        MLBStatsClient().get_schedule_raw(date(2026, 7, 1))
    except MLBStatsError as exc:
        assert "unavailable" in str(exc)
    else:
        raise AssertionError("network failure accepted")


def test_client_requests_live_game_feed_and_returns_unmodified_bytes(monkeypatch) -> None:
    calls = []
    payload = b'{"gamePk":123,"gameData":{"players":{"ID42":{"id":42}}}}'

    def fake_urlopen(request, timeout, context):
        calls.append(request)
        return FakeResponse(payload)

    monkeypatch.setattr("app.clients.mlb_stats.urlopen", fake_urlopen)
    assert MLBStatsClient().get_game_raw(123) == payload
    assert calls[0].full_url == "https://statsapi.mlb.com/api/v1.1/game/123/feed/live"
    assert calls[0].get_header("Accept") == "application/json"


def test_raw_route_preserves_upstream_json_and_validates_date() -> None:
    payload = b'{"dates":[{"date":"2026-07-01","games":[{"gamePk":1}]}]}'
    observed = []

    class FakeClient:
        def get_schedule_raw(self, game_date: date) -> bytes:
            observed.append(game_date)
            return payload

    app.dependency_overrides[get_mlb_stats_client] = lambda: FakeClient()
    try:
        client = TestClient(app)
        response = client.get("/raw/mlb-stats/schedule?date=2026-07-01")
        assert response.status_code == 200
        assert response.content == payload
        assert response.headers["content-type"] == "application/json"
        assert observed == [date(2026, 7, 1)]
        assert client.get("/raw/mlb-stats/schedule?date=invalid").status_code == 422
    finally:
        app.dependency_overrides.pop(get_mlb_stats_client, None)


def test_raw_route_reports_upstream_failure() -> None:
    class FailingClient:
        def get_schedule_raw(self, _game_date: date) -> bytes:
            raise MLBStatsError("MLB Stats API is unavailable")

    app.dependency_overrides[get_mlb_stats_client] = lambda: FailingClient()
    try:
        response = TestClient(app).get("/raw/mlb-stats/schedule?date=2026-07-01")
        assert response.status_code == 502
        assert response.json() == {"detail": "MLB Stats API is unavailable"}
    finally:
        app.dependency_overrides.pop(get_mlb_stats_client, None)


def test_raw_game_route_preserves_feed_and_validates_id() -> None:
    payload = b'{"gamePk":123,"gameData":{"players":{"ID42":{"id":42}}}}'
    observed = []

    class FakeClient:
        def get_game_raw(self, game_pk: int) -> bytes:
            observed.append(game_pk)
            return payload

    app.dependency_overrides[get_mlb_stats_client] = lambda: FakeClient()
    try:
        client = TestClient(app)
        response = client.get("/raw/mlb-stats/games/123")
        assert response.status_code == 200
        assert response.content == payload
        assert response.headers["content-type"] == "application/json"
        assert observed == [123]
        assert client.get("/raw/mlb-stats/games/0").status_code == 422
        assert client.get("/raw/mlb-stats/games/not-an-id").status_code == 422
    finally:
        app.dependency_overrides.pop(get_mlb_stats_client, None)


def test_raw_game_route_reports_upstream_failure() -> None:
    class FailingClient:
        def get_game_raw(self, _game_pk: int) -> bytes:
            raise MLBStatsError("MLB Stats API is unavailable")

    app.dependency_overrides[get_mlb_stats_client] = lambda: FailingClient()
    try:
        response = TestClient(app).get("/raw/mlb-stats/games/123")
        assert response.status_code == 502
        assert response.json() == {"detail": "MLB Stats API is unavailable"}
    finally:
        app.dependency_overrides.pop(get_mlb_stats_client, None)
