export type ScheduleGame = { gamePk: number; label: string };

function record(value: unknown): Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value) ? value as Record<string, unknown> : {};
}

export function scheduleGames(raw: string): ScheduleGame[] {
  let schedule: unknown;
  try {
    schedule = JSON.parse(raw);
  } catch {
    return [];
  }
  if (typeof schedule !== 'object' || schedule === null || !('dates' in schedule) || !Array.isArray(schedule.dates)) return [];

  return schedule.dates.flatMap((day: unknown) => {
    if (typeof day !== 'object' || day === null || !('games' in day) || !Array.isArray(day.games)) return [];
    return day.games.flatMap((game: unknown) => {
      if (typeof game !== 'object' || game === null || !('gamePk' in game) || typeof game.gamePk !== 'number') return [];
      const gamePk = game.gamePk;
      if (!Number.isInteger(gamePk) || gamePk <= 0) return [];
      const teams = record(record(game).teams);
      const names = ['away', 'home'].map((side) => {
        const team = record(record(teams[side]).team);
        return typeof team.name === 'string' ? team.name : null;
      });
      return [{ gamePk, label: names.every(Boolean) ? `${names[0]} at ${names[1]}` : `Game ${gamePk}` }];
    });
  });
}
