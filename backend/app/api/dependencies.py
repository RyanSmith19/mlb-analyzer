from fastapi import Depends

from app.clients.mlb_stats import MLBStatsClient
from app.db.snapshots import MlbSnapshotRepository, get_snapshot_repository
from app.services.games import GameService
from app.services.fixture_matchups import FixtureMatchupService


def get_mlb_stats_client() -> MLBStatsClient:
    return MLBStatsClient()


def get_game_service(
    client: MLBStatsClient = Depends(get_mlb_stats_client),
    snapshots: MlbSnapshotRepository = Depends(get_snapshot_repository),
) -> GameService:
    return GameService(client, snapshots)


def get_fixture_matchup_service() -> FixtureMatchupService:
    return FixtureMatchupService()
