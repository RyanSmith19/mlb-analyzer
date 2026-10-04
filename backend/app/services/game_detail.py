"""Convert MLB live feeds into normalized game details."""

from app.ingestion.mlb_game import MlbBoxTeam, MlbGameFeed, MlbScore, MlbTeam
from app.models.game_read import BattingLine, GameDetail, Inning, PitchingLine, PlaySummary, Score, TeamBox


def parse_game_detail(raw: bytes, game_pk: int) -> GameDetail:
    feed = MlbGameFeed.model_validate_json(raw)
    if feed.game_pk != game_pk:
        raise ValueError("MLB Stats API returned a different game")

    linescore = feed.live_data.linescore
    boxscore = feed.live_data.boxscore.teams
    return GameDetail(
        game_id=feed.game_pk,
        game_date=feed.game_data.datetime.date_time,
        status=feed.game_data.status.detailed_state,
        venue=feed.game_data.venue.name if feed.game_data.venue else None,
        away=_team_box(feed.game_data.teams.away, linescore.teams.away, boxscore.away),
        home=_team_box(feed.game_data.teams.home, linescore.teams.home, boxscore.home),
        innings=[Inning(number=inning.num, away_runs=inning.away.runs, home_runs=inning.home.runs) for inning in linescore.innings],
        plays=[
            PlaySummary(
                inning=play.about.inning,
                half=play.about.half_inning,
                event=play.result.event,
                description=play.result.description,
                is_scoring_play=play.about.is_scoring_play,
                away_score=play.result.away_score,
                home_score=play.result.home_score,
            )
            for play in feed.live_data.plays.all_plays
            if play.result.description
        ],
    )


def _team_box(team: MlbTeam, score: MlbScore, box: MlbBoxTeam) -> TeamBox:
    players = list(box.players.values())
    batting = sorted(
        (player for player in players if player.stats.batting.model_fields_set),
        key=lambda player: (player.batting_order or "999", player.person.full_name),
    )
    pitcher_order = {player_id: index for index, player_id in enumerate(box.pitchers)}
    pitching = sorted(
        (player for player in players if player.stats.pitching.model_fields_set),
        key=lambda player: (pitcher_order.get(player.person.id, len(pitcher_order)), player.person.full_name),
    )
    return TeamBox(
        team_id=team.id,
        name=team.name,
        abbreviation=team.abbreviation,
        score=Score(runs=score.runs, hits=score.hits, errors=score.errors),
        batting=[
            BattingLine(
                player_id=player.person.id,
                name=player.person.full_name,
                position=player.position.abbreviation if player.position else None,
                at_bats=player.stats.batting.at_bats,
                runs=player.stats.batting.runs,
                hits=player.stats.batting.hits,
                rbi=player.stats.batting.rbi,
                walks=player.stats.batting.base_on_balls,
                strikeouts=player.stats.batting.strike_outs,
            )
            for player in batting
        ],
        pitching=[
            PitchingLine(
                player_id=player.person.id,
                name=player.person.full_name,
                innings_pitched=player.stats.pitching.innings_pitched,
                hits=player.stats.pitching.hits,
                runs=player.stats.pitching.runs,
                earned_runs=player.stats.pitching.earned_runs,
                walks=player.stats.pitching.base_on_balls,
                strikeouts=player.stats.pitching.strike_outs,
                pitches=player.stats.pitching.number_of_pitches,
            )
            for player in pitching
        ],
    )
