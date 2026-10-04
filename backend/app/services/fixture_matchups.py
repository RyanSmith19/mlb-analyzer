"""Synthetic matchup source for the first API vertical slice."""

from dataclasses import dataclass
from datetime import date
from pathlib import Path

from app.analytics.profiles import build_hitter_profile, build_pitcher_profile
from app.ingestion.statcast import PitchObservation, load_statcast_csv
from app.matchup.model import MatchupModel, WeightedMatchupModel
from app.models.domain import (
    BatterSide, Game, GameStatus, Hitter, HitterProfile, MatchupResult,
    Pitcher, PitcherProfile, Team,
)


FIXTURE_PATH = Path(__file__).resolve().parents[1] / "data" / "statcast_pitches.csv"
PITCHERS = {
    900101: Pitcher(player_id=900101, full_name="Pitcher A", team_id=900001, throws="R"),
    900102: Pitcher(player_id=900102, full_name="Pitcher B", team_id=900003, throws="L"),
}
HITTERS = {
    900201: Hitter(player_id=900201, full_name="Hitter A", team_id=900002, bats="R"),
    900202: Hitter(player_id=900202, full_name="Hitter B", team_id=900002, bats="L"),
}
GAMES = {
    9900001: Game(
        game_id=9900001, game_date=date(2026, 7, 1),
        away_team=Team(team_id=900002, name="Fixture Visitors", abbreviation="VIS"),
        home_team=Team(team_id=900001, name="Fixture Hosts", abbreviation="HST"),
        status=GameStatus.FINAL, home_probable_pitcher_id=900101,
    ),
    9900002: Game(
        game_id=9900002, game_date=date(2026, 7, 2),
        away_team=Team(team_id=900002, name="Fixture Visitors", abbreviation="VIS"),
        home_team=Team(team_id=900003, name="Fixture Southpaws", abbreviation="STH"),
        status=GameStatus.FINAL, home_probable_pitcher_id=900102,
    ),
}


@dataclass(frozen=True)
class FixtureMatchup:
    pitcher_profile: PitcherProfile
    hitter_profile: HitterProfile
    result: MatchupResult


@dataclass(frozen=True)
class FixtureGameMatchups:
    game: Game
    pitcher: Pitcher
    matchups: tuple[FixtureMatchup, ...]


class FixtureMatchupService:
    def __init__(
        self, rows: tuple[PitchObservation, ...] | None = None,
        model: MatchupModel | None = None,
    ) -> None:
        self.rows = rows if rows is not None else load_statcast_csv(FIXTURE_PATH)
        self.model = model if model is not None else WeightedMatchupModel()

    def pitcher_profile(self, pitcher_id: int, batter_side: BatterSide | None = None) -> PitcherProfile | None:
        pitcher = PITCHERS.get(pitcher_id)
        return build_pitcher_profile(pitcher, self.rows, batter_side) if pitcher else None

    def hitter_profile(self, hitter_id: int) -> HitterProfile | None:
        hitter = HITTERS.get(hitter_id)
        return build_hitter_profile(hitter, self.rows) if hitter else None

    def matchup(self, pitcher_id: int, hitter_id: int) -> FixtureMatchup | None:
        hitter = HITTERS.get(hitter_id)
        if hitter is None or hitter.bats == BatterSide.SWITCH:
            return None
        pitcher_profile = self.pitcher_profile(pitcher_id, hitter.bats)
        if pitcher_profile is None:
            return None
        hitter_profile = self.hitter_profile(hitter_id)
        if hitter_profile is None:
            return None
        return FixtureMatchup(
            pitcher_profile=pitcher_profile,
            hitter_profile=hitter_profile,
            result=self.model.calculate(pitcher_profile, hitter_profile),
        )

    def game_matchups(self, game_id: int) -> FixtureGameMatchups | None:
        game = GAMES.get(game_id)
        if game is None:
            return None
        game_rows = [row for row in self.rows if row.game_id == game_id]
        if not game_rows:
            return None
        pitcher_id = game.home_probable_pitcher_id
        pitcher = PITCHERS.get(pitcher_id) if pitcher_id is not None else None
        if pitcher is None:
            return None
        hitter_ids = sorted({
            row.hitter_id for row in game_rows
            if row.pitcher_id == pitcher.player_id
            and row.hitter_id in HITTERS
            and HITTERS[row.hitter_id].team_id == game.away_team.team_id
        })
        matchups = tuple(
            matchup for hitter_id in hitter_ids
            if (matchup := self.matchup(pitcher.player_id, hitter_id)) is not None
        )
        return FixtureGameMatchups(
            game=game,
            pitcher=pitcher,
            matchups=tuple(sorted(matchups, key=lambda item: (-item.result.score, item.result.hitter_id))),
        )
