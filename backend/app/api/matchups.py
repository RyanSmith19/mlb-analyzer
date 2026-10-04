"""Fixture-backed matchup and profile controllers."""

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Path, Query

from app.api.dependencies import get_fixture_matchup_service
from app.models.domain import BatterSide
from app.models.matchup_read import (
    FixtureGameSummary, GameMatchupsRead, HitterProfileRead, MatchupRead,
    PitcherProfileRead, PlayerSummary,
)
from app.services.fixture_matchups import FixtureMatchup, FixtureMatchupService


router = APIRouter(tags=["fixture matchups"])


def _read_matchup(service_matchup: FixtureMatchup) -> MatchupRead:
    return MatchupRead.from_domain(
        service_matchup.pitcher_profile,
        service_matchup.hitter_profile,
        service_matchup.result,
    )


@router.get("/matchups/{pitcher_id}/{hitter_id}", response_model=MatchupRead)
def fixture_matchup(
    pitcher_id: int = Path(gt=0), hitter_id: int = Path(gt=0),
    service: FixtureMatchupService = Depends(get_fixture_matchup_service),
) -> MatchupRead:
    matchup = service.matchup(pitcher_id, hitter_id)
    if matchup is None:
        raise HTTPException(status_code=404, detail="Fixture pitcher or hitter not found")
    return _read_matchup(matchup)


@router.get("/games/{game_id}/matchups", response_model=GameMatchupsRead)
def fixture_game_matchups(
    game_id: int = Path(gt=0),
    service: FixtureMatchupService = Depends(get_fixture_matchup_service),
) -> GameMatchupsRead:
    game = service.game_matchups(game_id)
    if game is None:
        raise HTTPException(status_code=404, detail="Fixture game not found")
    return GameMatchupsRead(
        game=FixtureGameSummary.from_game(game.game),
        pitcher=PlayerSummary.from_player(game.pitcher),
        matchups=tuple(_read_matchup(matchup) for matchup in game.matchups),
    )


@router.get("/pitchers/{pitcher_id}/profile", response_model=PitcherProfileRead)
def fixture_pitcher_profile(
    pitcher_id: int = Path(gt=0),
    batter_side: Literal["L", "R"] | None = Query(default=None),
    service: FixtureMatchupService = Depends(get_fixture_matchup_service),
) -> PitcherProfileRead:
    profile = service.pitcher_profile(pitcher_id, BatterSide(batter_side) if batter_side else None)
    if profile is None:
        raise HTTPException(status_code=404, detail="Fixture pitcher not found")
    return PitcherProfileRead.from_profile(profile)


@router.get("/hitters/{hitter_id}/profile", response_model=HitterProfileRead)
def fixture_hitter_profile(
    hitter_id: int = Path(gt=0),
    service: FixtureMatchupService = Depends(get_fixture_matchup_service),
) -> HitterProfileRead:
    profile = service.hitter_profile(hitter_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="Fixture hitter not found")
    return HitterProfileRead.from_profile(profile)
