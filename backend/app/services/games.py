"""Game queries shared by the formatted and raw HTTP controllers."""

from datetime import date
from typing import Protocol

from pydantic import ValidationError

from app.models.game_read import GameDetail, GamesResponse
from app.services.game_detail import parse_game_detail
from app.services.schedule import parse_schedule


class InvalidMlbResponse(Exception):
    """The upstream payload cannot be represented by a game read model."""


class GameSource(Protocol):
    def get_schedule_raw(self, game_date: date) -> bytes: ...

    def get_game_raw(self, game_pk: int) -> bytes: ...


class GameSnapshotStore(Protocol):
    def put(self, kind: str, resource_key: str, payload: bytes) -> None: ...


class GameService:
    def __init__(self, client: GameSource, snapshots: GameSnapshotStore | None = None) -> None:
        self.client = client
        self.snapshots = snapshots

    def schedule(self, game_date: date) -> GamesResponse:
        try:
            return parse_schedule(self.raw_schedule(game_date), game_date)
        except ValidationError as exc:
            raise InvalidMlbResponse("MLB Stats API returned an unexpected schedule format") from exc

    def detail(self, game_pk: int) -> GameDetail:
        try:
            return parse_game_detail(self.raw_game(game_pk), game_pk)
        except (ValidationError, ValueError) as exc:
            raise InvalidMlbResponse("MLB Stats API returned an unexpected game format") from exc

    def raw_schedule(self, game_date: date) -> bytes:
        payload = self.client.get_schedule_raw(game_date)
        if self.snapshots is not None:
            self.snapshots.put("schedule", game_date.isoformat(), payload)
        return payload

    def raw_game(self, game_pk: int) -> bytes:
        payload = self.client.get_game_raw(game_pk)
        if self.snapshots is not None:
            self.snapshots.put("game", str(game_pk), payload)
        return payload
