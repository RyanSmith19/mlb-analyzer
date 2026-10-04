import pytest
from pydantic import ValidationError

from app.models.domain import (
    Confidence,
    Game,
    HitterPitchProfile,
    HitterProfile,
    MatchupResult,
    MetricEstimate,
    PitcherPitchProfile,
    PitcherProfile,
    PitchMatchupExplanation,
)


def metric(**changes: object) -> MetricEstimate:
    values = {"name": "whiff_rate", "unit": "rate", "raw_value": 0.25,
              "adjusted_value": 0.2, "sample_size": 10}
    return MetricEstimate.model_validate(values | changes)


def explanation(pitch_type: str, impact: float) -> PitchMatchupExplanation:
    return PitchMatchupExplanation(
        pitch_type=pitch_type,
        pitcher_usage=0.5,
        hitter_metric=metric(),
        pitcher_metric=metric(),
        impact=impact,
        summary="Measured pitch matchup",
    )


@pytest.mark.parametrize("value", [0.0, 1.0])
def test_fraction_and_score_boundaries_are_inclusive(value: float) -> None:
    assert metric(raw_value=value, adjusted_value=value).raw_value == value
    assert Confidence(value=value, sample_size=0, explanation="Available data").value == value
    assert PitcherPitchProfile(pitch_type="FF", usage=value, pitch_count=1).usage == value

    score = value * 100
    assert MatchupResult(
        pitcher_id=1, hitter_id=2, score=score,
        confidence=Confidence(value=value, explanation="Available data"),
    ).score == score


@pytest.mark.parametrize("bad_value", [-0.01, 1.01, float("nan")])
def test_invalid_fraction_and_nonfinite_values_are_rejected(bad_value: float) -> None:
    with pytest.raises(ValidationError):
        metric(raw_value=bad_value)
    with pytest.raises(ValidationError):
        Confidence(value=bad_value, explanation="Available data")
    with pytest.raises(ValidationError):
        PitcherPitchProfile(pitch_type="FF", usage=bad_value, pitch_count=1)


def test_metric_sample_size_and_pitch_profile_consistency() -> None:
    with pytest.raises(ValidationError, match="raw_value requires"):
        metric(sample_size=0)
    with pytest.raises(ValidationError, match="nonzero pitch_count"):
        PitcherPitchProfile(pitch_type="FF", usage=0.1, pitch_count=0)
    with pytest.raises(ValidationError, match="cannot exceed pitch_count"):
        PitcherPitchProfile(pitch_type="FF", usage=0.5, pitch_count=9, metrics=(metric(),))
    with pytest.raises(ValidationError, match="cannot exceed pitches_seen"):
        HitterPitchProfile(pitch_type="FF", pitcher_hand="R", pitches_seen=9, metrics=(metric(),))


def test_game_rejects_duplicate_teams_and_invalid_ids() -> None:
    values = {
        "game_id": 10, "game_date": "2026-04-01", "status": "scheduled",
        "away_team": {"team_id": 1, "name": "Away", "abbreviation": "AWY"},
        "home_team": {"team_id": 2, "name": "Home", "abbreviation": "HOM"},
    }
    assert Game.model_validate(values).game_id == 10
    with pytest.raises(ValidationError, match="home and away teams must differ"):
        Game.model_validate(values | {"home_team": values["away_team"]})
    with pytest.raises(ValidationError):
        Game.model_validate(values | {"away_probable_pitcher_id": 0})


def test_pitcher_profile_rejects_duplicate_split_and_bad_pitch_type() -> None:
    pitch = PitcherPitchProfile(pitch_type="FF", batter_side="L", usage=0.5, pitch_count=10)
    values = {"pitcher": {"player_id": 1, "full_name": "Starter", "throws": "R"},
              "total_pitches": 10, "pitches": (pitch, pitch)}
    with pytest.raises(ValidationError, match="pitch type and batter side must be unique"):
        PitcherProfile.model_validate(values)
    with pytest.raises(ValidationError):
        PitcherPitchProfile(pitch_type="bad pitch", usage=0.5, pitch_count=10)


def test_pitcher_profile_validates_disjoint_rows_and_group_usage() -> None:
    pitcher = {"player_id": 1, "full_name": "Starter", "throws": "R"}
    fastball = PitcherPitchProfile(pitch_type="FF", batter_side="L", usage=0.7, pitch_count=7)
    slider = PitcherPitchProfile(pitch_type="SL", batter_side="L", usage=0.7, pitch_count=7)
    with pytest.raises(ValidationError, match="pitch counts cannot exceed total_pitches"):
        PitcherProfile(pitcher=pitcher, batter_side="L", total_pitches=10, pitches=(fastball, slider))

    fastball = fastball.model_copy(update={"pitch_count": 3})
    slider = slider.model_copy(update={"pitch_count": 3})
    with pytest.raises(ValidationError, match="pitch usage must match"):
        PitcherProfile(pitcher=pitcher, batter_side="L", total_pitches=10, pitches=(fastball, slider))

    left_split = PitcherPitchProfile(pitch_type="FF", batter_side="L", usage=1.0, pitch_count=3)
    right_split = PitcherPitchProfile(pitch_type="FF", batter_side="R", usage=1.0, pitch_count=4)
    assert PitcherProfile(pitcher=pitcher, batter_side="L", total_pitches=3, pitches=(left_split,))
    assert PitcherProfile(pitcher=pitcher, batter_side="R", total_pitches=4, pitches=(right_split,))
    overall = PitcherPitchProfile(pitch_type="SL", usage=0.2, pitch_count=1)
    with pytest.raises(ValidationError, match="pitch rows must match profile batter_side"):
        PitcherProfile(pitcher=pitcher, batter_side="L", total_pitches=10, pitches=(fastball, overall))

    wrong_mix = (
        PitcherPitchProfile(pitch_type="FF", usage=0.1, pitch_count=7),
        PitcherPitchProfile(pitch_type="SL", usage=0.9, pitch_count=3),
    )
    with pytest.raises(ValidationError, match="pitch usage must match"):
        PitcherProfile(pitcher=pitcher, total_pitches=10, pitches=wrong_mix)


def test_hitter_profile_rejects_combined_pitch_counts_above_total() -> None:
    hitter = {"player_id": 2, "full_name": "Hitter", "bats": "L"}
    fastball = HitterPitchProfile(pitch_type="FF", pitcher_hand="R", pitches_seen=7)
    slider = HitterPitchProfile(pitch_type="SL", pitcher_hand="R", pitches_seen=7)
    with pytest.raises(ValidationError, match="pitch counts cannot exceed total_pitches_seen"):
        HitterProfile(hitter=hitter, total_pitches_seen=10, pitches=(fastball, slider))


def test_matchup_extremes_and_nested_json_round_trip() -> None:
    advantage = explanation("FF", 0.7)
    disadvantage = explanation("SL", -0.4)
    result = MatchupResult(
        pitcher_id=1, hitter_id=2, score=62.5,
        confidence=Confidence(value=0.8, sample_size=20, explanation="Twenty pitches"),
        explanations=(advantage, disadvantage),
        biggest_advantage=advantage,
        biggest_disadvantage=disadvantage,
    )

    assert MatchupResult.model_validate_json(result.model_dump_json()) == result
    with pytest.raises(ValidationError, match="biggest_advantage"):
        MatchupResult.model_validate(result.model_dump() | {"biggest_advantage": disadvantage})
    with pytest.raises(ValidationError, match="unique pitch types"):
        MatchupResult.model_validate(result.model_dump() | {
            "explanations": (advantage, advantage), "biggest_disadvantage": None,
        })


def test_game_json_round_trip_preserves_date_and_enum() -> None:
    game = Game.model_validate({
        "game_id": 10, "game_date": "2026-04-01", "status": "scheduled",
        "away_team": {"team_id": 1, "name": "Away", "abbreviation": "AWY"},
        "home_team": {"team_id": 2, "name": "Home", "abbreviation": "HOM"},
        "away_probable_pitcher_id": None,
    })

    assert Game.model_validate_json(game.model_dump_json()) == game
