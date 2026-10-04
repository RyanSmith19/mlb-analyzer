import importlib.util
import io
import json
from pathlib import Path
import sys
import tarfile
from urllib.error import HTTPError

import pytest


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "cli"))
from dugout import cli  # noqa: E402


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return None

    def read(self):
        return self.payload


def test_games_list_filters_team_across_dates_and_accepts_short_options(monkeypatch, capsys):
    requests = []

    def fake_urlopen(request, timeout):
        requests.append(request.full_url)
        date = "2026-07-01" if "2026-07-01" in request.full_url else "2026-07-02"
        return FakeResponse(json.dumps({"games": [
            {"game_id": 1 if date.endswith("01") else 2, "game_date": f"{date}T20:00:00Z",
             "status": "Final", "away": {"team_id": 135, "name": "San Diego Padres", "score": 4},
             "home": {"team_id": 111, "name": "Boston Red Sox", "score": 2}},
            {"game_id": 3, "game_date": f"{date}T21:00:00Z", "status": "Final",
             "away": {"team_id": 119, "name": "Los Angeles Dodgers", "score": 1},
             "home": {"team_id": 137, "name": "San Francisco Giants", "score": 0}},
        ]}).encode())

    monkeypatch.setattr(cli, "urlopen", fake_urlopen)
    assert cli.main(["games", "list", "-d", "2026-07-01", "-d", "2026-07-02",
                     "-t", "Padres", "-f", "json", "-u", "http://localhost:9000"]) == 0
    assert requests == [
        "http://localhost:9000/games?date=2026-07-01",
        "http://localhost:9000/games?date=2026-07-02",
    ]
    assert [game["game_id"] for game in json.loads(capsys.readouterr().out)["games"]] == [1, 2]


@pytest.mark.parametrize("alias", ["SD", "Padres", "San Diego Padres"])
def test_team_aliases(alias):
    assert cli.valid_team(alias) == 135


def test_games_show_formats_boxscore(monkeypatch, capsys):
    team = {"name": "San Diego Padres", "score": {"runs": 4, "hits": 7, "errors": 0},
            "batting": [{"name": "Batter", "at_bats": 4, "runs": 1, "hits": 2,
                         "rbi": 1, "walks": 0, "strikeouts": 1}],
            "pitching": [{"name": "Starter", "innings_pitched": "6.0", "hits": 3,
                          "runs": 1, "earned_runs": 1, "walks": 2, "strikeouts": 7, "pitches": 89}]}
    payload = {"game_id": 123, "game_date": "2026-07-01T20:00:00Z", "status": "Final",
               "venue": "Petco Park", "away": team, "home": team,
               "innings": [{"number": 1, "away_runs": 2, "home_runs": 0}], "plays": []}
    monkeypatch.setattr(cli, "urlopen", lambda *_args, **_kwargs: FakeResponse(json.dumps(payload).encode()))
    assert cli.main(["games", "show", "123"]) == 0
    output = capsys.readouterr().out
    assert "Petco Park" in output
    assert "TEAM" in output and "R  H  E" in output
    assert "San Diego Padres  2" in output
    assert "Batter" in output and "AB  R  H  RBI  BB  K" in output
    assert "Starter  6.0  3" in output
    assert "No plays available." in output


def test_games_list_displays_probables_and_time_tbd(monkeypatch, capsys):
    payload = {"games": [{
        "game_id": 456, "game_date": "2026-07-01T20:00:00Z", "status": "Preview",
        "start_time_tbd": True,
        "away": {"team_id": 135, "name": "San Diego Padres", "score": None,
                 "probable_pitcher_name": "Away Starter"},
        "home": {"team_id": 111, "name": "Boston Red Sox", "score": None,
                 "probable_pitcher_name": None},
    }]}
    monkeypatch.setattr(cli, "urlopen", lambda *_args, **_kwargs: FakeResponse(json.dumps(payload).encode()))
    assert cli.main(["games", "list", "-d", "2026-07-01"]) == 0
    output = capsys.readouterr().out
    assert "456" in output and "San Diego Padres" in output
    assert "Preview; time TBD" in output
    assert "456 probable starters: Away Starter / TBD" in output


def test_games_show_plays_in_reverse_order_and_filters_scoring(monkeypatch, capsys):
    team = {"name": "San Diego Padres", "abbreviation": "SD",
            "score": {"runs": 1, "hits": 2, "errors": 0}, "batting": [], "pitching": []}
    payload = {"game_id": 123, "game_date": "2026-07-01T20:00:00Z", "status": "Final",
               "venue": None, "away": team, "home": team, "innings": [],
               "plays": [
                   {"inning": 1, "half": "top", "event": "Single", "description": "First play.",
                    "is_scoring_play": False, "away_score": 0, "home_score": 0},
                   {"inning": 2, "half": "bottom", "event": "Home Run", "description": "Scoring play.",
                    "is_scoring_play": True, "away_score": 1, "home_score": 0},
               ]}
    monkeypatch.setattr(cli, "urlopen", lambda *_args, **_kwargs: FakeResponse(json.dumps(payload).encode()))

    assert cli.main(["games", "show", "123", "-v", "plays"]) == 0
    output = capsys.readouterr().out
    assert "No line score yet." in output
    assert output.index("Scoring play.") < output.index("First play.")
    assert "SD 1 - SD 0" in output
    assert "Batting" not in output

    assert cli.main(["games", "show", "123", "-v", "plays", "-s"]) == 0
    output = capsys.readouterr().out
    assert "Scoring play." in output
    assert "First play." not in output


def test_games_show_rejects_table_filters_with_json():
    with pytest.raises(SystemExit) as exc:
        cli.main(["games", "show", "123", "-f", "json", "-v", "plays"])
    assert exc.value.code == 2


def test_raw_game_preserves_json_bytes(monkeypatch, capsysbinary):
    requests = []

    def fake_urlopen(request, timeout):
        requests.append(request.full_url)
        return FakeResponse(b'{"gamePk":123}')

    monkeypatch.setattr(cli, "urlopen", fake_urlopen)
    assert cli.main(["raw", "game", "123"]) == 0
    assert requests == ["http://127.0.0.1:8000/raw/mlb-stats/games/123"]
    assert capsysbinary.readouterr().out == b'{"gamePk":123}\n'


def test_backend_http_error_has_clean_message(monkeypatch, capsys):
    def fake_urlopen(request, timeout):
        raise HTTPError(request.full_url, 404, "Not Found", {}, io.BytesIO(b'{"detail":"Not Found"}'))

    monkeypatch.setattr(cli, "urlopen", fake_urlopen)
    assert cli.main(["games", "show", "123"]) == 1
    assert capsys.readouterr().err == "dug: Backend returned HTTP 404: Not Found\n"


def test_deb_contains_launcher_control_and_python_modules(tmp_path):
    spec = importlib.util.spec_from_file_location("build_dug_deb", ROOT / "scripts" / "build-dug-deb.py")
    assert spec is not None and spec.loader is not None
    builder = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(builder)
    package = builder.build(tmp_path).read_bytes()
    assert package.startswith(b"!<arch>\n")

    members = {}
    position = 8
    while position < len(package):
        header = package[position:position + 60]
        name = header[:16].decode().strip().rstrip("/")
        size = int(header[48:58])
        position += 60
        members[name] = package[position:position + size]
        position += size + size % 2

    assert members["debian-binary"] == b"2.0\n"
    with tarfile.open(fileobj=io.BytesIO(members["control.tar.gz"]), mode="r:gz") as archive:
        control = archive.extractfile("./control").read().decode()
        assert "Package: dugout-mlb-data-analysis\n" in control
        assert "Depends: python3 (>= 3.10)\n" in control
    with tarfile.open(fileobj=io.BytesIO(members["data.tar.gz"]), mode="r:gz") as archive:
        launcher = archive.getmember("./usr/bin/dug")
        assert launcher.mode == 0o755
        assert b"from dugout.cli import main" in archive.extractfile(launcher).read()
        assert archive.getmember("./usr/lib/dugout-mlb-data-analysis/dugout/cli.py")
