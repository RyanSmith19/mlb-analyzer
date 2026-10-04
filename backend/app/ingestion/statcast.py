"""Statcast CSV adapter; analytics consumes only PitchObservation."""

import csv
from datetime import date
from pathlib import Path
from typing import Iterable, Mapping

from pydantic import Field, field_validator, model_validator

from app.models.domain.base import DomainModel
from app.models.domain.player import BatterSide, Handedness
from app.models.domain.profile import PitchType


class PitchObservation(DomainModel):
    game_date: date
    game_id: int = Field(gt=0)
    at_bat_number: int = Field(gt=0)
    pitch_number: int = Field(gt=0)
    pitcher_id: int = Field(gt=0)
    hitter_id: int = Field(gt=0)
    pitcher_hand: Handedness
    batter_side: BatterSide
    pitch_type: PitchType
    velocity_mph: float | None = Field(default=None, ge=0)
    horizontal_movement_ft: float | None = None
    vertical_movement_ft: float | None = None
    zone: int | None = Field(default=None, ge=1)
    plate_x_ft: float | None = None
    plate_z_ft: float | None = None
    balls: int | None = Field(default=None, ge=0, le=3)
    strikes: int | None = Field(default=None, ge=0, le=2)
    description: str = Field(min_length=1)
    event: str | None = None
    exit_velocity_mph: float | None = Field(default=None, ge=0)
    launch_angle_deg: float | None = None
    estimated_woba: float | None = Field(default=None, ge=0)
    woba_value: float | None = Field(default=None, ge=0)
    woba_denominator: float | None = Field(default=None, ge=0)
    launch_speed_angle: int | None = Field(default=None, ge=1, le=6)

    @field_validator("batter_side")
    @classmethod
    def concrete_batter_side(cls, value: BatterSide) -> BatterSide:
        if value == BatterSide.SWITCH:
            raise ValueError("Statcast stand must be L or R")
        return value

    @model_validator(mode="after")
    def validate_batted_ball(self) -> "PitchObservation":
        if self.estimated_woba is not None and self.exit_velocity_mph is None:
            raise ValueError("estimated_woba requires exit_velocity_mph")
        return self


_FIELDS = {
    "game_date": "game_date",
    "game_pk": "game_id",
    "at_bat_number": "at_bat_number",
    "pitch_number": "pitch_number",
    "pitcher": "pitcher_id",
    "batter": "hitter_id",
    "p_throws": "pitcher_hand",
    "stand": "batter_side",
    "pitch_type": "pitch_type",
    "release_speed": "velocity_mph",
    "pfx_x": "horizontal_movement_ft",
    "pfx_z": "vertical_movement_ft",
    "zone": "zone",
    "plate_x": "plate_x_ft",
    "plate_z": "plate_z_ft",
    "balls": "balls",
    "strikes": "strikes",
    "description": "description",
    "events": "event",
    "launch_speed": "exit_velocity_mph",
    "launch_angle": "launch_angle_deg",
    "estimated_woba_using_speedangle": "estimated_woba",
    "woba_value": "woba_value",
    "woba_denom": "woba_denominator",
    "launch_speed_angle": "launch_speed_angle",
}
_REQUIRED = frozenset({
    "game_date", "game_pk", "at_bat_number", "pitch_number", "pitcher",
    "batter", "p_throws", "stand", "pitch_type", "description",
})


def parse_statcast_row(row: Mapping[str, str | None]) -> PitchObservation:
    missing = sorted(key for key in _REQUIRED if not row.get(key) or not row[key].strip())
    if missing:
        raise ValueError(f"missing required Statcast fields: {', '.join(missing)}")
    values = {
        internal: row[source].strip() if row.get(source) and row[source].strip() else None
        for source, internal in _FIELDS.items()
    }
    return PitchObservation.model_validate(values)


def parse_statcast_rows(rows: Iterable[Mapping[str, str | None]]) -> tuple[PitchObservation, ...]:
    return tuple(parse_statcast_row(row) for row in rows)


def load_statcast_csv(path: Path) -> tuple[PitchObservation, ...]:
    with path.open(newline="", encoding="utf-8") as stream:
        return parse_statcast_rows(csv.DictReader(stream))
