"""Count-aware pitcher pitch mix, backed off to handedness and overall usage."""

from collections import Counter
from typing import Iterable, Literal

from pydantic import Field, model_validator

from app.ingestion.statcast import PitchObservation
from app.models.domain.base import DomainModel
from app.models.domain.player import BatterSide, Pitcher
from app.models.domain.profile import PitchType


class PitchSelectionShare(DomainModel):
    pitch_type: PitchType
    probability: float = Field(ge=0, le=1)


class PitchSelectionDistribution(DomainModel):
    pitches: tuple[PitchSelectionShare, ...]
    sample_size: int = Field(ge=0)
    fallback: Literal["count", "handedness", "overall", "unavailable"]

    @model_validator(mode="after")
    def validate_distribution(self) -> "PitchSelectionDistribution":
        if self.pitches and abs(sum(item.probability for item in self.pitches) - 1) > 1e-9:
            raise ValueError("pitch selection probabilities must sum to one")
        if not self.pitches and self.fallback != "unavailable":
            raise ValueError("empty pitch selection must be unavailable")
        return self


class PitchSelectionModel:
    """Estimate P(pitch type | pitcher, batter side, pre-pitch count)."""

    def __init__(self, prior_strength: float = 10.0) -> None:
        if prior_strength < 0:
            raise ValueError("prior_strength must be nonnegative")
        self.prior_strength = prior_strength

    def estimate(
        self, observations: Iterable[PitchObservation], pitcher: Pitcher,
        batter_side: BatterSide, balls: int | None = None, strikes: int | None = None,
    ) -> PitchSelectionDistribution:
        if batter_side == BatterSide.SWITCH:
            raise ValueError("use the switch hitter's actual batting side")
        if (balls is None) != (strikes is None):
            raise ValueError("balls and strikes must be supplied together")
        if balls is not None and not (0 <= balls <= 3 and 0 <= strikes <= 2):
            raise ValueError("invalid pre-pitch count")
        overall = [row for row in observations if row.pitcher_id == pitcher.player_id
                   and row.pitcher_hand == pitcher.throws]
        if not overall:
            return PitchSelectionDistribution(pitches=(), sample_size=0, fallback="unavailable")
        handed = [row for row in overall if row.batter_side == batter_side]
        overall_counts = Counter(row.pitch_type for row in overall)
        handed_counts = Counter(row.pitch_type for row in handed)
        handed_probabilities = (
            {pitch_type: (handed_counts[pitch_type] + self.prior_strength * count / len(overall)) /
                         (len(handed) + self.prior_strength)
             for pitch_type, count in overall_counts.items()}
            if handed else {pitch_type: count / len(overall) for pitch_type, count in overall_counts.items()}
        )
        baseline_source = "handedness" if handed else "overall"
        contextual = [row for row in handed if row.balls == balls and row.strikes == strikes] if balls is not None else []
        current = contextual or handed or overall
        fallback = "count" if contextual else baseline_source
        current_counts = Counter(row.pitch_type for row in current)
        if contextual:
            probabilities = {
                pitch_type: (current_counts[pitch_type] + self.prior_strength * base_probability) /
                            (len(contextual) + self.prior_strength)
                for pitch_type, base_probability in handed_probabilities.items()
            }
        else:
            probabilities = handed_probabilities
        return PitchSelectionDistribution(
            pitches=tuple(PitchSelectionShare(pitch_type=pitch_type, probability=probability)
                          for pitch_type, probability in sorted(probabilities.items())),
            sample_size=len(current), fallback=fallback,
        )
