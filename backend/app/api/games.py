"""HTTP controllers for normalized game data."""

from datetime import date

from fastapi import APIRouter, Depends, Path, Query, Response

from app.api.dependencies import get_game_service
from app.models.game_read import GameDetail, GamesResponse
from app.services.games import GameService


router = APIRouter(tags=["games"])


@router.get("/games", response_model=GamesResponse)
def games_for_date(
    response: Response,
    game_date: date = Query(alias="date"),
    service: GameService = Depends(get_game_service),
) -> GamesResponse:
    result = service.schedule_with_source(game_date)
    response.headers["X-Data-Source"] = result.source
    return result.value


@router.get("/games/{game_pk}", response_model=GameDetail)
def game_detail(
    response: Response,
    game_pk: int = Path(gt=0),
    service: GameService = Depends(get_game_service),
) -> GameDetail:
    result = service.detail_with_source(game_pk)
    response.headers["X-Data-Source"] = result.source
    return result.value
