"""A transparent pitch-sequence estimate, not a calibrated prediction."""

from collections import defaultdict
from datetime import date
from enum import Enum
from typing import Iterable, Literal

from pydantic import Field, model_validator

from app.analytics.contact import ContactResult, HitterContactModel
from app.analytics.location import ZoneLocationModel
from app.analytics.regression import sample_confidence
from app.analytics.response import HitterResponseModel, PitchResponse
from app.analytics.selection import PitchSelectionDistribution, PitchSelectionModel
from app.ingestion.statcast import PitchObservation
from app.models.domain.base import DomainModel
from app.models.domain.matchup import Confidence
from app.models.domain.player import BatterSide, Hitter, Pitcher


class PlateAppearanceOutcome(str, Enum):
    STRIKEOUT = "strikeout"
    WALK = "walk"
    HOME_RUN = "home_run"
    NON_HOME_RUN_HIT = "non_home_run_hit"
    OUT = "out"
    HIT_BY_PITCH = "hit_by_pitch"
    IN_PLAY_UNKNOWN = "in_play_unknown"
    UNRESOLVED = "unresolved"


class OutcomeShare(DomainModel):
    outcome: PlateAppearanceOutcome
    probability: float = Field(ge=0, le=1)


class PlateAppearanceEstimate(DomainModel):
    pitcher_id: int = Field(gt=0)
    hitter_id: int = Field(gt=0)
    outcomes: tuple[OutcomeShare, ...]
    confidence: Confidence
    first_pitch_mix: PitchSelectionDistribution | None = None
    status: Literal["available", "unavailable"]
    model_version: Literal["empirical_markov_v1"] = "empirical_markov_v1"
    calibrated: Literal[False] = False

    @model_validator(mode="after")
    def validate_distribution(self) -> "PlateAppearanceEstimate":
        if self.status == "available" and abs(sum(item.probability for item in self.outcomes) - 1) > 1e-8:
            raise ValueError("plate appearance outcomes must sum to one")
        if self.status == "unavailable" and self.outcomes:
            raise ValueError("unavailable estimate cannot contain outcomes")
        return self

    def probability_of(self, outcome: PlateAppearanceOutcome) -> float | None:
        if self.status == "unavailable":
            return None
        return next((item.probability for item in self.outcomes if item.outcome == outcome), 0.0)

    def hit_probability(self) -> float | None:
        if self.status == "unavailable":
            return None
        return (self.probability_of(PlateAppearanceOutcome.NON_HOME_RUN_HIT) or 0.0) + (
            self.probability_of(PlateAppearanceOutcome.HOME_RUN) or 0.0
        )


_CONTACT_TO_PA = {
    ContactResult.HOME_RUN: PlateAppearanceOutcome.HOME_RUN,
    ContactResult.NON_HOME_RUN_HIT: PlateAppearanceOutcome.NON_HOME_RUN_HIT,
    ContactResult.OUT: PlateAppearanceOutcome.OUT,
    ContactResult.OTHER: PlateAppearanceOutcome.IN_PLAY_UNKNOWN,
}


class PlateAppearanceModel:
    """Compose selection, location, response, and contact into an absorbing count process."""

    def __init__(
        self, selection: PitchSelectionModel | None = None,
        location: ZoneLocationModel | None = None,
        response: HitterResponseModel | None = None,
        contact: HitterContactModel | None = None,
        *, max_pitches: int = 40, confidence_k: float = 100.0,
    ) -> None:
        if max_pitches <= 0 or confidence_k <= 0:
            raise ValueError("max_pitches and confidence_k must be positive")
        self.selection = selection or PitchSelectionModel()
        self.location = location or ZoneLocationModel()
        self.response = response or HitterResponseModel()
        self.contact = contact or HitterContactModel()
        self.max_pitches = max_pitches
        self.confidence_k = confidence_k

    def estimate(
        self, observations: Iterable[PitchObservation], pitcher: Pitcher,
        hitter: Hitter, batter_side: BatterSide | None = None,
        *, before_date: date | None = None,
    ) -> PlateAppearanceEstimate:
        if hitter.bats == BatterSide.SWITCH and batter_side is None:
            raise ValueError("switch hitters require their actual batting side")
        side = batter_side or hitter.bats
        if side == BatterSide.SWITCH or (hitter.bats != BatterSide.SWITCH and side != hitter.bats):
            raise ValueError("batter_side does not match hitter")
        rows = tuple(row for row in observations if before_date is None or row.game_date < before_date)
        pitcher_rows = tuple(row for row in rows if row.pitcher_id == pitcher.player_id
                             and row.pitcher_hand == pitcher.throws)
        hitter_rows = tuple(row for row in rows if row.hitter_id == hitter.player_id)
        sample = min(
            sum(row.batter_side == side for row in pitcher_rows),
            sum(row.pitcher_hand == pitcher.throws for row in hitter_rows),
        )
        confidence = Confidence(
            value=sample_confidence(sample, self.confidence_k), sample_size=sample,
            explanation="Pitch-count sufficiency only; not historical calibration",
        )
        first_mix = self.selection.estimate(pitcher_rows, pitcher, side, balls=0, strikes=0)
        if not hitter_rows or not first_mix.pitches:
            return PlateAppearanceEstimate(
                pitcher_id=pitcher.player_id, hitter_id=hitter.player_id,
                outcomes=(), confidence=confidence, status="unavailable",
            )

        location_by_type = {
            item.pitch_type: self.location.estimate(pitcher_rows, pitcher, side, item.pitch_type)
            for item in first_mix.pitches
        }
        contact_by_type = {
            item.pitch_type: self.contact.estimate(hitter_rows, hitter, pitcher.throws, item.pitch_type)
            for item in first_mix.pitches
        }
        transitions = {}
        for balls in range(4):
            for strikes in range(3):
                selection = self.selection.estimate(pitcher_rows, pitcher, side, balls=balls, strikes=strikes)
                choices = []
                for pitch in selection.pitches:
                    locations = location_by_type[pitch.pitch_type]
                    zones = ((item.zone, item.probability) for item in locations.zones) if locations.zones else ((None, 1.0),)
                    for zone, zone_weight in zones:
                        responses = self.response.estimate(
                            hitter_rows, hitter, pitcher.throws, pitch.pitch_type,
                            zone=zone, balls=balls, strikes=strikes,
                        )
                        for item in responses.responses:
                            choices.append((pitch.pitch_type, item.response,
                                            pitch.probability * zone_weight * item.probability))
                transitions[balls, strikes] = choices
        states: dict[tuple[int, int], float] = {(0, 0): 1.0}
        absorbed: dict[PlateAppearanceOutcome, float] = defaultdict(float)
        for _ in range(self.max_pitches):
            next_states: dict[tuple[int, int], float] = defaultdict(float)
            for (balls, strikes), state_weight in states.items():
                for pitch_type, response, probability in transitions[balls, strikes]:
                    weight = state_weight * probability
                    if response == PitchResponse.BALL:
                        if balls == 3:
                            absorbed[PlateAppearanceOutcome.WALK] += weight
                        else:
                            next_states[balls + 1, strikes] += weight
                    elif response in (PitchResponse.CALLED_STRIKE, PitchResponse.WHIFF,
                                      PitchResponse.STRIKE_OTHER):
                        if strikes == 2:
                            absorbed[PlateAppearanceOutcome.STRIKEOUT] += weight
                        else:
                            next_states[balls, strikes + 1] += weight
                    elif response == PitchResponse.FOUL:
                        next_states[balls, min(strikes + 1, 2)] += weight
                    elif response == PitchResponse.HIT_BY_PITCH:
                        absorbed[PlateAppearanceOutcome.HIT_BY_PITCH] += weight
                    elif response == PitchResponse.IN_PLAY:
                        contact = contact_by_type[pitch_type]
                        if contact.results:
                            for result in contact.results:
                                absorbed[_CONTACT_TO_PA[result.result]] += weight * result.probability
                        else:
                            absorbed[PlateAppearanceOutcome.IN_PLAY_UNKNOWN] += weight
                    else:
                        absorbed[PlateAppearanceOutcome.UNRESOLVED] += weight
            states = next_states
            if sum(states.values()) < 1e-12:
                break
        absorbed[PlateAppearanceOutcome.UNRESOLVED] += sum(states.values())
        total = sum(absorbed.values())
        if total == 0:
            return PlateAppearanceEstimate(
                pitcher_id=pitcher.player_id, hitter_id=hitter.player_id,
                outcomes=(), confidence=confidence, status="unavailable",
            )
        outcomes = tuple(OutcomeShare(outcome=outcome, probability=absorbed[outcome] / total)
                         for outcome in PlateAppearanceOutcome)
        return PlateAppearanceEstimate(
            pitcher_id=pitcher.player_id, hitter_id=hitter.player_id,
            outcomes=outcomes, confidence=confidence, first_pitch_mix=first_mix,
            status="available",
        )
