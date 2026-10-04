from fastapi.testclient import TestClient
import pytest

from app.main import app
from app.models.matchup_read import GameMatchupsRead, HitterProfileRead, MatchupRead, PitcherProfileRead
from app.models.domain import Hitter, MatchupResult
from app.services.fixture_matchups import FixtureMatchupService, HITTERS


client = TestClient(app)


def test_fixture_matchup_contract_and_json_round_trip() -> None:
    response = client.get("/matchups/900101/900202")

    assert response.status_code == 200
    body = response.json()
    assert body["pitcher"] == {"player_id": 900101, "full_name": "Pitcher A", "handedness": "R"}
    assert body["hitter"] == {"player_id": 900202, "full_name": "Hitter B", "handedness": "L"}
    assert body["score"] == pytest.approx(50.733333333333334)
    assert body["score_band"] == "Neutral"
    assert body["score_type"] == "contact_quality_index"
    assert body["data_source"] == "synthetic_fixture"
    assert body["calibrated"] is False
    assert body["confidence"]["sample_size"] == 2
    assert 0 < body["confidence"]["value"] < 0.1
    assert "SL" in body["top_explanation"]
    assert [item["pitch_type"] for item in body["pitches"]] == ["FF", "SL"]
    slider = body["pitches"][1]
    assert slider["pitcher_usage"] == 0.6
    assert slider["pitcher_pitch_count"] == 3
    assert slider["hitter_pitches_seen"] == 3
    assert slider["hitter_xwoba"]["raw_value"] == 0.485
    assert slider["hitter_xwoba"]["sample_size"] == 2
    assert slider["hitter_xwoba"]["adjusted_value"] < slider["hitter_xwoba"]["raw_value"]
    assert body["biggest_advantage_pitch_type"] == "SL"
    assert body["biggest_disadvantage_pitch_type"] is None
    assert MatchupRead.model_validate_json(response.content) == MatchupRead.model_validate(body)


@pytest.mark.parametrize("url", [
    "/matchups/999999/900201", "/matchups/900101/999999",
])
def test_fixture_matchup_unknown_player_returns_404(url: str) -> None:
    response = client.get(url)
    assert response.status_code == 404
    assert response.json() == {"detail": "Fixture pitcher or hitter not found"}


def test_fixture_game_matchups_are_ranked_and_explained() -> None:
    response = client.get("/games/9900001/matchups")

    assert response.status_code == 200
    body = response.json()
    assert body["game"]["game_id"] == 9900001
    assert body["game"]["game_date"] == "2026-07-01"
    assert body["game"]["status"] == "final"
    assert body["game"]["away_team"] == {
        "team_id": 900002, "name": "Fixture Visitors", "abbreviation": "VIS",
    }
    assert body["game"]["home_team"] == {
        "team_id": 900001, "name": "Fixture Hosts", "abbreviation": "HST",
    }
    assert body["data_source"] == "synthetic_fixture"
    assert body["pitcher"]["player_id"] == 900101
    assert len(body["matchups"]) == 2
    assert [item["score"] for item in body["matchups"]] == sorted(
        (item["score"] for item in body["matchups"]), reverse=True,
    )
    assert {item["hitter"]["player_id"] for item in body["matchups"]} == {900201, 900202}
    assert all(item["confidence"]["sample_size"] is not None for item in body["matchups"])
    assert all(item["top_explanation"] for item in body["matchups"])
    assert GameMatchupsRead.model_validate_json(response.content)
    assert client.get("/games/9999999/matchups").status_code == 404


def test_game_rankings_exclude_hitter_on_starters_team(monkeypatch) -> None:
    service = FixtureMatchupService()
    own_hitter = Hitter(player_id=900203, full_name="Home Hitter", team_id=900001, bats="R")
    monkeypatch.setitem(HITTERS, own_hitter.player_id, own_hitter)
    same_team_pitch = next(row for row in service.rows if row.game_id == 9900001).model_copy(
        update={"hitter_id": own_hitter.player_id},
    )
    game = FixtureMatchupService(rows=service.rows + (same_team_pitch,)).game_matchups(9900001)
    assert game is not None
    assert game.pitcher.team_id == game.game.home_team.team_id
    assert {item.hitter_profile.hitter.team_id for item in game.matchups} == {game.game.away_team.team_id}
    assert own_hitter.player_id not in {item.result.hitter_id for item in game.matchups}


def test_fixture_profile_endpoints_include_splits_metrics_and_samples() -> None:
    pitcher_response = client.get("/pitchers/900101/profile")
    assert pitcher_response.status_code == 200
    pitcher = pitcher_response.json()
    assert pitcher["total_pitches"] == 10
    assert sum(item["usage"] for item in pitcher["pitches"]) == 1
    assert {item["pitch_type"]: item["pitch_count"] for item in pitcher["pitches"]} == {"FF": 5, "SL": 5}
    assert PitcherProfileRead.model_validate_json(pitcher_response.content)

    split = client.get("/pitchers/900101/profile?batter_side=L")
    assert split.status_code == 200
    assert split.json()["batter_side"] == "L"
    assert split.json()["total_pitches"] == 5
    assert {item["pitch_type"]: item["pitch_count"] for item in split.json()["pitches"]} == {"FF": 2, "SL": 3}

    hitter_response = client.get("/hitters/900201/profile")
    assert hitter_response.status_code == 200
    hitter = hitter_response.json()
    assert hitter["total_pitches_seen"] == 10
    assert {(item["pitch_type"], item["pitcher_hand"]) for item in hitter["pitches"]} == {
        ("FF", "R"), ("SL", "R"), ("FF", "L"), ("CH", "L"),
    }
    changeup = next(item for item in hitter["pitches"] if item["pitch_type"] == "CH")
    assert changeup["plate_appearances"] == 2
    assert next(item for item in changeup["metrics"] if item["name"] == "xwoba")["sample_size"] == 1
    assert HitterProfileRead.model_validate_json(hitter_response.content)


def test_fixture_profile_endpoints_reject_unknown_players_and_bad_side() -> None:
    assert client.get("/pitchers/999999/profile").status_code == 404
    assert client.get("/hitters/999999/profile").status_code == 404
    assert client.get("/pitchers/900101/profile?batter_side=S").status_code == 422


def test_top_explanation_uses_largest_absolute_contribution() -> None:
    matchup = FixtureMatchupService().matchup(900102, 900202)
    assert matchup is not None
    negative, positive = matchup.result.explanations
    negative = negative.model_copy(update={"impact": -2.0})
    positive = positive.model_copy(update={"impact": 0.2})
    result = MatchupResult(
        pitcher_id=900102, hitter_id=900202, score=48.2,
        confidence=matchup.result.confidence,
        explanations=(negative, positive),
        biggest_advantage=positive,
        biggest_disadvantage=negative,
    )
    read = MatchupRead.from_domain(matchup.pitcher_profile, matchup.hitter_profile, result)
    assert read.top_explanation == negative.summary
