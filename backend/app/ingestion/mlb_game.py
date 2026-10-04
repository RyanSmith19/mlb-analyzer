"""MLB Stats API live game-feed payload shape."""

from datetime import datetime

from pydantic import BaseModel, Field


class MlbTeam(BaseModel):
    id: int
    name: str
    abbreviation: str | None = None


class MlbTeams(BaseModel):
    away: MlbTeam
    home: MlbTeam


class MlbStatus(BaseModel):
    detailed_state: str = Field(alias="detailedState")


class MlbDateTime(BaseModel):
    date_time: datetime = Field(alias="dateTime")


class MlbVenue(BaseModel):
    name: str


class MlbGameData(BaseModel):
    datetime: MlbDateTime
    status: MlbStatus
    teams: MlbTeams
    venue: MlbVenue | None = None


class MlbScore(BaseModel):
    runs: int | None = None
    hits: int | None = None
    errors: int | None = None


class MlbInning(BaseModel):
    num: int
    away: MlbScore = Field(default_factory=MlbScore)
    home: MlbScore = Field(default_factory=MlbScore)


class MlbLineTeams(BaseModel):
    away: MlbScore = Field(default_factory=MlbScore)
    home: MlbScore = Field(default_factory=MlbScore)


class MlbLinescore(BaseModel):
    innings: list[MlbInning] = Field(default_factory=list)
    teams: MlbLineTeams = Field(default_factory=MlbLineTeams)


class MlbPerson(BaseModel):
    id: int
    full_name: str = Field(alias="fullName")


class MlbPosition(BaseModel):
    abbreviation: str | None = None


class MlbBattingStats(BaseModel):
    at_bats: int | None = Field(default=None, alias="atBats")
    runs: int | None = None
    hits: int | None = None
    rbi: int | None = None
    base_on_balls: int | None = Field(default=None, alias="baseOnBalls")
    strike_outs: int | None = Field(default=None, alias="strikeOuts")


class MlbPitchingStats(BaseModel):
    innings_pitched: str | None = Field(default=None, alias="inningsPitched")
    hits: int | None = None
    runs: int | None = None
    earned_runs: int | None = Field(default=None, alias="earnedRuns")
    base_on_balls: int | None = Field(default=None, alias="baseOnBalls")
    strike_outs: int | None = Field(default=None, alias="strikeOuts")
    number_of_pitches: int | None = Field(default=None, alias="numberOfPitches")


class MlbPlayerStats(BaseModel):
    batting: MlbBattingStats = Field(default_factory=MlbBattingStats)
    pitching: MlbPitchingStats = Field(default_factory=MlbPitchingStats)


class MlbBoxPlayer(BaseModel):
    person: MlbPerson
    position: MlbPosition | None = None
    batting_order: str | None = Field(default=None, alias="battingOrder")
    stats: MlbPlayerStats = Field(default_factory=MlbPlayerStats)


class MlbBoxTeam(BaseModel):
    players: dict[str, MlbBoxPlayer] = Field(default_factory=dict)
    pitchers: list[int] = Field(default_factory=list)


class MlbBoxTeams(BaseModel):
    away: MlbBoxTeam = Field(default_factory=MlbBoxTeam)
    home: MlbBoxTeam = Field(default_factory=MlbBoxTeam)


class MlbBoxscore(BaseModel):
    teams: MlbBoxTeams = Field(default_factory=MlbBoxTeams)


class MlbPlayResult(BaseModel):
    event: str | None = None
    description: str | None = None
    away_score: int | None = Field(default=None, alias="awayScore")
    home_score: int | None = Field(default=None, alias="homeScore")


class MlbPlayAbout(BaseModel):
    inning: int
    half_inning: str = Field(alias="halfInning")
    is_scoring_play: bool = Field(default=False, alias="isScoringPlay")


class MlbPlay(BaseModel):
    about: MlbPlayAbout
    result: MlbPlayResult


class MlbPlays(BaseModel):
    all_plays: list[MlbPlay] = Field(default_factory=list, alias="allPlays")


class MlbLiveData(BaseModel):
    linescore: MlbLinescore = Field(default_factory=MlbLinescore)
    boxscore: MlbBoxscore = Field(default_factory=MlbBoxscore)
    plays: MlbPlays = Field(default_factory=MlbPlays)


class MlbGameFeed(BaseModel):
    game_pk: int = Field(alias="gamePk")
    game_data: MlbGameData = Field(alias="gameData")
    live_data: MlbLiveData = Field(default_factory=MlbLiveData, alias="liveData")
