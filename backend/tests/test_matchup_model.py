from pathlib import Path

import pytest
from pydantic import ValidationError

from app.analytics.profiles import build_hitter_profile, build_pitcher_profile
from app.analytics.regression import RegressionPrior, regress_metric, sample_confidence
from app.ingestion.statcast import load_statcast_csv, parse_statcast_row
from app.matchup.model import MatchupModel, WeightedMatchupModel, score_band
from app.models.domain import Hitter, MatchupResult, MetricUnit, Pitcher


FIXTURE = Path(__file__).parents[1] / "app" / "data" / "statcast_pitches.csv"
PITCHER_R = Pitcher(player_id=900101, full_name="Pitcher A", throws="R")
PITCHER_L = Pitcher(player_id=900102, full_name="Pitcher B", throws="L")
HITTER_R = Hitter(player_id=900201, full_name="Hitter A", bats="R")
HITTER_L = Hitter(player_id=900202, full_name="Hitter B", bats="L")


def metric(profile, name):
    return next(item for item in profile.metrics if item.name == name)


def test_parser_normalizes_fixture_and_optional_values() -> None:
    observations = load_statcast_csv(FIXTURE)
    assert len(observations) == 20
    first = observations[0]
    assert (first.game_id, first.pitcher_id, first.hitter_id) == (9900001, 900101, 900201)
    assert first.velocity_mph == 95
    assert first.estimated_woba is None
    assert first.event is None
    assert observations[4].estimated_woba == 0.700


def test_parser_rejects_missing_or_invalid_required_fields() -> None:
    row = {
        "game_date": "2026-07-01", "game_pk": "1", "at_bat_number": "1",
        "pitch_number": "1", "pitcher": "2", "batter": "3",
        "p_throws": "R", "stand": "L", "pitch_type": "FF",
        "description": "called_strike",
    }
    assert parse_statcast_row(row).exit_velocity_mph is None
    assert parse_statcast_row(row | {"events": "", "launch_speed": ""}).event is None
    with pytest.raises(ValueError, match="missing required Statcast fields: pitcher"):
        parse_statcast_row(row | {"pitcher": ""})
    with pytest.raises(ValidationError):
        parse_statcast_row(row | {"p_throws": "X"})
    with pytest.raises(ValidationError):
        parse_statcast_row(row | {"release_speed": "nan"})
    with pytest.raises(ValidationError, match="requires exit_velocity"):
        parse_statcast_row(row | {"estimated_woba_using_speedangle": "0.4"})


def test_pitcher_profile_usage_and_hand_splits() -> None:
    rows = load_statcast_csv(FIXTURE)
    profile = build_pitcher_profile(PITCHER_R, rows)
    assert profile.total_pitches == 10
    assert {pitch.pitch_type: pitch.pitch_count for pitch in profile.pitches} == {"FF": 5, "SL": 5}
    assert sum(pitch.usage for pitch in profile.pitches) == 1
    fastball = next(pitch for pitch in profile.pitches if pitch.pitch_type == "FF")
    assert metric(fastball, "velocity").raw_value == 95
    assert metric(fastball, "horizontal_movement").raw_value == -6
    assert metric(fastball, "whiff_rate").sample_size == 3
    assert metric(fastball, "whiff_rate").raw_value == pytest.approx(1 / 3)
    assert metric(fastball, "xwoba").sample_size == 1
    assert metric(fastball, "xwoba").raw_value == 0.7

    split = build_pitcher_profile(PITCHER_R, rows, batter_side="L")
    assert split.total_pitches == 5
    assert {pitch.pitch_type: pitch.pitch_count for pitch in split.pitches} == {"FF": 2, "SL": 3}
    assert {pitch.pitch_type: pitch.usage for pitch in split.pitches} == {"FF": 0.4, "SL": 0.6}
    assert build_pitcher_profile(PITCHER_L, rows, batter_side="R").total_pitches == 5


def test_hitter_profile_groups_by_pitch_and_hand_with_sparse_metrics() -> None:
    profile = build_hitter_profile(HITTER_R, load_statcast_csv(FIXTURE))
    assert profile.total_pitches_seen == 10
    by_key = {(pitch.pitch_type, pitch.pitcher_hand.value): pitch for pitch in profile.pitches}
    assert set(by_key) == {("FF", "R"), ("SL", "R"), ("FF", "L"), ("CH", "L")}
    assert by_key["FF", "R"].pitches_seen == 3
    assert by_key["FF", "R"].plate_appearances == 2
    assert metric(by_key["FF", "R"], "xwoba").raw_value == 0.7
    assert metric(by_key["FF", "L"], "xwoba").raw_value is None
    assert metric(by_key["FF", "L"], "xwoba").sample_size == 0
    assert metric(by_key["CH", "L"], "strikeout_rate").raw_value == 0.5
    assert metric(by_key["CH", "L"], "exit_velocity").raw_value == 106
    assert metric(by_key["FF", "R"], "strikeout_rate").raw_value == 0
    assert metric(by_key["FF", "R"], "strikeout_rate").sample_size == 1
    assert metric(by_key["FF", "R"], "woba").raw_value is None


def test_woba_uses_denominator_and_barrel_uses_upstream_classification() -> None:
    base = {
        "game_date": "2026-07-01", "game_pk": "1", "at_bat_number": "1",
        "pitch_number": "1", "pitcher": "2", "batter": "900201",
        "p_throws": "R", "stand": "R", "pitch_type": "FF",
        "description": "hit_into_play", "events": "single",
        "launch_speed": "100", "launch_angle": "25",
        "estimated_woba_using_speedangle": "0.7",
        "woba_value": "0.9", "woba_denom": "1", "launch_speed_angle": "6",
    }
    rows = (
        parse_statcast_row(base),
        parse_statcast_row(base | {
            "at_bat_number": "2", "events": "field_out", "woba_value": "0.3",
            "woba_denom": "2", "launch_speed_angle": "4",
        }),
    )
    pitch = build_hitter_profile(HITTER_R, rows).pitches[0]
    assert metric(pitch, "woba").raw_value == pytest.approx(0.4)
    assert metric(pitch, "woba").sample_size == 2
    assert metric(pitch, "barrel_rate").raw_value == 0.5
    assert metric(pitch, "barrel_rate").sample_size == 2


def test_regression_zero_small_and_large_samples() -> None:
    prior = RegressionPrior(average=0.32, k=10)
    assert regress_metric("xwoba", MetricUnit.VALUE, None, 0, prior).adjusted_value == 0.32
    assert regress_metric("xwoba", MetricUnit.VALUE, 1.0, 1, prior).adjusted_value == pytest.approx(0.38181818)
    assert regress_metric("xwoba", MetricUnit.VALUE, 1.0, 1000, prior).adjusted_value == pytest.approx(0.9932673)
    assert sample_confidence(0, prior.k) == 0
    assert sample_confidence(1000, prior.k) > 0.99
    with pytest.raises(ValueError):
        regress_metric("xwoba", MetricUnit.VALUE, None, 1, prior)


def test_weighted_model_is_deterministic_and_reports_contributions() -> None:
    rows = load_statcast_csv(FIXTURE)
    pitcher = build_pitcher_profile(PITCHER_R, rows, batter_side="L")
    hitter = build_hitter_profile(HITTER_L, rows)
    model: MatchupModel = WeightedMatchupModel()
    result = model.calculate(pitcher, hitter)
    assert isinstance(result, MatchupResult)
    assert result.pitcher_id == PITCHER_R.player_id
    assert result.hitter_id == HITTER_L.player_id
    assert 0 <= result.score <= 100
    assert result.score == pytest.approx(50 + sum(item.impact for item in result.explanations))
    assert result.score == pytest.approx(50 + 0.6 * ((2 * 0.485 + 25 * 0.32) / 27 - 0.32) * 100)
    assert {item.pitch_type for item in result.explanations} == {"FF", "SL"}
    assert result.biggest_advantage is not None
    assert result.confidence.value < 0.1
    assert MatchupResult.model_validate_json(result.model_dump_json()) == result
    assert model.calculate(pitcher, hitter) == result


def test_model_can_be_swapped_and_rejects_wrong_handed_split() -> None:
    class FakeModel(MatchupModel):
        def calculate(self, pitcher_profile, hitter_profile):
            return MatchupResult(
                pitcher_id=pitcher_profile.pitcher.player_id,
                hitter_id=hitter_profile.hitter.player_id,
                score=50, confidence={"value": 0, "explanation": "Fake"},
            )

    rows = load_statcast_csv(FIXTURE)
    pitcher = build_pitcher_profile(PITCHER_R, rows, batter_side="L")
    hitter = build_hitter_profile(HITTER_L, rows)
    assert FakeModel().calculate(pitcher, hitter).score == 50
    with pytest.raises(ValueError, match="pitcher split"):
        WeightedMatchupModel().calculate(pitcher, build_hitter_profile(HITTER_R, rows))


def test_empty_and_unseen_pitch_types_are_neutral_or_low_confidence() -> None:
    rows = load_statcast_csv(FIXTURE)
    model = WeightedMatchupModel()
    empty_pitcher = build_pitcher_profile(PITCHER_R, ())
    empty_hitter = build_hitter_profile(HITTER_R, ())
    empty = model.calculate(empty_pitcher, empty_hitter)
    assert empty.score == 50
    assert empty.confidence.value == 0
    assert empty.explanations == ()

    pitcher = build_pitcher_profile(PITCHER_L, rows, batter_side="R")
    unseen = build_hitter_profile(HITTER_R, (row for row in rows if row.pitch_type != "CH"))
    result = model.calculate(pitcher, unseen)
    changeup = next(item for item in result.explanations if item.pitch_type == "CH")
    assert changeup.hitter_metric.sample_size == 0
    assert changeup.hitter_metric.adjusted_value == 0.32
    assert result.confidence.value <= 0.1
    assert changeup.impact == 0


def test_custom_prior_and_switch_hitter_split() -> None:
    rows = load_statcast_csv(FIXTURE)
    prior = RegressionPrior(average=0.4, k=10)
    pitcher = build_pitcher_profile(PITCHER_R, rows, batter_side="L")
    hitter = build_hitter_profile(HITTER_L, rows)
    model = WeightedMatchupModel(prior)
    assert model.calculate(build_pitcher_profile(PITCHER_R, ()), build_hitter_profile(HITTER_L, ())).score == 50
    assert model.calculate(pitcher, hitter).score != WeightedMatchupModel().calculate(pitcher, hitter).score

    switch_hitter = Hitter(player_id=HITTER_L.player_id, full_name="Switch Hitter", bats="S")
    switch_profile = build_hitter_profile(switch_hitter, rows)
    assert model.calculate(pitcher, switch_profile).hitter_id == switch_hitter.player_id


@pytest.mark.parametrize("score,band", [
    (0, "Poor matchup"), (24, "Poor matchup"),
    (25, "Slight disadvantage"), (44, "Slight disadvantage"),
    (45, "Neutral"), (54, "Neutral"),
    (55, "Slight advantage"), (74, "Slight advantage"),
    (75, "Strong advantage"), (89, "Strong advantage"),
    (90, "Elite matchup"), (100, "Elite matchup"),
])
def test_score_bands(score, band) -> None:
    assert score_band(score) == band
