"""Model-layer contract and an interpretable, fixture-ready baseline scorer."""

from abc import ABC, abstractmethod

from app.analytics.profiles import DEFAULT_XWOBA_PRIOR
from app.analytics.regression import RegressionPrior, regress_metric, sample_confidence
from app.models.domain.matchup import Confidence, MatchupResult, PitchMatchupExplanation
from app.models.domain.profile import HitterProfile, MetricEstimate, MetricUnit, PitcherProfile
from app.models.domain.player import BatterSide


class MatchupModel(ABC):
    @abstractmethod
    def calculate(self, pitcher_profile: PitcherProfile, hitter_profile: HitterProfile) -> MatchupResult:
        """Score a hitter's advantage against a pitcher's expected pitch mix."""


def score_band(score: float) -> str:
    if not 0 <= score <= 100:
        raise ValueError("score must be between 0 and 100")
    if score >= 90:
        return "Elite matchup"
    if score >= 75:
        return "Strong advantage"
    if score >= 55:
        return "Slight advantage"
    if score >= 45:
        return "Neutral"
    if score >= 25:
        return "Slight disadvantage"
    return "Poor matchup"


def _xwoba(metrics: tuple[MetricEstimate, ...], prior: RegressionPrior) -> MetricEstimate:
    metric = next((item for item in metrics if item.name == "xwoba"), None)
    return regress_metric(
        "xwoba", MetricUnit.VALUE, metric.raw_value if metric else None,
        metric.sample_size if metric else 0, prior,
    )


class WeightedMatchupModel(MatchupModel):
    """Usage-weighted xwOBA opportunity index; 50 is the configured neutral prior."""

    def __init__(self, prior: RegressionPrior = DEFAULT_XWOBA_PRIOR) -> None:
        self.prior = prior

    def calculate(self, pitcher_profile: PitcherProfile, hitter_profile: HitterProfile) -> MatchupResult:
        if (pitcher_profile.batter_side is not None
                and hitter_profile.hitter.bats != BatterSide.SWITCH
                and pitcher_profile.batter_side != hitter_profile.hitter.bats):
            raise ValueError("pitcher split does not match hitter batting side")
        hitter_pitches = {
            (pitch.pitch_type, pitch.pitcher_hand): pitch
            for pitch in hitter_profile.pitches
        }
        explanations = []
        confidence = 0.0
        for pitcher_pitch in pitcher_profile.pitches:
            hitter_pitch = hitter_pitches.get((pitcher_pitch.pitch_type, pitcher_profile.pitcher.throws))
            hitter_metric = _xwoba(hitter_pitch.metrics if hitter_pitch else (), self.prior)
            pitcher_metric = _xwoba(pitcher_pitch.metrics, self.prior)
            hitter_value = hitter_metric.adjusted_value if hitter_metric.adjusted_value is not None else self.prior.average
            pitcher_value = pitcher_metric.adjusted_value if pitcher_metric.adjusted_value is not None else self.prior.average
            # Both inputs measure xwOBA on contact; averaging keeps the neutral point fixed.
            combined = (hitter_value + pitcher_value) / 2
            effective_sample = min(hitter_metric.sample_size, pitcher_metric.sample_size)
            impact = (pitcher_pitch.usage * (combined - self.prior.average) * 100
                      if effective_sample else 0.0)
            confidence += pitcher_pitch.usage * sample_confidence(effective_sample, self.prior.k)
            explanations.append(PitchMatchupExplanation(
                pitch_type=pitcher_pitch.pitch_type,
                pitcher_usage=pitcher_pitch.usage,
                hitter_metric=hitter_metric,
                pitcher_metric=pitcher_metric,
                impact=impact,
                summary=f"{pitcher_pitch.pitch_type}: {pitcher_pitch.usage:.0%} usage; "
                        f"hitter {hitter_value:.3f}, pitcher allowed {pitcher_value:.3f} adjusted xwOBA",
            ))
        score = max(0.0, min(100.0, 50 + sum(item.impact for item in explanations)))
        return MatchupResult(
            pitcher_id=pitcher_profile.pitcher.player_id,
            hitter_id=hitter_profile.hitter.player_id,
            score=score,
            confidence=Confidence(
                value=confidence,
                sample_size=sum(min(item.hitter_metric.sample_size, item.pitcher_metric.sample_size)
                                for item in explanations),
                explanation="Usage-weighted overlap of hitter and pitcher xwOBA contact samples; "
                            "unobserved pitch types have zero confidence",
            ),
            explanations=tuple(explanations),
            biggest_advantage=max((item for item in explanations if item.impact > 0),
                                  key=lambda item: item.impact, default=None),
            biggest_disadvantage=min((item for item in explanations if item.impact < 0),
                                     key=lambda item: item.impact, default=None),
        )
