type JsonRecord = Record<string, unknown>;

function record(value: unknown): JsonRecord {
  return typeof value === 'object' && value !== null && !Array.isArray(value) ? value as JsonRecord : {};
}

export type GamePlayer = {
  id: number;
  name: string;
  profile: JsonRecord;
  boxscore: JsonRecord | null;
};

export function gamePlayers(raw: string): GamePlayer[] {
  let feed: unknown;
  try {
    feed = JSON.parse(raw);
  } catch {
    return [];
  }

  const root = record(feed);
  const profiles = record(record(root.gameData).players);
  const teams = record(record(root.liveData).boxscore);
  const boxscoreTeams = record(teams.teams);
  const away = record(record(boxscoreTeams.away).players);
  const home = record(record(boxscoreTeams.home).players);

  return Object.entries(profiles).flatMap(([key, value]) => {
    const profile = record(value);
    const id = profile.id;
    if (typeof id !== 'number' || !Number.isInteger(id) || id <= 0) return [];
    const name = typeof profile.fullName === 'string' ? profile.fullName : `Player ${id}`;
    const boxscore = away[key] ?? home[key];
    return [{ id, name, profile, boxscore: boxscore === undefined ? null : record(boxscore) }];
  }).sort((a, b) => a.name.localeCompare(b.name));
}

export function playerPlays(raw: string, playerId: number): unknown[] {
  let feed: unknown;
  try {
    feed = JSON.parse(raw);
  } catch {
    return [];
  }
  const plays = record(record(record(feed).liveData).plays).allPlays;
  if (!Array.isArray(plays)) return [];

  return plays.filter((play: unknown) => {
    const data = record(play);
    const matchup = record(data.matchup);
    const batter = record(matchup.batter).id;
    const pitcher = record(matchup.pitcher).id;
    if (batter === playerId || pitcher === playerId) return true;
    const runners = data.runners;
    return Array.isArray(runners) && runners.some((runner: unknown) =>
      record(record(record(runner).details).runner).id === playerId);
  });
}
