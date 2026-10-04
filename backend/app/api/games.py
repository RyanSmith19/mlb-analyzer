"""HTTP controllers for normalized game data."""

from datetime import date

from fastapi import APIRouter, Depends, Path, Query

from app.api.dependencies import get_game_service
from app.models.game_read import GameDetail, GamesResponse
from app.services.games import GameService


router = APIRouter(tags=["games"])


@router.get("/games", response_model=GamesResponse)
def games_for_date(
    game_date: date = Query(alias="date"),
    service: GameService = Depends(get_game_service),
) -> GamesResponse:
    return service.schedule(game_date)


@router.get("/games/{game_pk}", response_model=GameDetail)
def game_detail(
    game_pk: int = Path(gt=0),
    service: GameService = Depends(get_game_service),
) -> GameDetail:
    return service.detail(game_pk)
