"""Plain-text displays for the backend's parsed game responses."""


def value(item: object) -> str:
    return "-" if item is None else str(item)


def table(headers: tuple[str, ...], rows: list[tuple[object, ...]]) -> str:
    columns = [[header, *(value(row[index]) for row in rows)] for index, header in enumerate(headers)]
    widths = [max(len(cell) for cell in column) for column in columns]

    def line(cells: tuple[object, ...]) -> str:
        return "  ".join(value(cell).ljust(width) for cell, width in zip(cells, widths)).rstrip()

    return "\n".join([line(headers), line(tuple("-" * width for width in widths)), *(line(row) for row in rows)])


def schedule(games: list[dict]) -> str:
    if not games:
        return "No games found."
    rows = []
    for game in games:
        away, home = game["away"], game["home"]
        away_name = f"{away['name']} ({away['score']})" if away.get("score") is not None else away["name"]
        home_name = f"{home['name']} ({home['score']})" if home.get("score") is not None else home["name"]
        status = game["status"] + ("; time TBD" if game.get("start_time_tbd") else "")
        rows.append((game["game_id"], game["game_date"], away_name, home_name, status))
    lines = [table(("ID", "DATE/TIME", "AWAY", "HOME", "STATUS"), rows)]
    probable_games = [game for game in games if game["away"].get("probable_pitcher_name")
                      or game["home"].get("probable_pitcher_name")]
    if probable_games:
        lines.append("")
        for game in probable_games:
            away = game["away"].get("probable_pitcher_name") or "TBD"
            home = game["home"].get("probable_pitcher_name") or "TBD"
            lines.append(f"{game['game_id']} probable starters: {away} / {home}")
    return "\n".join(lines)


def boxscore(team: dict) -> str:
    lines = [team["name"], "Batting"]
    if team["batting"]:
        rows = [tuple(player.get(key) for key in
                      ("name", "position", "at_bats", "runs", "hits", "rbi", "walks", "strikeouts"))
                for player in team["batting"]]
        lines.append(table(("PLAYER", "POS", "AB", "R", "H", "RBI", "BB", "K"), rows))
    else:
        lines.append("No batting stats yet.")
    lines.append("Pitching")
    if team["pitching"]:
        rows = [tuple(player.get(key) for key in
                      ("name", "innings_pitched", "hits", "runs", "earned_runs", "walks", "strikeouts", "pitches"))
                for player in team["pitching"]]
        lines.append(table(("PLAYER", "IP", "H", "R", "ER", "BB", "K", "P"), rows))
    else:
        lines.append("No pitching stats yet.")
    return "\n".join(lines)


def plays(game: dict, scoring_only: bool = False) -> str:
    selected = [play for play in game["plays"] if not scoring_only or play["is_scoring_play"]]
    if not selected:
        return "No scoring plays available." if scoring_only else "No plays available."
    lines = []
    for play in reversed(selected):
        half = "Top" if play["half"] == "top" else "Bottom"
        label = f"{half} {play['inning']}"
        if play.get("event"):
            label += f" | {play['event']}"
        if play.get("away_score") is not None and play.get("home_score") is not None:
            away = game["away"].get("abbreviation") or "Away"
            home = game["home"].get("abbreviation") or "Home"
            label += f" | {away} {play['away_score']} - {home} {play['home_score']}"
        lines.append(f"{label}\n  {play['description']}")
    return "\n".join(lines)


def game_detail(game: dict, view: str = "all", scoring_only: bool = False) -> str:
    away, home = game["away"], game["home"]
    lines = [f"{away['name']} at {home['name']}",
             f"Game {game['game_id']} | {game['status']} | {game['game_date']} | {game.get('venue') or 'Venue TBD'}",
             ""]
    if game["innings"]:
        headers = ("TEAM", *(str(inning["number"]) for inning in game["innings"]), "R", "H", "E")
        rows = []
        for side, team in (("away", away), ("home", home)):
            rows.append((team.get("abbreviation") or team["name"],
                         *(inning[f"{side}_runs"] for inning in game["innings"]),
                         team["score"].get("runs"), team["score"].get("hits"), team["score"].get("errors")))
        lines.append(table(headers, rows))
    else:
        lines.append(f"{away['name']} {value(away['score'].get('runs'))} - "
                     f"{home['name']} {value(home['score'].get('runs'))}")
        lines.append("No line score yet.")

    if view in ("all", "boxscore"):
        lines.extend(("", boxscore(away), "", boxscore(home)))
    if view in ("all", "plays"):
        lines.extend(("", "Plays", plays(game, scoring_only)))
    return "\n".join(lines)
