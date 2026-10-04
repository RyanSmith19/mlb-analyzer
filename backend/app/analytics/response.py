"""Hitter response tendencies by pitch type, pitcher hand, count, and zone."""

from collections import Counter
from enum import Enum
from typing import Iterable, Literal

from pydantic import Field, model_validator

from app.ingestion.statcast import PitchObservation
from app.models.domain.base import DomainModel
from app.models.domain.player import Handedness, Hitter
from app.models.domain.profile import PitchType


class PitchResponse(str, Enum):
    BALL = "ball"
    CALLED_STRIKE = "called_strike"
    FOUL = "foul"
    WHIFF = "whiff"
    STRIKE_OTHER = "strike_other"
    IN_PLAY = "in_play"
    HIT_BY_PITCH = "hit_by_pitch"
    OTHER = "other"


_DESCRIPTION_TO_RESPONSE = {
    "ball": PitchResponse.BALL,
    "blocked_ball": PitchResponse.BALL,
    "called_strike": PitchResponse.CALLED_STRIKE,
    "foul": PitchResponse.FOUL,
    "foul_tip": PitchResponse.STRIKE_OTHER,
    "foul_bunt": PitchResponse.STRIKE_OTHER,
    "swinging_strike": PitchResponse.WHIFF,
    "swinging_strike_blocked": PitchResponse.WHIFF,
    "missed_bunt": PitchResponse.WHIFF,
    "hit_into_play": PitchResponse.IN_PLAY,
    "hit_into_play_no_out": PitchResponse.IN_PLAY,
    "hit_into_play_score": PitchResponse.IN_PLAY,
    "hit_by_pitch": PitchResponse.HIT_BY_PITCH,
}


def classify_response(observation: PitchObservation) -> PitchResponse:
    return _DESCRIPTION_TO_RESPONSE.get(observation.description, PitchResponse.OTHER)


class ResponseShare(DomainModel):
    response: PitchResponse
    probability: float = Field(ge=0, le=1)


class ResponseDistribution(DomainModel):
    responses: tuple[ResponseShare, ...]
    sample_size: int = Field(ge=0)
    fallback: Literal["count_zone", "zone", "count", "pitch_type", "handedness", "overall", "unavailable"]

    @model_validator(mode="after")
    def validate_distribution(self) -> "ResponseDistribution":
        if self.responses and abs(sum(item.probability for item in self.responses) - 1) > 1e-9:
            raise ValueError("response probabilities must sum to one")
        if not self.responses and self.fallback != "unavailable":
            raise ValueError("empty response distribution must be unavailable")
        return self

    def probability_of(self, response: PitchResponse) -> float:
        return next((item.probability for item in self.responses if item.response == response), 0.0)


class HitterResponseModel:
    """Empirical pitch outcomes with contextual estimates shrunk to broader hitter history."""

    def __init__(self, prior_strength: float = 10.0) -> None:
        if prior_strength < 0:
            raise ValueError("prior_strength must be nonnegative")
        self.prior_strength = prior_strength

    def estimate(
        self, observations: Iterable[PitchObservation], hitter: Hitter,
        pitcher_hand: Handedness, pitch_type: PitchType,
        *, zone: int | None = None, balls: int | None = None, strikes: int | None = None,
    ) -> ResponseDistribution:
        if (balls is None) != (strikes is None):
            raise ValueError("balls and strikes must be supplied together")
        if balls is not None and not (0 <= balls <= 3 and 0 <= strikes <= 2):
            raise ValueError("invalid pre-pitch count")
        if zone is not None and zone < 1:
            raise ValueError("zone must be positive")
        overall = [row for row in observations if row.hitter_id == hitter.player_id]
        if not overall:
            return ResponseDistribution(responses=(), sample_size=0, fallback="unavailable")
        handed = [row for row in overall if row.pitcher_hand == pitcher_hand]
        typed = [row for row in handed if row.pitch_type == pitch_type]
        broad = handed or overall
        source = "pitch_type" if typed else "handedness" if handed else "overall"
        broad_counts = Counter(classify_response(row) for row in broad)
        typed_counts = Counter(classify_response(row) for row in typed)
        typed_probabilities = (
            {response: (typed_counts[response] + self.prior_strength * count / len(broad)) /
                       (len(typed) + self.prior_strength)
             for response, count in broad_counts.items()}
            if typed else {response: count / len(broad) for response, count in broad_counts.items()}
        )
        contexts = []
        if zone is not None and balls is not None:
            contexts.append(("count_zone", [row for row in typed
                                             if row.zone == zone and row.balls == balls and row.strikes == strikes]))
        if zone is not None:
            contexts.append(("zone", [row for row in typed if row.zone == zone]))
        if balls is not None:
            contexts.append(("count", [row for row in typed if row.balls == balls and row.strikes == strikes]))
        context = next(((name, sample) for name, sample in contexts if sample), None)
        contextual = context[1] if context else []
        use_context = bool(context)
        current = contextual if use_context else typed or broad
        current_counts = Counter(classify_response(row) for row in current)
        if use_context:
            probabilities = {
                response: (current_counts[response] + self.prior_strength * base_probability) /
                          (len(current) + self.prior_strength)
                for response, base_probability in typed_probabilities.items()
            }
        else:
            probabilities = typed_probabilities
        return ResponseDistribution(
            responses=tuple(ResponseShare(response=response, probability=probability)
                            for response, probability in sorted(probabilities.items(), key=lambda item: item[0].value)),
            sample_size=len(current), fallback=context[0] if context else source,
        )
