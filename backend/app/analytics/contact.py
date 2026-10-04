"""Conditional results of balls put in play by a hitter."""

from collections import Counter
from enum import Enum
from typing import Iterable, Literal

from pydantic import Field, model_validator

from app.analytics.response import PitchResponse, classify_response
from app.ingestion.statcast import PitchObservation
from app.models.domain.base import DomainModel
from app.models.domain.player import Handedness, Hitter
from app.models.domain.profile import PitchType


class ContactResult(str, Enum):
    HOME_RUN = "home_run"
    NON_HOME_RUN_HIT = "non_home_run_hit"
    OUT = "out"
    OTHER = "other"


_HITS = frozenset({"single", "double", "triple"})
_OUTS = frozenset({"field_out", "force_out", "grounded_into_double_play", "fielders_choice_out",
                   "double_play", "sac_fly", "sac_bunt", "lineout", "flyout", "groundout", "pop_out"})


def classify_contact(observation: PitchObservation) -> ContactResult:
    if observation.event == "home_run":
        return ContactResult.HOME_RUN
    if observation.event in _HITS:
        return ContactResult.NON_HOME_RUN_HIT
    if observation.event in _OUTS:
        return ContactResult.OUT
    return ContactResult.OTHER


class ContactShare(DomainModel):
    result: ContactResult
    probability: float = Field(ge=0, le=1)


class ContactDistribution(DomainModel):
    results: tuple[ContactShare, ...]
    sample_size: int = Field(ge=0)
    fallback: Literal["pitch_type", "handedness", "overall", "unavailable"]

    @model_validator(mode="after")
    def validate_distribution(self) -> "ContactDistribution":
        if self.results and abs(sum(item.probability for item in self.results) - 1) > 1e-9:
            raise ValueError("contact probabilities must sum to one")
        if not self.results and self.fallback != "unavailable":
            raise ValueError("empty contact distribution must be unavailable")
        return self


class HitterContactModel:
    """Descriptive P(result | ball in play), shrunk by pitcher hand and pitch type."""

    def __init__(self, prior_strength: float = 10.0) -> None:
        if prior_strength < 0:
            raise ValueError("prior_strength must be nonnegative")
        self.prior_strength = prior_strength

    def estimate(
        self, observations: Iterable[PitchObservation], hitter: Hitter,
        pitcher_hand: Handedness, pitch_type: PitchType,
    ) -> ContactDistribution:
        overall = [row for row in observations if row.hitter_id == hitter.player_id
                   and row.event is not None and classify_response(row) == PitchResponse.IN_PLAY]
        if not overall:
            return ContactDistribution(results=(), sample_size=0, fallback="unavailable")
        handed = [row for row in overall if row.pitcher_hand == pitcher_hand]
        broad = handed or overall
        typed = [row for row in handed if row.pitch_type == pitch_type]
        broad_counts = Counter(classify_contact(row) for row in broad)
        typed_counts = Counter(classify_contact(row) for row in typed)
        if typed:
            probabilities = {
                result: (typed_counts[result] + self.prior_strength * count / len(broad)) /
                        (len(typed) + self.prior_strength)
                for result, count in broad_counts.items()
            }
        else:
            probabilities = {result: count / len(broad) for result, count in broad_counts.items()}
        return ContactDistribution(
            results=tuple(ContactShare(result=result, probability=probability)
                          for result, probability in sorted(probabilities.items(), key=lambda item: item[0].value)),
            sample_size=len(typed) if typed else len(broad),
            fallback="pitch_type" if typed else "handedness" if handed else "overall",
        )
