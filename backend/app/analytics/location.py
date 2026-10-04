"""Pitch location distribution in Statcast zones, with sparse split backoff."""

from collections import Counter
from typing import Iterable, Literal

from pydantic import Field, model_validator

from app.ingestion.statcast import PitchObservation
from app.models.domain.base import DomainModel
from app.models.domain.player import BatterSide, Pitcher
from app.models.domain.profile import PitchType


class ZoneShare(DomainModel):
    zone: int = Field(ge=1)
    probability: float = Field(ge=0, le=1)


class LocationDistribution(DomainModel):
    zones: tuple[ZoneShare, ...]
    sample_size: int = Field(ge=0)
    fallback: Literal["handedness", "pitch_type", "unavailable"]

    @model_validator(mode="after")
    def validate_distribution(self) -> "LocationDistribution":
        if self.zones and abs(sum(item.probability for item in self.zones) - 1) > 1e-9:
            raise ValueError("zone probabilities must sum to one")
        if not self.zones and self.fallback != "unavailable":
            raise ValueError("empty zone distribution must be unavailable")
        return self


class ZoneLocationModel:
    """Estimate zone use by pitch and batter side without fitting on tiny coordinate samples."""

    def __init__(self, prior_strength: float = 10.0) -> None:
        if prior_strength < 0:
            raise ValueError("prior_strength must be nonnegative")
        self.prior_strength = prior_strength

    def estimate(
        self, observations: Iterable[PitchObservation], pitcher: Pitcher,
        batter_side: BatterSide, pitch_type: PitchType,
    ) -> LocationDistribution:
        if batter_side == BatterSide.SWITCH:
            raise ValueError("use the switch hitter's actual batting side")
        typed = [row for row in observations if row.pitcher_id == pitcher.player_id
                 and row.pitcher_hand == pitcher.throws and row.pitch_type == pitch_type
                 and row.zone is not None]
        if not typed:
            return LocationDistribution(zones=(), sample_size=0, fallback="unavailable")
        handed = [row for row in typed if row.batter_side == batter_side]
        base_counts = Counter(row.zone for row in typed)
        if handed:
            handed_counts = Counter(row.zone for row in handed)
            probabilities = {
                zone: (handed_counts[zone] + self.prior_strength * count / len(typed)) /
                      (len(handed) + self.prior_strength)
                for zone, count in base_counts.items()
            }
        else:
            probabilities = {zone: count / len(typed) for zone, count in base_counts.items()}
        return LocationDistribution(
            zones=tuple(ZoneShare(zone=zone, probability=probability)
                        for zone, probability in sorted(probabilities.items())),
            sample_size=len(handed) if handed else len(typed),
            fallback="handedness" if handed else "pitch_type",
        )
