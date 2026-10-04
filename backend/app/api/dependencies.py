from fastapi import Depends

from app.clients.mlb_stats import MLBStatsClient
from app.services.games import GameService
from app.services.fixture_matchups import FixtureMatchupService


def get_mlb_stats_client() -> MLBStatsClient:
    return MLBStatsClient()


def get_game_service(client: MLBStatsClient = Depends(get_mlb_stats_client)) -> GameService:
    return GameService(client)


def get_fixture_matchup_service() -> FixtureMatchupService:
    return FixtureMatchupService()
