"""Convert MLB schedules into normalized game summaries."""

from datetime import date

from app.ingestion.mlb_schedule import MlbSchedule, MlbSide
from app.models.game_read import GamesResponse, GameSummary, GameTeam


def parse_schedule(raw: bytes, requested_date: date) -> GamesResponse:
    schedule = MlbSchedule.model_validate_json(raw)
    games = []
    for day in schedule.dates:
        if day.date != requested_date:
            continue
        for game in day.games:
            games.append(
                GameSummary(
                    game_id=game.game_id,
                    game_date=game.game_date,
                    status=game.status.detailed_state or game.status.abstract_game_state or "Unknown",
                    start_time_tbd=game.status.start_time_tbd,
                    away=_team_summary(game.teams.away),
                    home=_team_summary(game.teams.home),
                )
            )
    games.sort(key=lambda game: (game.game_date, game.game_id))
    return GamesResponse(date=requested_date, games=games)


def _team_summary(side: MlbSide) -> GameTeam:
    return GameTeam(
        team_id=side.team.id,
        name=side.team.name,
        score=side.score,
        probable_pitcher_name=side.probable_pitcher.full_name if side.probable_pitcher else None,
    )
