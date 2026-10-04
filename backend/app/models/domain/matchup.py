from pydantic import Field, model_validator

from app.models.domain.base import DomainModel
from app.models.domain.profile import MetricEstimate, PitchType


class Confidence(DomainModel):
    value: float = Field(ge=0, le=1)
    sample_size: int | None = Field(default=None, ge=0)
    explanation: str = Field(min_length=1)


class PitchMatchupExplanation(DomainModel):
    pitch_type: PitchType
    pitcher_usage: float = Field(ge=0, le=1)
    hitter_metric: MetricEstimate
    pitcher_metric: MetricEstimate
    impact: float
    summary: str = Field(min_length=1)


class MatchupResult(DomainModel):
    pitcher_id: int = Field(gt=0)
    hitter_id: int = Field(gt=0)
    score: float = Field(ge=0, le=100)
    confidence: Confidence
    explanations: tuple[PitchMatchupExplanation, ...] = ()
    biggest_advantage: PitchMatchupExplanation | None = None
    biggest_disadvantage: PitchMatchupExplanation | None = None

    @model_validator(mode="after")
    def validate_extremes(self) -> "MatchupResult":
        positive = [item for item in self.explanations if item.impact > 0]
        negative = [item for item in self.explanations if item.impact < 0]
        if positive:
            if self.biggest_advantage not in positive or self.biggest_advantage.impact != max(item.impact for item in positive):
                raise ValueError("biggest_advantage must have the highest positive impact")
        elif self.biggest_advantage is not None:
            raise ValueError("biggest_advantage requires a positive explanation")
        if negative:
            if self.biggest_disadvantage not in negative or self.biggest_disadvantage.impact != min(item.impact for item in negative):
                raise ValueError("biggest_disadvantage must have the lowest negative impact")
        elif self.biggest_disadvantage is not None:
            raise ValueError("biggest_disadvantage requires a negative explanation")
        if len({item.pitch_type for item in self.explanations}) != len(self.explanations):
            raise ValueError("explanations must have unique pitch types")
        return self
