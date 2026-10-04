"""MLB Stats API schedule payload shape."""

from datetime import date, datetime

from pydantic import BaseModel, Field


class MlbTeam(BaseModel):
    id: int
    name: str


class MlbPitcher(BaseModel):
    full_name: str = Field(alias="fullName")


class MlbSide(BaseModel):
    team: MlbTeam
    score: int | None = None
    probable_pitcher: MlbPitcher | None = Field(default=None, alias="probablePitcher")


class MlbTeams(BaseModel):
    away: MlbSide
    home: MlbSide


class MlbStatus(BaseModel):
    detailed_state: str | None = Field(default=None, alias="detailedState")
    abstract_game_state: str | None = Field(default=None, alias="abstractGameState")
    start_time_tbd: bool = Field(default=False, alias="startTimeTBD")


class MlbGame(BaseModel):
    game_id: int = Field(alias="gamePk")
    game_date: datetime = Field(alias="gameDate")
    status: MlbStatus
    teams: MlbTeams


class MlbDate(BaseModel):
    date: date
    games: list[MlbGame]


class MlbSchedule(BaseModel):
    dates: list[MlbDate]
