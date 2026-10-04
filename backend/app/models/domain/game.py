from datetime import date
from enum import Enum

from pydantic import Field, model_validator

from app.models.domain.base import DomainModel


class GameStatus(str, Enum):
    SCHEDULED = "scheduled"
    LIVE = "live"
    FINAL = "final"
    POSTPONED = "postponed"
    CANCELED = "canceled"


class Team(DomainModel):
    team_id: int = Field(gt=0)
    name: str = Field(min_length=1)
    abbreviation: str = Field(min_length=2, max_length=3)


class Game(DomainModel):
    game_id: int = Field(gt=0)
    game_date: date
    away_team: Team
    home_team: Team
    status: GameStatus
    away_probable_pitcher_id: int | None = Field(default=None, gt=0)
    home_probable_pitcher_id: int | None = Field(default=None, gt=0)

    @model_validator(mode="after")
    def distinct_teams(self) -> "Game":
        if self.away_team.team_id == self.home_team.team_id:
            raise ValueError("home and away teams must differ")
        return self
