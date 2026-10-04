"""Game queries shared by the formatted and raw HTTP controllers."""

from datetime import date
from dataclasses import dataclass
from typing import Callable, Generic, Literal, Protocol, TypeVar

from pydantic import ValidationError

from app.clients.mlb_stats import MLBStatsError
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

    def get(self, kind: str, resource_key: str) -> bytes | None: ...


Value = TypeVar("Value")


@dataclass(frozen=True)
class SourcedValue(Generic[Value]):
    value: Value
    source: Literal["live", "stored"]


class GameService:
    def __init__(self, client: GameSource, snapshots: GameSnapshotStore | None = None) -> None:
        self.client = client
        self.snapshots = snapshots

    def schedule(self, game_date: date) -> GamesResponse:
        return self.schedule_with_source(game_date).value

    def schedule_with_source(self, game_date: date) -> SourcedValue[GamesResponse]:
        raw = self.raw_schedule_with_source(game_date)
        try:
            return SourcedValue(parse_schedule(raw.value, game_date), raw.source)
        except ValidationError as exc:
            raise InvalidMlbResponse("MLB Stats API returned an unexpected schedule format") from exc

    def detail(self, game_pk: int) -> GameDetail:
        return self.detail_with_source(game_pk).value

    def detail_with_source(self, game_pk: int) -> SourcedValue[GameDetail]:
        raw = self.raw_game_with_source(game_pk)
        try:
            return SourcedValue(parse_game_detail(raw.value, game_pk), raw.source)
        except (ValidationError, ValueError) as exc:
            raise InvalidMlbResponse("MLB Stats API returned an unexpected game format") from exc

    def raw_schedule(self, game_date: date) -> bytes:
        return self.raw_schedule_with_source(game_date).value

    def raw_schedule_with_source(self, game_date: date) -> SourcedValue[bytes]:
        return self._read_payload("schedule", game_date.isoformat(), lambda: self.client.get_schedule_raw(game_date))

    def raw_game(self, game_pk: int) -> bytes:
        return self.raw_game_with_source(game_pk).value

    def raw_game_with_source(self, game_pk: int) -> SourcedValue[bytes]:
        return self._read_payload("game", str(game_pk), lambda: self.client.get_game_raw(game_pk))

    def _read_payload(self, kind: str, resource_key: str, fetch: Callable[[], bytes]) -> SourcedValue[bytes]:
        try:
            payload = fetch()
        except MLBStatsError:
            getter = getattr(self.snapshots, "get", None)
            if getter is None:
                raise
            stored = getter(kind, resource_key)
            if stored is None:
                raise
            return SourcedValue(stored, "stored")
        if self.snapshots is not None:
            self.snapshots.put(kind, resource_key, payload)
        return SourcedValue(payload, "live")
