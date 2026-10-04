"""HTTP controllers for unmodified MLB Stats payloads."""

from datetime import date

from fastapi import APIRouter, Depends, Path, Query, Response

from app.api.dependencies import get_game_service
from app.services.games import GameService


router = APIRouter(prefix="/raw/mlb-stats", tags=["raw MLB Stats"])


@router.get("/schedule", response_class=Response)
def raw_schedule(
    game_date: date = Query(alias="date"),
    service: GameService = Depends(get_game_service),
) -> Response:
    result = service.raw_schedule_with_source(game_date)
    return Response(content=result.value, media_type="application/json", headers={"X-Data-Source": result.source})


@router.get("/games/{game_pk}", response_class=Response)
def raw_game(
    game_pk: int = Path(gt=0),
    service: GameService = Depends(get_game_service),
) -> Response:
    result = service.raw_game_with_source(game_pk)
    return Response(content=result.value, media_type="application/json", headers={"X-Data-Source": result.source})
