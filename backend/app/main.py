from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.api.games import router as games_router
from app.api.health import router as health_router
from app.api.matchups import router as matchups_router
from app.api.mlb_stats_raw import router as mlb_stats_raw_router
from app.clients.mlb_stats import MLBStatsError
from app.config import get_settings
from app.services.games import InvalidMlbResponse


def upstream_error_response(_request: Request, exc: MLBStatsError | InvalidMlbResponse) -> JSONResponse:
    return JSONResponse(status_code=502, content={"detail": str(exc)})


def create_app() -> FastAPI:
    application = FastAPI(title=get_settings().app_name)
    application.include_router(games_router)
    application.include_router(health_router)
    application.include_router(matchups_router)
    application.include_router(mlb_stats_raw_router)
    application.add_exception_handler(MLBStatsError, upstream_error_response)
    application.add_exception_handler(InvalidMlbResponse, upstream_error_response)
    return application


app = create_app()
