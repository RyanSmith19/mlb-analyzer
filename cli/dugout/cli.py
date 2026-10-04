"""The dug command-line interface."""

import argparse
from datetime import date
import json
import sys
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from dugout.teams import team_id
from dugout.views import game_detail, schedule


DEFAULT_BACKEND = "http://127.0.0.1:8000"


class BackendError(Exception):
    pass


def valid_date(value: str) -> date:
    try:
        parsed = date.fromisoformat(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("date must be YYYY-MM-DD") from exc
    if parsed.isoformat() != value:
        raise argparse.ArgumentTypeError("date must be YYYY-MM-DD")
    return parsed


def positive_id(value: str) -> int:
    try:
        parsed = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("game ID must be a positive integer") from exc
    if parsed <= 0:
        raise argparse.ArgumentTypeError("game ID must be a positive integer")
    return parsed


def valid_team(value: str) -> int:
    try:
        return team_id(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(str(exc)) from exc


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(prog="dug", description="MLB data from the local Analyzer backend")
    groups = root.add_subparsers(dest="group", required=True)
    games = groups.add_parser("games", help="Formatted game data")
    game_commands = games.add_subparsers(dest="command", required=True)
    raw = groups.add_parser("raw", help="Upstream MLB Stats JSON")
    raw_commands = raw.add_subparsers(dest="command", required=True)

    games_list = game_commands.add_parser("list", help="List scheduled games")
    games_list.add_argument("-d", "--date", type=valid_date, action="append", help="Date (repeatable; default: today)")
    games_list.add_argument("-t", "--team", type=valid_team, help="Team abbreviation or name")
    games_list.add_argument("-f", "--format", choices=("table", "json"), default="table")

    games_show = game_commands.add_parser("show", help="Show a game's score and boxscore")
    games_show.add_argument("game_id", type=positive_id)
    games_show.add_argument("-f", "--format", choices=("table", "json"), default="table")
    games_show.add_argument("-v", "--view", choices=("all", "boxscore", "plays"), default="all",
                            help="Parsed display to show (default: all)")
    games_show.add_argument("-s", "--scoring-only", action="store_true", help="Show only scoring plays")

    raw_schedule = raw_commands.add_parser("schedule", help="Print raw schedule JSON")
    raw_schedule.add_argument("-d", "--date", type=valid_date, help="Date (default: today)")

    raw_game = raw_commands.add_parser("game", help="Print raw game-feed JSON")
    raw_game.add_argument("game_id", type=positive_id)

    for command in (games_list, games_show, raw_schedule, raw_game):
        command.add_argument("-u", "--backend-url", default=DEFAULT_BACKEND, help="Backend base URL")
    return root


def fetch(path: str, backend_url: str) -> bytes:
    url = f"{backend_url.rstrip('/')}/{path.lstrip('/')}"
    request = Request(url, headers={"Accept": "application/json"})
    try:
        with urlopen(request, timeout=15) as response:
            return response.read()
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        try:
            detail = json.loads(detail).get("detail", detail)
        except (ValueError, AttributeError):
            pass
        raise BackendError(f"Backend returned HTTP {exc.code}: {detail}") from exc
    except (URLError, TimeoutError, OSError) as exc:
        raise BackendError(f"Could not reach backend at {backend_url}: {exc}") from exc


def fetch_json(path: str, backend_url: str) -> dict:
    try:
        payload = json.loads(fetch(path, backend_url))
    except (ValueError, UnicodeDecodeError) as exc:
        raise BackendError("Backend returned invalid JSON") from exc
    if not isinstance(payload, dict):
        raise BackendError("Backend returned an unexpected JSON response")
    return payload


def print_json(value: object) -> None:
    print(json.dumps(value, indent=2))


def list_games(args: argparse.Namespace) -> None:
    dates = list(dict.fromkeys(args.date or [date.today()]))
    games = []
    for selected_date in dates:
        query = urlencode({"date": selected_date.isoformat()})
        response = fetch_json(f"games?{query}", args.backend_url)
        day_games = response.get("games")
        if not isinstance(day_games, list):
            raise BackendError("Backend returned an unexpected games response")
        games.extend(game for game in day_games if args.team is None or
                     game["away"]["team_id"] == args.team or game["home"]["team_id"] == args.team)
    games.sort(key=lambda game: (game["game_date"], game["game_id"]))
    if args.format == "json":
        print_json({"dates": [day.isoformat() for day in dates], "games": games})
    else:
        print(schedule(games))


def show_game(args: argparse.Namespace) -> None:
    game = fetch_json(f"games/{args.game_id}", args.backend_url)
    if args.format == "json":
        print_json(game)
        return
    print(game_detail(game, args.view, args.scoring_only))


def print_raw(path: str, backend_url: str) -> None:
    payload = fetch(path, backend_url)
    sys.stdout.buffer.write(payload)
    if payload and not payload.endswith(b"\n"):
        sys.stdout.buffer.write(b"\n")


def main(argv: list[str] | None = None) -> int:
    command_parser = parser()
    args = command_parser.parse_args(argv)
    if args.group == "games" and args.command == "show":
        if args.format == "json" and (args.view != "all" or args.scoring_only):
            command_parser.error("--view and --scoring-only require --format table")
        if args.scoring_only and args.view == "boxscore":
            command_parser.error("--scoring-only requires --view all or --view plays")
    try:
        if args.group == "games" and args.command == "list":
            list_games(args)
        elif args.group == "games" and args.command == "show":
            show_game(args)
        elif args.group == "raw" and args.command == "schedule":
            selected_date = args.date or date.today()
            print_raw(f"raw/mlb-stats/schedule?{urlencode({'date': selected_date.isoformat()})}", args.backend_url)
        else:
            print_raw(f"raw/mlb-stats/games/{args.game_id}", args.backend_url)
    except (BackendError, KeyError, TypeError) as exc:
        print(f"dug: {exc}", file=sys.stderr)
        return 1
    return 0
