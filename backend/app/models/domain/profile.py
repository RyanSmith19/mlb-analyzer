from enum import Enum
from typing import Annotated

from pydantic import Field, StringConstraints, model_validator

from app.models.domain.base import DomainModel
from app.models.domain.player import BatterSide, Handedness, Hitter, Pitcher


PitchType = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, pattern=r"^[A-Z0-9]{1,4}$"),
]


class MetricUnit(str, Enum):
    RATE = "rate"
    MPH = "mph"
    INCHES = "inches"
    VALUE = "value"


class MetricEstimate(DomainModel):
    name: str = Field(min_length=1)
    unit: MetricUnit
    raw_value: float | None = None
    adjusted_value: float | None = None
    sample_size: int = Field(ge=0)

    @model_validator(mode="after")
    def validate_values(self) -> "MetricEstimate":
        if self.raw_value is not None and self.sample_size == 0:
            raise ValueError("raw_value requires a nonzero sample_size")
        if self.unit == MetricUnit.RATE:
            for value in (self.raw_value, self.adjusted_value):
                if value is not None and not 0 <= value <= 1:
                    raise ValueError("rate values must be between 0 and 1")
        return self


class PitcherPitchProfile(DomainModel):
    pitch_type: PitchType
    batter_side: BatterSide | None = None
    usage: float = Field(ge=0, le=1)
    pitch_count: int = Field(ge=0)
    metrics: tuple[MetricEstimate, ...] = ()

    @model_validator(mode="after")
    def validate_split(self) -> "PitcherPitchProfile":
        if self.batter_side == BatterSide.SWITCH:
            raise ValueError("split batter_side must be L or R")
        if self.pitch_count == 0 and self.usage > 0:
            raise ValueError("usage requires a nonzero pitch_count")
        if any(metric.sample_size > self.pitch_count for metric in self.metrics):
            raise ValueError("metric sample_size cannot exceed pitch_count")
        _unique_metrics(self.metrics)
        return self


class HitterPitchProfile(DomainModel):
    pitch_type: PitchType
    pitcher_hand: Handedness
    pitches_seen: int = Field(ge=0)
    plate_appearances: int | None = Field(default=None, ge=0)
    metrics: tuple[MetricEstimate, ...] = ()

    @model_validator(mode="after")
    def validate_metrics(self) -> "HitterPitchProfile":
        if self.plate_appearances is not None and self.plate_appearances > self.pitches_seen:
            raise ValueError("plate_appearances cannot exceed pitches_seen")
        if any(metric.sample_size > self.pitches_seen for metric in self.metrics):
            raise ValueError("metric sample_size cannot exceed pitches_seen")
        _unique_metrics(self.metrics)
        return self


class PitcherProfile(DomainModel):
    """One overall or batter-side cohort; total_pitches is the usage denominator."""

    pitcher: Pitcher
    batter_side: BatterSide | None = None
    total_pitches: int = Field(ge=0)
    pitches: tuple[PitcherPitchProfile, ...] = ()

    @model_validator(mode="after")
    def validate_pitches(self) -> "PitcherProfile":
        if self.batter_side == BatterSide.SWITCH:
            raise ValueError("profile batter_side must be L or R")
        keys = {(item.pitch_type, item.batter_side) for item in self.pitches}
        if len(keys) != len(self.pitches):
            raise ValueError("pitch type and batter side must be unique")
        if any(item.batter_side != self.batter_side for item in self.pitches):
            raise ValueError("pitch rows must match profile batter_side")
        if sum(item.pitch_count for item in self.pitches) > self.total_pitches:
            raise ValueError("pitch counts cannot exceed total_pitches")
        expected_usage = sum(item.pitch_count for item in self.pitches) / self.total_pitches if self.total_pitches else 0
        if self.total_pitches:
            if any(abs(item.usage - item.pitch_count / self.total_pitches) > 0.005 for item in self.pitches):
                raise ValueError("pitch usage must match pitch_count / total_pitches")
        elif any(item.usage > 0 for item in self.pitches):
            raise ValueError("pitch usage requires a nonzero total_pitches")
        if abs(sum(item.usage for item in self.pitches) - expected_usage) > 0.005:
            raise ValueError("total pitch usage must match pitch counts")
        return self


class HitterProfile(DomainModel):
    """Pitch rows partition the observed pitches by type and pitcher hand."""

    hitter: Hitter
    total_pitches_seen: int = Field(ge=0)
    pitches: tuple[HitterPitchProfile, ...] = ()

    @model_validator(mode="after")
    def validate_pitches(self) -> "HitterProfile":
        keys = {(item.pitch_type, item.pitcher_hand) for item in self.pitches}
        if len(keys) != len(self.pitches):
            raise ValueError("pitch type and pitcher hand must be unique")
        if sum(item.pitches_seen for item in self.pitches) > self.total_pitches_seen:
            raise ValueError("pitch counts cannot exceed total_pitches_seen")
        return self


def _unique_metrics(metrics: tuple[MetricEstimate, ...]) -> None:
    if len({metric.name for metric in metrics}) != len(metrics):
        raise ValueError("metric names must be unique within a pitch profile")
