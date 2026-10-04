from datetime import date
from pathlib import Path

import pytest

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

    def get_schedule_raw(self, game_date: date) -> bytes:
        self.dates.append(game_date)
        return self.schedule

    def get_game_raw(self, game_pk: int) -> bytes:
        self.game_ids.append(game_pk)
        return self.game


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
