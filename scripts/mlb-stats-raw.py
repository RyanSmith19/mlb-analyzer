#!/usr/bin/env python3
"""Print raw MLB schedule or game-feed JSON returned by the local backend."""

import argparse
from datetime import date
import json
import sys
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


TEAM_ALIASES = {
    "109": 109,
    "ari": 109,
    "arizona diamondbacks": 109,
    "diamondbacks": 109,
    "d-backs": 109,
    "144": 144,
    "atl": 144,
    "atlanta braves": 144,
    "braves": 144,
    "110": 110,
    "bal": 110,
    "baltimore orioles": 110,
    "orioles": 110,
    "111": 111,
    "bos": 111,
    "boston red sox": 111,
    "red sox": 111,
    "112": 112,
    "chc": 112,
    "chicago cubs": 112,
    "cubs": 112,
    "145": 145,
    "cws": 145,
    "chw": 145,
    "chicago white sox": 145,
    "white sox": 145,
    "113": 113,
    "cin": 113,
    "cincinnati reds": 113,
    "reds": 113,
    "114": 114,
    "cle": 114,
    "cleveland guardians": 114,
    "guardians": 114,
    "115": 115,
    "col": 115,
    "colorado rockies": 115,
    "rockies": 115,
    "116": 116,
    "det": 116,
    "detroit tigers": 116,
    "tigers": 116,
    "117": 117,
    "hou": 117,
    "houston astros": 117,
    "astros": 117,
    "118": 118,
    "kc": 118,
    "kcr": 118,
    "kansas city royals": 118,
    "royals": 118,
    "108": 108,
    "laa": 108,
    "ana": 108,
    "los angeles angels": 108,
    "angels": 108,
    "119": 119,
    "lad": 119,
    "la dodgers": 119,
    "los angeles dodgers": 119,
    "dodgers": 119,
    "146": 146,
    "mia": 146,
    "florida marlins": 146,
    "miami marlins": 146,
    "marlins": 146,
    "158": 158,
    "mil": 158,
    "milwaukee brewers": 158,
    "brewers": 158,
    "142": 142,
    "min": 142,
    "minnesota twins": 142,
    "twins": 142,
    "121": 121,
    "nym": 121,
    "new york mets": 121,
    "mets": 121,
    "147": 147,
    "nyy": 147,
    "new york yankees": 147,
    "yankees": 147,
    "133": 133,
    "ath": 133,
    "oak": 133,
    "oakland athletics": 133,
    "athletics": 133,
    "a's": 133,
    "143": 143,
    "phi": 143,
    "philadelphia phillies": 143,
    "phillies": 143,
    "134": 134,
    "pit": 134,
    "pittsburgh pirates": 134,
    "pirates": 134,
    "135": 135,
    "sd": 135,
    "sdp": 135,
    "san diego padres": 135,
    "padres": 135,
    "136": 136,
    "sea": 136,
    "seattle mariners": 136,
    "mariners": 136,
    "137": 137,
    "sf": 137,
    "sfg": 137,
    "san francisco giants": 137,
    "giants": 137,
    "138": 138,
    "stl": 138,
    "st. louis cardinals": 138,
    "st louis cardinals": 138,
    "saint louis cardinals": 138,
    "cardinals": 138,
    "139": 139,
    "tb": 139,
    "tbr": 139,
    "tampa bay rays": 139,
    "rays": 139,
    "140": 140,
    "tex": 140,
    "texas rangers": 140,
    "rangers": 140,
    "141": 141,
    "tor": 141,
    "toronto blue jays": 141,
    "blue jays": 141,
    "120": 120,
    "wsh": 120,
    "was": 120,
    "washington nationals": 120,
    "nationals": 120,
}


def game_date(value: str) -> date:
    try:
        parsed = date.fromisoformat(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("date must be YYYY-MM-DD") from exc
    if parsed.isoformat() != value:
        raise argparse.ArgumentTypeError("date must be YYYY-MM-DD")
    return parsed


def game_pk(value: str) -> int:
    try:
        parsed = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("game ID must be a positive integer") from exc
    if parsed <= 0:
        raise argparse.ArgumentTypeError("game ID must be a positive integer")
    return parsed


def team_identifier(value: str) -> str:
    normalized = " ".join(value.lower().replace(".", "").split())
    if normalized not in TEAM_ALIASES and len(normalized) <= 1:
        raise argparse.ArgumentTypeError("team must be a short identifier or team name")
    return value


def format_games_list(payloads: list[tuple[date, bytes]], team: str | None = None) -> str:
    rows = []
    requested_dates = []
    for selected_date, payload in payloads:
        requested_dates.append(selected_date.isoformat())
        rows.extend(schedule_games(payload, selected_date, team))

    if not rows:
        date_label = ", ".join(requested_dates)
        team_label = f" for {team}" if team else ""
        return f"No games found{team_label} on {date_label}\n"

    return "\n".join(format_game_row(game) for game in rows) + "\n"


def schedule_games(payload: bytes, selected_date: date, team: str | None = None) -> list[dict]:
    data = json.loads(payload)
    games = []
    for schedule_date in data.get("dates", []):
        if schedule_date.get("date") != selected_date.isoformat():
            continue
        for game in schedule_date.get("games", []):
            if team is None or game_matches_team(game, team):
                games.append(normalize_game(game))
    games.sort(key=lambda game: (game["game_date"], game["game_id"]))
    return games


def normalize_game(game: dict) -> dict:
    status = game.get("status", {})
    teams = game["teams"]
    return {
        "game_id": game["gamePk"],
        "game_date": game["gameDate"],
        "status": status.get("detailedState") or status.get("abstractGameState") or "Unknown",
        "start_time_tbd": status.get("startTimeTBD", False),
        "away": normalize_team_side(teams["away"]),
        "home": normalize_team_side(teams["home"]),
    }


def normalize_team_side(side: dict) -> dict:
    team = side["team"]
    probable_pitcher = side.get("probablePitcher")
    return {
        "team_id": team.get("id"),
        "name": team["name"],
        "score": side.get("score"),
        "probable_pitcher_name": probable_pitcher.get("fullName") if probable_pitcher else None,
    }


def format_game_row(game: dict) -> str:
    away = game["away"]
    home = game["home"]
    away_name = away["name"]
    home_name = home["name"]
    if away.get("score") is not None and home.get("score") is not None:
        matchup = f"{away_name} {away['score']} at {home_name} {home['score']}"
    else:
        matchup = f"{away_name} at {home_name}"

    details = [game["status"]]
    if game.get("start_time_tbd"):
        details.append("start TBD")

    away_pitcher = away.get("probable_pitcher_name")
    home_pitcher = home.get("probable_pitcher_name")
    if away_pitcher or home_pitcher:
        details.append(f"probables: {away_pitcher or 'TBD'} / {home_pitcher or 'TBD'}")

    return f"{game['game_id']}\t{game['game_date']}\t{matchup}\t({', '.join(details)})"


def game_matches_team(game: dict, team: str) -> bool:
    query = " ".join(team.lower().replace(".", "").split())
    team_id = TEAM_ALIASES.get(query)
    teams = game.get("teams", {})
    return any(team_side_matches(teams.get(side, {}).get("team", {}), query, team_id) for side in ("away", "home"))


def team_side_matches(team: dict, query: str, team_id: int | None) -> bool:
    if team_id is not None and team.get("id") == team_id:
        return True

    values = [
        team.get("abbreviation"),
        team.get("teamCode"),
        team.get("fileCode"),
        team.get("name"),
        team.get("teamName"),
        team.get("shortName"),
        team.get("clubName"),
        team.get("franchiseName"),
    ]
    names = {" ".join(str(value).lower().replace(".", "").split()) for value in values if value}
    return query in names or any(name.endswith(f" {query}") for name in names)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    target = parser.add_mutually_exclusive_group()
    target.add_argument("--game-pk", type=game_pk, help="Game ID from the schedule")
    target.add_argument("--list-games", action="store_true", help="Print game IDs and matchups for the selected date")
    parser.add_argument("--date", type=game_date, action="append", help="Schedule date (YYYY-MM-DD; default: today)")
    parser.add_argument("--team", type=team_identifier, help='Filter listed games by team, such as "SD" or "Padres"')
    parser.add_argument("--backend-url", default="http://127.0.0.1:8000", help="Local backend base URL")
    args = parser.parse_args(argv)

    if args.game_pk is not None and args.date is not None:
        parser.error("--date cannot be used with --game-pk")
    if args.game_pk is not None and args.team is not None:
        parser.error("--team cannot be used with --game-pk")
    if args.team is not None:
        args.list_games = True
    if not args.list_games and args.date is not None and len(args.date) > 1:
        parser.error("multiple --date values require --list-games or --team")

    selected_dates = args.date or [date.today()]
    if args.game_pk is not None:
        url = f"{args.backend_url.rstrip('/')}/raw/mlb-stats/games/{args.game_pk}"
    else:
        selected_date = selected_dates[0]
        query = urlencode({"date": selected_date.isoformat()})
        url = f"{args.backend_url.rstrip('/')}/raw/mlb-stats/schedule?{query}"

    if args.list_games:
        payloads = []
        for selected_date in selected_dates:
            query = urlencode({"date": selected_date.isoformat()})
            url = f"{args.backend_url.rstrip('/')}/raw/mlb-stats/schedule?{query}"
            payload = fetch_backend(url, args.backend_url)
            if payload is None:
                return 1
            payloads.append((selected_date, payload))
        try:
            sys.stdout.write(format_games_list(payloads, args.team))
        except (KeyError, TypeError, json.JSONDecodeError) as exc:
            print(f"Backend returned an unexpected schedule response: {exc}", file=sys.stderr)
            return 1
        return 0

    payload = fetch_backend(url, args.backend_url)
    if payload is None:
        return 1
    sys.stdout.buffer.write(payload)
    if payload and not payload.endswith(b"\n"):
        sys.stdout.buffer.write(b"\n")
    return 0


def fetch_backend(url: str, backend_url: str) -> bytes | None:
    request = Request(url, headers={"Accept": "application/json"})
    try:
        with urlopen(request, timeout=15) as response:
            return response.read()
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        print(f"Backend returned HTTP {exc.code}: {detail}", file=sys.stderr)
        return None
    except (URLError, TimeoutError, OSError) as exc:
        print(f"Could not reach backend at {backend_url}: {exc}", file=sys.stderr)
        return None


if __name__ == "__main__":
    raise SystemExit(main())
