"""Pure pitch-type aggregations over normalized observations."""

from collections import defaultdict
from statistics import mean, pstdev
from typing import Iterable

from app.analytics.regression import RegressionPrior, regress_metric
from app.ingestion.statcast import PitchObservation
from app.models.domain.player import BatterSide, Hitter, Pitcher
from app.models.domain.profile import (
    HitterPitchProfile, HitterProfile, MetricEstimate, MetricUnit,
    PitcherPitchProfile, PitcherProfile,
)


# Illustrative prior for fixture analysis, not a measured seasonal league average.
DEFAULT_XWOBA_PRIOR = RegressionPrior(average=0.320, k=25)
_SWING_DESCRIPTIONS = frozenset({
    "swinging_strike", "swinging_strike_blocked", "foul", "foul_tip",
    "foul_bunt", "missed_bunt", "hit_into_play", "hit_into_play_no_out",
    "hit_into_play_score",
})
_WHIFF_DESCRIPTIONS = frozenset({"swinging_strike", "swinging_strike_blocked", "missed_bunt"})


def _estimate(name: str, unit: MetricUnit, values: list[float]) -> MetricEstimate:
    return MetricEstimate(
        name=name, unit=unit, raw_value=mean(values) if values else None,
        adjusted_value=mean(values) if values else None, sample_size=len(values),
    )


def _rate(name: str, successes: int, opportunities: int) -> MetricEstimate:
    return MetricEstimate(
        name=name, unit=MetricUnit.RATE,
        raw_value=successes / opportunities if opportunities else None,
        adjusted_value=successes / opportunities if opportunities else None,
        sample_size=opportunities,
    )


def _appearance_key(pitch: PitchObservation) -> tuple[int, int]:
    return pitch.game_id, pitch.at_bat_number


def _pitch_metrics(rows: list[PitchObservation], prior: RegressionPrior) -> tuple[MetricEstimate, ...]:
    speeds = [row.velocity_mph for row in rows if row.velocity_mph is not None]
    horizontal = [row.horizontal_movement_ft * 12 for row in rows if row.horizontal_movement_ft is not None]
    vertical = [row.vertical_movement_ft * 12 for row in rows if row.vertical_movement_ft is not None]
    swings = [row for row in rows if row.description in _SWING_DESCRIPTIONS]
    zones = [row for row in rows if row.zone is not None]
    batted = [row for row in rows if row.exit_velocity_mph is not None]
    xwoba = [row.estimated_woba for row in rows if row.estimated_woba is not None]
    classified = [row for row in rows if row.launch_speed_angle is not None]
    return (
        _estimate("velocity", MetricUnit.MPH, speeds),
        MetricEstimate(name="velocity_stddev", unit=MetricUnit.MPH,
                       raw_value=pstdev(speeds) if speeds else None,
                       adjusted_value=pstdev(speeds) if speeds else None, sample_size=len(speeds)),
        _estimate("horizontal_movement", MetricUnit.INCHES, horizontal),
        _estimate("vertical_movement", MetricUnit.INCHES, vertical),
        _rate("zone_rate", sum(row.zone <= 9 for row in zones), len(zones)),
        _rate("whiff_rate", sum(row.description in _WHIFF_DESCRIPTIONS for row in swings), len(swings)),
        regress_metric("xwoba", MetricUnit.VALUE, mean(xwoba) if xwoba else None, len(xwoba), prior),
        _rate("hard_hit_rate", sum(row.exit_velocity_mph >= 95 for row in batted), len(batted)),
        _rate("barrel_rate", sum(row.launch_speed_angle == 6 for row in classified), len(classified)),
    )


def build_pitcher_profile(
    pitcher: Pitcher, observations: Iterable[PitchObservation],
    batter_side: BatterSide | None = None,
    prior: RegressionPrior = DEFAULT_XWOBA_PRIOR,
) -> PitcherProfile:
    if batter_side == BatterSide.SWITCH:
        raise ValueError("batter_side must be L or R")
    rows = [row for row in observations if row.pitcher_id == pitcher.player_id
            and row.pitcher_hand == pitcher.throws
            and (batter_side is None or row.batter_side == batter_side)]
    groups: dict[str, list[PitchObservation]] = defaultdict(list)
    for row in rows:
        groups[row.pitch_type].append(row)
    pitches = tuple(
        PitcherPitchProfile(
            pitch_type=pitch_type, batter_side=batter_side,
            usage=len(group) / len(rows), pitch_count=len(group),
            metrics=_pitch_metrics(group, prior),
        )
        for pitch_type, group in sorted(groups.items())
    )
    return PitcherProfile(pitcher=pitcher, batter_side=batter_side,
                          total_pitches=len(rows), pitches=pitches)


def build_hitter_profile(
    hitter: Hitter, observations: Iterable[PitchObservation],
    prior: RegressionPrior = DEFAULT_XWOBA_PRIOR,
) -> HitterProfile:
    rows = [row for row in observations if row.hitter_id == hitter.player_id]
    groups: dict[tuple[str, str], list[PitchObservation]] = defaultdict(list)
    for row in rows:
        groups[(row.pitch_type, row.pitcher_hand.value)].append(row)
    pitches = []
    for (pitch_type, hand), group in sorted(groups.items()):
        appearances = {_appearance_key(row) for row in group}
        terminal_rows = [row for row in group if row.event is not None]
        strikeouts = sum(row.event == "strikeout" for row in terminal_rows)
        woba_rows = [row for row in terminal_rows if row.woba_value is not None
                     and row.woba_denominator is not None and row.woba_denominator > 0]
        woba_value = (sum(row.woba_value for row in woba_rows) /
                      sum(row.woba_denominator for row in woba_rows)) if woba_rows else None
        woba = MetricEstimate(
            name="woba", unit=MetricUnit.VALUE,
            raw_value=woba_value, adjusted_value=woba_value,
            sample_size=len(woba_rows),
        )
        batted = [row.exit_velocity_mph for row in group if row.exit_velocity_mph is not None]
        metrics = _pitch_metrics(group, prior) + (
            woba,
            _rate("strikeout_rate", strikeouts, len(terminal_rows)),
            _estimate("exit_velocity", MetricUnit.MPH, batted),
        )
        pitches.append(HitterPitchProfile(
            pitch_type=pitch_type, pitcher_hand=hand, pitches_seen=len(group),
            plate_appearances=len(appearances), metrics=metrics,
        ))
    return HitterProfile(hitter=hitter, total_pitches_seen=len(rows), pitches=tuple(pitches))
