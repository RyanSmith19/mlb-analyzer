import importlib.util
from pathlib import Path
from urllib.error import URLError

import pytest


SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "mlb-stats-raw.py"
SCHEDULE = (
    b'{"dates":[{"date":"2026-07-01","games":[{'
    b'"gamePk":1002,'
    b'"gameDate":"2026-07-01T20:10:00Z",'
    b'"status":{"detailedState":"Final"},'
    b'"teams":{'
    b'"away":{"team":{"id":135,"name":"San Diego Padres"},"score":4,'
    b'"probablePitcher":{"fullName":"Away Starter"}},'
    b'"home":{"team":{"id":111,"name":"Boston Red Sox"},"score":2,'
    b'"probablePitcher":{"fullName":"Home Starter"}}'
    b"}}]}]}"
)
EMPTY_SCHEDULE = b'{"dates":[{"date":"2026-07-01","games":[]}]}'


@pytest.fixture
def raw_script():
    spec = importlib.util.spec_from_file_location("mlb_stats_raw_script", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_script_calls_backend_and_prints_raw_json(raw_script, monkeypatch, capsysbinary) -> None:
    requests = []

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

        def read(self):
            return b'{"dates":[{"games":[]}]}'

    def fake_urlopen(request, timeout):
        requests.append((request, timeout))
        return FakeResponse()

    monkeypatch.setattr(raw_script, "urlopen", fake_urlopen)
    assert raw_script.main(["--date", "2026-07-01", "--backend-url", "http://127.0.0.1:9000"]) == 0
    assert requests[0][0].full_url == "http://127.0.0.1:9000/raw/mlb-stats/schedule?date=2026-07-01"
    assert capsysbinary.readouterr().out == b'{"dates":[{"games":[]}]}\n'


def test_script_reports_unreachable_backend(raw_script, monkeypatch, capsys) -> None:
    def fail_urlopen(*_args, **_kwargs):
        raise URLError("offline")

    monkeypatch.setattr(raw_script, "urlopen", fail_urlopen)
    assert raw_script.main(["--date", "2026-07-01"]) == 1
    assert "Could not reach backend" in capsys.readouterr().err


def test_script_fetches_game_feed_by_id(raw_script, monkeypatch, capsysbinary) -> None:
    requests = []

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

        def read(self):
            return b'{"gamePk":123}'

    def fake_urlopen(request, timeout):
        requests.append(request)
        return FakeResponse()

    monkeypatch.setattr(raw_script, "urlopen", fake_urlopen)
    assert raw_script.main(["--game-pk", "123"]) == 0
    assert requests[0].full_url == "http://127.0.0.1:8000/raw/mlb-stats/games/123"
    assert capsysbinary.readouterr().out == b'{"gamePk":123}\n'


def test_script_lists_games_for_date(raw_script, monkeypatch, capsys) -> None:
    requests = []

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

        def read(self):
            return SCHEDULE

    def fake_urlopen(request, timeout):
        requests.append((request, timeout))
        return FakeResponse()

    monkeypatch.setattr(raw_script, "urlopen", fake_urlopen)
    assert raw_script.main(["--list-games", "--date", "2026-07-01"]) == 0
    assert requests[0][0].full_url == "http://127.0.0.1:8000/raw/mlb-stats/schedule?date=2026-07-01"
    assert capsys.readouterr().out == (
        "1002\t2026-07-01T20:10:00Z\tSan Diego Padres 4 at Boston Red Sox 2\t"
        "(Final, probables: Away Starter / Home Starter)\n"
    )


def test_script_lists_empty_games_date(raw_script, monkeypatch, capsys) -> None:
    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

        def read(self):
            return EMPTY_SCHEDULE

    monkeypatch.setattr(raw_script, "urlopen", lambda *_args, **_kwargs: FakeResponse())
    assert raw_script.main(["--list-games", "--date", "2026-07-01"]) == 0
    assert capsys.readouterr().out == "No games found on 2026-07-01\n"


def test_script_filters_games_by_team_identifier(raw_script, monkeypatch, capsys) -> None:
    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

        def read(self):
            return SCHEDULE

    monkeypatch.setattr(raw_script, "urlopen", lambda *_args, **_kwargs: FakeResponse())
    assert raw_script.main(["--team", "SD", "--date", "2026-07-01"]) == 0
    assert "San Diego Padres 4 at Boston Red Sox 2" in capsys.readouterr().out


def test_script_filters_games_by_full_team_name(raw_script, monkeypatch, capsys) -> None:
    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

        def read(self):
            return SCHEDULE

    monkeypatch.setattr(raw_script, "urlopen", lambda *_args, **_kwargs: FakeResponse())
    assert raw_script.main(["--team", "Padres", "--date", "2026-07-01"]) == 0
    assert "San Diego Padres 4 at Boston Red Sox 2" in capsys.readouterr().out


def test_script_supports_multiple_dates_for_team_filter(raw_script, monkeypatch, capsys) -> None:
    requests = []

    class FakeResponse:
        def __init__(self, payload):
            self.payload = payload

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

        def read(self):
            return self.payload

    def fake_urlopen(request, timeout):
        requests.append(request.full_url)
        if "2026-07-01" in request.full_url:
            return FakeResponse(SCHEDULE)
        return FakeResponse(
            b'{"dates":[{"date":"2026-07-02","games":[{'
            b'"gamePk":2001,'
            b'"gameDate":"2026-07-02T17:10:00Z",'
            b'"status":{"abstractGameState":"Preview","startTimeTBD":true},'
            b'"teams":{'
            b'"away":{"team":{"id":121,"name":"New York Mets"}},'
            b'"home":{"team":{"id":135,"name":"San Diego Padres"}}'
            b"}}]}]}"
        )

    monkeypatch.setattr(raw_script, "urlopen", fake_urlopen)
    assert raw_script.main(["--team", "Padres", "--date", "2026-07-01", "--date", "2026-07-02"]) == 0
    assert requests == [
        "http://127.0.0.1:8000/raw/mlb-stats/schedule?date=2026-07-01",
        "http://127.0.0.1:8000/raw/mlb-stats/schedule?date=2026-07-02",
    ]
    assert capsys.readouterr().out == (
        "1002\t2026-07-01T20:10:00Z\tSan Diego Padres 4 at Boston Red Sox 2\t"
        "(Final, probables: Away Starter / Home Starter)\n"
        "2001\t2026-07-02T17:10:00Z\tNew York Mets at San Diego Padres\t(Preview, start TBD)\n"
    )


def test_script_rejects_invalid_game_id(raw_script) -> None:
    with pytest.raises(SystemExit) as exc:
        raw_script.main(["--game-pk", "0"])
    assert exc.value.code == 2


def test_script_rejects_date_with_game_id(raw_script) -> None:
    with pytest.raises(SystemExit) as exc:
        raw_script.main(["--game-pk", "123", "--date", "2026-07-01"])
    assert exc.value.code == 2


def test_script_rejects_team_with_game_id(raw_script) -> None:
    with pytest.raises(SystemExit) as exc:
        raw_script.main(["--game-pk", "123", "--team", "SD"])
    assert exc.value.code == 2


def test_script_rejects_multiple_dates_without_list_mode(raw_script) -> None:
    with pytest.raises(SystemExit) as exc:
        raw_script.main(["--date", "2026-07-01", "--date", "2026-07-02"])
    assert exc.value.code == 2


def test_script_rejects_invalid_date(raw_script) -> None:
    with pytest.raises(SystemExit) as exc:
        raw_script.main(["--date", "July 1"])
    assert exc.value.code == 2
