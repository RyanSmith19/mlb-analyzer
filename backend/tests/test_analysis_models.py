from pathlib import Path
from datetime import date

import pytest

from app.analytics.contact import ContactResult, HitterContactModel
from app.analytics.location import ZoneLocationModel
from app.analytics.response import HitterResponseModel, PitchResponse, classify_response
from app.analytics.response import ResponseDistribution
from app.analytics.selection import PitchSelectionModel
from app.ingestion.statcast import load_statcast_csv, parse_statcast_row
from app.matchup.outcomes import PlateAppearanceModel, PlateAppearanceOutcome, PlateAppearanceEstimate
from app.models.domain import Hitter, Pitcher


ROWS = load_statcast_csv(Path(__file__).parents[1] / "app" / "data" / "statcast_pitches.csv")
PITCHER_R = Pitcher(player_id=900101, full_name="Pitcher A", throws="R")
HITTER_R = Hitter(player_id=900201, full_name="Hitter A", bats="R")
HITTER_L = Hitter(player_id=900202, full_name="Hitter B", bats="L")


def test_parser_accepts_optional_count_and_location_and_rejects_invalid_count() -> None:
    base = {
        "game_date": "2026-07-01", "game_pk": "1", "at_bat_number": "1",
        "pitch_number": "1", "pitcher": "2", "batter": "3",
        "p_throws": "R", "stand": "L", "pitch_type": "FF",
        "description": "called_strike", "plate_x": "0.25", "plate_z": "2.4",
        "balls": "2", "strikes": "1",
    }
    observation = parse_statcast_row(base)
    assert (observation.plate_x_ft, observation.plate_z_ft) == (0.25, 2.4)
    assert (observation.balls, observation.strikes) == (2, 1)
    with pytest.raises(ValueError):
        parse_statcast_row(base | {"balls": "4"})


def test_pitch_selection_uses_count_and_shrinks_to_hand_and_overall() -> None:
    model = PitchSelectionModel(prior_strength=10)
    handed = model.estimate(ROWS, PITCHER_R, "L")
    shares = {item.pitch_type: item.probability for item in handed.pitches}
    assert handed.fallback == "handedness"
    assert handed.sample_size == 5
    assert shares["FF"] == pytest.approx((2 + 10 * 0.5) / 15)
    assert shares["SL"] == pytest.approx((3 + 10 * 0.5) / 15)

    with_count = tuple(row.model_copy(update={"balls": 0, "strikes": 0}) if row == ROWS[5] else row
                       for row in ROWS)
    count = model.estimate(with_count, PITCHER_R, "L", balls=0, strikes=0)
    assert count.fallback == "count"
    assert count.sample_size == 1
    assert {item.pitch_type: item.probability for item in count.pitches}["FF"] > shares["FF"]
    assert model.estimate(ROWS, PITCHER_R, "L", balls=0, strikes=0).fallback == "handedness"
    with pytest.raises(ValueError, match="supplied together"):
        model.estimate(ROWS, PITCHER_R, "L", balls=0)


def test_location_distribution_uses_statcast_zones_and_missing_data() -> None:
    model = ZoneLocationModel(prior_strength=10)
    distribution = model.estimate(ROWS, PITCHER_R, "L", "FF")
    zones = {item.zone: item.probability for item in distribution.zones}
    assert distribution.fallback == "handedness"
    assert distribution.sample_size == 2
    assert sum(zones.values()) == pytest.approx(1)
    assert zones[2] == pytest.approx((1 + 10 / 5) / 12)
    assert model.estimate(ROWS, PITCHER_R, "L", "CH").fallback == "unavailable"


def test_hitter_response_shrinks_sparse_pitch_and_zone_splits() -> None:
    model = HitterResponseModel(prior_strength=10)
    typed = model.estimate(ROWS, HITTER_R, "R", "FF")
    zone = model.estimate(ROWS, HITTER_R, "R", "FF", zone=4)
    assert typed.fallback == "pitch_type"
    assert zone.fallback == "zone"
    assert zone.sample_size == 1
    assert 0 < zone.probability_of(PitchResponse.IN_PLAY) < 1
    assert sum(item.probability for item in zone.responses) == pytest.approx(1)
    assert model.estimate(ROWS, HITTER_R, "R", "CH").fallback == "handedness"
    assert model.estimate((), HITTER_R, "R", "FF").fallback == "unavailable"

    foul_tip = ROWS[0].model_copy(update={"description": "foul_tip"})
    assert classify_response(foul_tip) == PitchResponse.STRIKE_OTHER


def test_contact_model_distinguishes_hit_and_out_and_falls_back() -> None:
    model = HitterContactModel()
    distribution = model.estimate(ROWS, HITTER_L, "R", "SL")
    shares = {item.result: item.probability for item in distribution.results}
    assert shares == {ContactResult.NON_HOME_RUN_HIT: 0.5, ContactResult.OUT: 0.5}
    assert distribution.sample_size == 2
    assert model.estimate(ROWS, HITTER_L, "R", "CH").fallback == "handedness"
    assert model.estimate((), HITTER_L, "R", "SL").fallback == "unavailable"


def test_plate_appearance_model_is_normalized_deterministic_and_explicitly_uncalibrated() -> None:
    model = PlateAppearanceModel()
    result = model.estimate(ROWS, PITCHER_R, HITTER_L)
    assert result.status == "available"
    assert result.calibrated is False
    assert result.model_version == "empirical_markov_v1"
    assert result.first_pitch_mix is not None
    assert sum(item.probability for item in result.outcomes) == pytest.approx(1)
    assert result.probability_of(PlateAppearanceOutcome.STRIKEOUT) == pytest.approx(0.121, abs=0.005)
    assert result.probability_of(PlateAppearanceOutcome.NON_HOME_RUN_HIT) == pytest.approx(0.436, abs=0.005)
    assert result.hit_probability() == pytest.approx(
        result.probability_of(PlateAppearanceOutcome.NON_HOME_RUN_HIT)
        + result.probability_of(PlateAppearanceOutcome.HOME_RUN)
    )
    assert result.probability_of(PlateAppearanceOutcome.WALK) > 0
    assert result.confidence.value < 0.1
    assert model.estimate(ROWS, PITCHER_R, HITTER_L) == result
    assert PlateAppearanceEstimate.model_validate_json(result.model_dump_json()) == result
    assert model.estimate(ROWS, PITCHER_R, HITTER_L, before_date=date(2026, 7, 1)).status == "unavailable"
    assert model.estimate(ROWS, PITCHER_R, HITTER_L, before_date=date(2026, 7, 3)) == result


def test_plate_appearance_model_handles_empty_switch_and_unresolved() -> None:
    model = PlateAppearanceModel(max_pitches=3)
    empty = model.estimate((), PITCHER_R, HITTER_R)
    assert empty.status == "unavailable"
    assert empty.hit_probability() is None
    switch = Hitter(player_id=HITTER_L.player_id, full_name="Switch", bats="S")
    with pytest.raises(ValueError, match="actual batting side"):
        model.estimate(ROWS, PITCHER_R, switch)
    assert model.estimate(ROWS, PITCHER_R, switch, batter_side="L").status == "available"

    one_foul = ROWS[0].model_copy(update={"description": "foul", "hitter_id": HITTER_R.player_id})
    unresolved = model.estimate((one_foul,), PITCHER_R, HITTER_R)
    assert unresolved.probability_of(PlateAppearanceOutcome.UNRESOLVED) == pytest.approx(1)


def test_plate_appearance_model_handles_unavailable_injected_response() -> None:
    class UnavailableResponse(HitterResponseModel):
        def estimate(self, *args, **kwargs):
            return ResponseDistribution(responses=(), sample_size=0, fallback="unavailable")

    estimate = PlateAppearanceModel(response=UnavailableResponse()).estimate(ROWS, PITCHER_R, HITTER_L)
    assert estimate.status == "unavailable"
    assert estimate.outcomes == ()
