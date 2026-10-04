from enum import Enum

from pydantic import Field

from app.models.domain.base import DomainModel


class Handedness(str, Enum):
    LEFT = "L"
    RIGHT = "R"


class BatterSide(str, Enum):
    LEFT = "L"
    RIGHT = "R"
    SWITCH = "S"


class Player(DomainModel):
    player_id: int = Field(gt=0)
    full_name: str = Field(min_length=1)
    team_id: int | None = Field(default=None, gt=0)


class Pitcher(Player):
    throws: Handedness


class Hitter(Player):
    bats: BatterSide
