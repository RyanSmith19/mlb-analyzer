from fastapi import Depends

from app.clients.mlb_stats import MLBStatsClient
from app.services.games import GameService


def get_mlb_stats_client() -> MLBStatsClient:
    return MLBStatsClient()


def get_game_service(client: MLBStatsClient = Depends(get_mlb_stats_client)) -> GameService:
    return GameService(client)
