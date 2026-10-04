from datetime import date
from pathlib import Path

import pytest

from app.clients.mlb_stats import MLBStatsError
from app.services.games import GameService, InvalidMlbResponse


SCHEDULE = (Path(__file__).parent / "fixtures" / "mlb_schedule.json").read_bytes()
GAME_FEED = (
    b'{"gamePk":123,"gameData":{'
    b'"datetime":{"dateTime":"2026-07-01T20:10:00Z"},'
    b'"status":{"detailedState":"Preview"},'
    b'"teams":{"away":{"id":135,"name":"San Diego Padres"},'
    b'"home":{"id":111,"name":"Boston Red Sox"}}}}'
)


class StubSource:
    def __init__(self) -> None:
        self.schedule = SCHEDULE
        self.game = GAME_FEED
        self.dates: list[date] = []
        self.game_ids: list[int] = []
        self.error: Exception | None = None

    def get_schedule_raw(self, game_date: date) -> bytes:
        self.dates.append(game_date)
        if self.error is not None:
            raise self.error
        return self.schedule

    def get_game_raw(self, game_pk: int) -> bytes:
        self.game_ids.append(game_pk)
        if self.error is not None:
            raise self.error
        return self.game


class StubSnapshots:
    def __init__(self) -> None:
        self.payloads: dict[tuple[str, str], bytes] = {}
        self.reads: list[tuple[str, str]] = []
        self.writes: list[tuple[str, str, bytes]] = []

    def get(self, kind: str, resource_key: str) -> bytes | None:
        self.reads.append((kind, resource_key))
        return self.payloads.get((kind, resource_key))

    def put(self, kind: str, resource_key: str, payload: bytes) -> None:
        self.writes.append((kind, resource_key, payload))
        self.payloads[(kind, resource_key)] = payload


def test_game_service_exposes_raw_and_normalized_data_without_http() -> None:
    source = StubSource()
    service = GameService(source)
    selected_date = date(2026, 7, 1)

    assert service.raw_schedule(selected_date) == SCHEDULE
    assert service.schedule(selected_date).games[1].away.name == "Away Club"
    assert service.raw_game(123) == GAME_FEED
    assert service.detail(123).away.name == "San Diego Padres"
    assert source.dates == [selected_date, selected_date]
    assert source.game_ids == [123, 123]


def test_game_service_reports_unexpected_upstream_shapes() -> None:
    source = StubSource()
    service = GameService(source)
    source.schedule = b'{}'

    with pytest.raises(InvalidMlbResponse, match="unexpected schedule format"):
        service.schedule(date(2026, 7, 1))
    with pytest.raises(InvalidMlbResponse, match="unexpected game format"):
        service.detail(456)


def test_game_service_records_live_reads_and_provenance() -> None:
    source = StubSource()
    snapshots = StubSnapshots()
    service = GameService(source, snapshots)

    assert service.schedule_with_source(date(2026, 7, 1)).source == "live"
    assert service.detail_with_source(123).source == "live"
    assert snapshots.writes == [
        ("schedule", "2026-07-01", SCHEDULE),
        ("game", "123", GAME_FEED),
    ]
    assert snapshots.reads == []


def test_game_service_uses_stored_bytes_for_schedule_and_game_on_mlb_error() -> None:
    source = StubSource()
    source.error = MLBStatsError("MLB Stats API is unavailable")
    snapshots = StubSnapshots()
    snapshots.payloads = {("schedule", "2026-07-01"): SCHEDULE, ("game", "123"): GAME_FEED}
    service = GameService(source, snapshots)

    assert service.raw_schedule_with_source(date(2026, 7, 1)).value == SCHEDULE
    assert service.schedule_with_source(date(2026, 7, 1)).value.games[1].away.name == "Away Club"
    assert service.raw_game_with_source(123).value == GAME_FEED
    assert service.detail_with_source(123).value.away.name == "San Diego Padres"
    assert service.schedule_with_source(date(2026, 7, 1)).source == "stored"
    assert service.detail_with_source(123).source == "stored"
    assert snapshots.reads == [
        ("schedule", "2026-07-01"),
        ("schedule", "2026-07-01"),
        ("game", "123"),
        ("game", "123"),
        ("schedule", "2026-07-01"),
        ("game", "123"),
    ]
    assert snapshots.writes == []


def test_game_service_re_raises_mlb_error_when_snapshot_is_missing() -> None:
    source = StubSource()
    source.error = MLBStatsError("MLB Stats API is unavailable")
    service = GameService(source, StubSnapshots())

    with pytest.raises(MLBStatsError, match="unavailable"):
        service.schedule(date(2026, 7, 1))
    with pytest.raises(MLBStatsError, match="unavailable"):
        service.raw_game(123)


def test_game_service_does_not_fall_back_for_other_errors() -> None:
    source = StubSource()
    source.error = RuntimeError("unexpected client failure")
    snapshots = StubSnapshots()
    snapshots.payloads[("schedule", "2026-07-01")] = SCHEDULE

    with pytest.raises(RuntimeError, match="unexpected client failure"):
        GameService(source, snapshots).schedule(date(2026, 7, 1))
    assert snapshots.reads == []
