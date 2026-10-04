"""Stable HTTP response contracts for fixture-backed matchup views."""

from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.matchup.model import score_band
from app.models.domain import (
    Confidence, Game, GameStatus, Hitter, HitterPitchProfile, HitterProfile,
    MetricEstimate, MetricUnit, MatchupResult, Pitcher, PitcherPitchProfile,
    PitcherProfile, Team,
)


class ReadModel(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


class PlayerSummary(ReadModel):
    player_id: int = Field(gt=0)
    full_name: str
    handedness: Literal["L", "R", "S"]

    @classmethod
    def from_player(cls, player: Pitcher | Hitter) -> "PlayerSummary":
        hand = player.throws if isinstance(player, Pitcher) else player.bats
        return cls(player_id=player.player_id, full_name=player.full_name, handedness=hand.value)


class MetricRead(ReadModel):
    name: str
    unit: MetricUnit
    raw_value: float | None
    adjusted_value: float | None
    sample_size: int = Field(ge=0)

    @classmethod
    def from_metric(cls, metric: MetricEstimate) -> "MetricRead":
        return cls.model_validate(metric.model_dump())


class ConfidenceRead(ReadModel):
    value: float = Field(ge=0, le=1)
    sample_size: int | None = Field(ge=0)
    explanation: str

    @classmethod
    def from_confidence(cls, confidence: Confidence) -> "ConfidenceRead":
        return cls.model_validate(confidence.model_dump())


class PitchBreakdown(ReadModel):
    pitch_type: str
    pitcher_usage: float = Field(ge=0, le=1)
    pitcher_pitch_count: int = Field(ge=0)
    hitter_pitches_seen: int = Field(ge=0)
    hitter_xwoba: MetricRead
    pitcher_xwoba: MetricRead
    impact: float
    summary: str


class MatchupRead(ReadModel):
    pitcher: PlayerSummary
    hitter: PlayerSummary
    score: float = Field(ge=0, le=100)
    score_band: str
    score_type: Literal["contact_quality_index"] = "contact_quality_index"
    data_source: Literal["synthetic_fixture"] = "synthetic_fixture"
    calibrated: Literal[False] = False
    confidence: ConfidenceRead
    top_explanation: str
    pitches: tuple[PitchBreakdown, ...]
    biggest_advantage_pitch_type: str | None
    biggest_disadvantage_pitch_type: str | None

    @classmethod
    def from_domain(
        cls, pitcher_profile: PitcherProfile, hitter_profile: HitterProfile,
        result: MatchupResult,
    ) -> "MatchupRead":
        top_driver = max(
            (item for item in result.explanations if item.impact != 0),
            key=lambda item: abs(item.impact), default=None,
        )
        pitcher_pitches = {item.pitch_type: item for item in pitcher_profile.pitches}
        hitter_pitches = {
            item.pitch_type: item for item in hitter_profile.pitches
            if item.pitcher_hand == pitcher_profile.pitcher.throws
        }
        return cls(
            pitcher=PlayerSummary.from_player(pitcher_profile.pitcher),
            hitter=PlayerSummary.from_player(hitter_profile.hitter),
            score=result.score,
            score_band=score_band(result.score),
            confidence=ConfidenceRead.from_confidence(result.confidence),
            top_explanation=top_driver.summary if top_driver else
            "No directional contact-quality signal in the available sample",
            pitches=tuple(
                PitchBreakdown(
                    pitch_type=item.pitch_type,
                    pitcher_usage=item.pitcher_usage,
                    pitcher_pitch_count=pitcher_pitches[item.pitch_type].pitch_count,
                    hitter_pitches_seen=hitter_pitches[item.pitch_type].pitches_seen
                    if item.pitch_type in hitter_pitches else 0,
                    hitter_xwoba=MetricRead.from_metric(item.hitter_metric),
                    pitcher_xwoba=MetricRead.from_metric(item.pitcher_metric),
                    impact=item.impact,
                    summary=item.summary,
                )
                for item in result.explanations
            ),
            biggest_advantage_pitch_type=result.biggest_advantage.pitch_type
            if result.biggest_advantage else None,
            biggest_disadvantage_pitch_type=result.biggest_disadvantage.pitch_type
            if result.biggest_disadvantage else None,
        )


class PitcherPitchRead(ReadModel):
    pitch_type: str
    batter_side: Literal["L", "R"] | None
    usage: float = Field(ge=0, le=1)
    pitch_count: int = Field(ge=0)
    metrics: tuple[MetricRead, ...]

    @classmethod
    def from_profile(cls, pitch: PitcherPitchProfile) -> "PitcherPitchRead":
        return cls(
            pitch_type=pitch.pitch_type,
            batter_side=pitch.batter_side.value if pitch.batter_side else None,
            usage=pitch.usage,
            pitch_count=pitch.pitch_count,
            metrics=tuple(MetricRead.from_metric(item) for item in pitch.metrics),
        )


class PitcherProfileRead(ReadModel):
    pitcher: PlayerSummary
    data_source: Literal["synthetic_fixture"] = "synthetic_fixture"
    batter_side: Literal["L", "R"] | None
    total_pitches: int = Field(ge=0)
    pitches: tuple[PitcherPitchRead, ...]

    @classmethod
    def from_profile(cls, profile: PitcherProfile) -> "PitcherProfileRead":
        return cls(
            pitcher=PlayerSummary.from_player(profile.pitcher),
            batter_side=profile.batter_side.value if profile.batter_side else None,
            total_pitches=profile.total_pitches,
            pitches=tuple(PitcherPitchRead.from_profile(item) for item in profile.pitches),
        )


class HitterPitchRead(ReadModel):
    pitch_type: str
    pitcher_hand: Literal["L", "R"]
    pitches_seen: int = Field(ge=0)
    plate_appearances: int | None = Field(ge=0)
    metrics: tuple[MetricRead, ...]

    @classmethod
    def from_profile(cls, pitch: HitterPitchProfile) -> "HitterPitchRead":
        return cls(
            pitch_type=pitch.pitch_type,
            pitcher_hand=pitch.pitcher_hand.value,
            pitches_seen=pitch.pitches_seen,
            plate_appearances=pitch.plate_appearances,
            metrics=tuple(MetricRead.from_metric(item) for item in pitch.metrics),
        )


class HitterProfileRead(ReadModel):
    hitter: PlayerSummary
    data_source: Literal["synthetic_fixture"] = "synthetic_fixture"
    total_pitches_seen: int = Field(ge=0)
    pitches: tuple[HitterPitchRead, ...]

    @classmethod
    def from_profile(cls, profile: HitterProfile) -> "HitterProfileRead":
        return cls(
            hitter=PlayerSummary.from_player(profile.hitter),
            total_pitches_seen=profile.total_pitches_seen,
            pitches=tuple(HitterPitchRead.from_profile(item) for item in profile.pitches),
        )


class TeamSummary(ReadModel):
    team_id: int = Field(gt=0)
    name: str
    abbreviation: str

    @classmethod
    def from_team(cls, team: Team) -> "TeamSummary":
        return cls(team_id=team.team_id, name=team.name, abbreviation=team.abbreviation)


class FixtureGameSummary(ReadModel):
    game_id: int = Field(gt=0)
    game_date: date
    status: GameStatus
    away_team: TeamSummary
    home_team: TeamSummary

    @classmethod
    def from_game(cls, game: Game) -> "FixtureGameSummary":
        return cls(
            game_id=game.game_id, game_date=game.game_date, status=game.status,
            away_team=TeamSummary.from_team(game.away_team),
            home_team=TeamSummary.from_team(game.home_team),
        )


class GameMatchupsRead(ReadModel):
    game: FixtureGameSummary
    data_source: Literal["synthetic_fixture"] = "synthetic_fixture"
    pitcher: PlayerSummary
    matchups: tuple[MatchupRead, ...]
