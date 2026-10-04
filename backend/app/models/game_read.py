"""Normalized game data shared by HTTP, browser, and CLI consumers."""

from datetime import date, datetime

from pydantic import BaseModel


class GameTeam(BaseModel):
    team_id: int
    name: str
    score: int | None
    probable_pitcher_name: str | None


class GameSummary(BaseModel):
    game_id: int
    game_date: datetime
    status: str
    start_time_tbd: bool
    away: GameTeam
    home: GameTeam


class GamesResponse(BaseModel):
    date: date
    games: list[GameSummary]


class Score(BaseModel):
    runs: int | None
    hits: int | None
    errors: int | None


class Inning(BaseModel):
    number: int
    away_runs: int | None
    home_runs: int | None


class BattingLine(BaseModel):
    player_id: int
    name: str
    position: str | None
    at_bats: int | None
    runs: int | None
    hits: int | None
    rbi: int | None
    walks: int | None
    strikeouts: int | None


class PitchingLine(BaseModel):
    player_id: int
    name: str
    innings_pitched: str | None
    hits: int | None
    runs: int | None
    earned_runs: int | None
    walks: int | None
    strikeouts: int | None
    pitches: int | None


class TeamBox(BaseModel):
    team_id: int
    name: str
    abbreviation: str | None
    score: Score
    batting: list[BattingLine]
    pitching: list[PitchingLine]


class PlaySummary(BaseModel):
    inning: int
    half: str
    event: str | None
    description: str
    is_scoring_play: bool
    away_score: int | None
    home_score: int | None


class GameDetail(BaseModel):
    game_id: int
    game_date: datetime
    status: str
    venue: str | None
    away: TeamBox
    home: TeamBox
    innings: list[Inning]
    plays: list[PlaySummary]
