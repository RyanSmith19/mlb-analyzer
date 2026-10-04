"""Stable MLB team identifiers accepted by the CLI."""

TEAMS = (
    (109, "ARI", "Arizona Diamondbacks", "Diamondbacks"),
    (144, "ATL", "Atlanta Braves", "Braves"),
    (110, "BAL", "Baltimore Orioles", "Orioles"),
    (111, "BOS", "Boston Red Sox", "Red Sox"),
    (112, "CHC", "Chicago Cubs", "Cubs"),
    (145, "CWS", "Chicago White Sox", "White Sox"),
    (113, "CIN", "Cincinnati Reds", "Reds"),
    (114, "CLE", "Cleveland Guardians", "Guardians"),
    (115, "COL", "Colorado Rockies", "Rockies"),
    (116, "DET", "Detroit Tigers", "Tigers"),
    (117, "HOU", "Houston Astros", "Astros"),
    (118, "KC", "Kansas City Royals", "Royals"),
    (108, "LAA", "Los Angeles Angels", "Angels"),
    (119, "LAD", "Los Angeles Dodgers", "Dodgers"),
    (146, "MIA", "Miami Marlins", "Marlins"),
    (158, "MIL", "Milwaukee Brewers", "Brewers"),
    (142, "MIN", "Minnesota Twins", "Twins"),
    (121, "NYM", "New York Mets", "Mets"),
    (147, "NYY", "New York Yankees", "Yankees"),
    (133, "ATH", "Athletics", "Athletics"),
    (143, "PHI", "Philadelphia Phillies", "Phillies"),
    (134, "PIT", "Pittsburgh Pirates", "Pirates"),
    (135, "SD", "San Diego Padres", "Padres"),
    (136, "SEA", "Seattle Mariners", "Mariners"),
    (137, "SF", "San Francisco Giants", "Giants"),
    (138, "STL", "St. Louis Cardinals", "Cardinals"),
    (139, "TB", "Tampa Bay Rays", "Rays"),
    (140, "TEX", "Texas Rangers", "Rangers"),
    (141, "TOR", "Toronto Blue Jays", "Blue Jays"),
    (120, "WSH", "Washington Nationals", "Nationals"),
)

EXTRA_ALIASES = {
    "SDP": 135, "SFG": 137, "TBR": 139, "KCR": 118, "WAS": 120,
    "CHW": 145, "OAK": 133, "A'S": 133, "LA DODGERS": 119,
    "ST LOUIS CARDINALS": 138, "ST. LOUIS CARDINALS": 138,
}


def _normalize(value: str) -> str:
    return " ".join(value.strip().casefold().replace(".", "").split())


ALIASES = {
    _normalize(alias): team_id
    for team_id, abbreviation, name, nickname in TEAMS
    for alias in (str(team_id), abbreviation, name, nickname)
}
ALIASES.update({_normalize(alias): team_id for alias, team_id in EXTRA_ALIASES.items()})


def team_id(value: str) -> int:
    try:
        return ALIASES[_normalize(value)]
    except KeyError as exc:
        raise ValueError(f"Unknown MLB team: {value}") from exc
