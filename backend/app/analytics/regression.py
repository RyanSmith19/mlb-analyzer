"""Configurable sample-size shrinkage for measured metrics."""

from pydantic import Field

from app.models.domain.base import DomainModel
from app.models.domain.profile import MetricEstimate, MetricUnit


class RegressionPrior(DomainModel):
    average: float = Field(ge=0)
    k: float = Field(gt=0)


def regress_metric(
    name: str, unit: MetricUnit, raw_value: float | None, sample_size: int,
    prior: RegressionPrior,
) -> MetricEstimate:
    if sample_size < 0 or (raw_value is None and sample_size != 0):
        raise ValueError("sample_size must be zero when no raw value is available")
    weight = sample_size / (sample_size + prior.k)
    adjusted = prior.average if raw_value is None else weight * raw_value + (1 - weight) * prior.average
    return MetricEstimate(
        name=name, unit=unit, raw_value=raw_value,
        adjusted_value=adjusted, sample_size=sample_size,
    )


def sample_confidence(sample_size: int, k: float) -> float:
    if sample_size < 0 or k <= 0:
        raise ValueError("sample_size must be nonnegative and k positive")
    return sample_size / (sample_size + k)
