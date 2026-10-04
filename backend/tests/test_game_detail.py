import json

import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import get_mlb_stats_client
from app.clients.mlb_stats import MLBStatsError
from app.main import app
from app.services.game_detail import parse_game_detail


def feed_payload(with_stats: bool = True) -> bytes:
    feed = {
        "gamePk": 849830,
        "gameData": {
            "datetime": {"dateTime": "2026-10-04T00:30:00Z"},
            "status": {"detailedState": "Final"},
            "teams": {
                "away": {"id": 135, "name": "San Diego Padres", "abbreviation": "SD"},
                "home": {"id": 158, "name": "Milwaukee Brewers", "abbreviation": "MIL"},
            },
            "venue": {"name": "American Family Field"},
        },
    }
    if with_stats:
        feed["liveData"] = {
            "linescore": {
                "innings": [
                    {"num": 1, "away": {"runs": 2}, "home": {"runs": 0}},
                    {"num": 2, "away": {"runs": 0}, "home": {"runs": 3}},
                ],
                "teams": {"away": {"runs": 2, "hits": 9, "errors": 1}, "home": {"runs": 3, "hits": 7, "errors": 0}},
            },
            "boxscore": {"teams": {
                "away": {"pitchers": [44, 43], "players": {
                    "ID42": {
                        "person": {"id": 42, "fullName": "First Batter"},
                        "position": {"abbreviation": "CF"},
                        "battingOrder": "100",
                        "stats": {"batting": {"atBats": 4, "runs": 1, "hits": 2, "rbi": 1, "baseOnBalls": 0, "strikeOuts": 1}},
                    },
                    "ID43": {
                        "person": {"id": 43, "fullName": "Relief Pitcher"},
                        "stats": {"pitching": {"inningsPitched": "2.1", "hits": 1, "runs": 0, "earnedRuns": 0, "baseOnBalls": 1, "strikeOuts": 3, "numberOfPitches": 37}},
                    },
                    "ID44": {
                        "person": {"id": 44, "fullName": "Another Pitcher"},
                        "stats": {"pitching": {"inningsPitched": "1.0", "hits": 0}},
                    },
                }},
                "home": {"players": {}},
            }},
            "plays": {"allPlays": [
                {"about": {"inning": 1, "halfInning": "top", "isScoringPlay": True}, "result": {"event": "Single", "description": "First Batter singles.", "awayScore": 1, "homeScore": 0}},
            ]},
        }
    return json.dumps(feed).encode()


def test_parse_game_detail_formats_score_boxscore_and_plays() -> None:
    detail = parse_game_detail(feed_payload(), 849830)

    assert detail.game_id == 849830
    assert detail.status == "Final"
    assert detail.away.score.model_dump() == {"runs": 2, "hits": 9, "errors": 1}
    assert detail.home.score.runs == 3
    assert [inning.away_runs for inning in detail.innings] == [2, 0]
    assert detail.away.batting[0].model_dump() == {
        "player_id": 42, "name": "First Batter", "position": "CF", "at_bats": 4,
        "runs": 1, "hits": 2, "rbi": 1, "walks": 0, "strikeouts": 1,
    }
    assert detail.away.pitching[1].innings_pitched == "2.1"
    assert detail.away.pitching[1].pitches == 37
    assert [player.player_id for player in detail.away.pitching] == [44, 43]
    assert detail.plays[0].description == "First Batter singles."
    assert detail.plays[0].is_scoring_play is True


def test_parse_game_detail_handles_pregame_feed() -> None:
    detail = parse_game_detail(feed_payload(with_stats=False), 849830)
    assert detail.innings == []
    assert detail.away.batting == []
    assert detail.home.pitching == []
    assert detail.plays == []
    assert detail.away.score.runs is None


@pytest.fixture
def route_client():
    class StubClient:
        payload = feed_payload()
        error = None
        requested_ids: list[int] = []

        def get_game_raw(self, game_pk: int) -> bytes:
            self.requested_ids.append(game_pk)
            if self.error is not None:
                raise self.error
            return self.payload

    stub = StubClient()
    app.dependency_overrides[get_mlb_stats_client] = lambda: stub
    try:
        with TestClient(app) as client:
            yield client, stub
    finally:
        app.dependency_overrides.pop(get_mlb_stats_client, None)


def test_formatted_game_route_returns_detail(route_client) -> None:
    client, stub = route_client
    response = client.get("/games/849830")
    assert response.status_code == 200
    assert response.json()["home"]["score"]["runs"] == 3
    assert response.json()["away"]["batting"][0]["name"] == "First Batter"
    assert stub.requested_ids == [849830]
    assert client.get("/games/0").status_code == 422
    assert client.get("/games/not-an-id").status_code == 422


def test_formatted_game_route_rejects_bad_feed(route_client) -> None:
    client, stub = route_client
    stub.payload = b"not json"
    response = client.get("/games/849830")
    assert response.status_code == 502
    assert response.json()["detail"] == "MLB Stats API returned an unexpected game format"

    stub.payload = feed_payload()
    response = client.get("/games/849831")
    assert response.status_code == 502


def test_formatted_game_route_reports_upstream_error(route_client) -> None:
    client, stub = route_client
    stub.error = MLBStatsError("MLB Stats API is unavailable")
    response = client.get("/games/849830")
    assert response.status_code == 502
    assert response.json()["detail"] == "MLB Stats API is unavailable"
