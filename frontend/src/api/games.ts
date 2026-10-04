import { apiBaseUrl } from '../config';

export type GameTeam = {
  team_id: number;
  name: string;
  score: number | null;
  probable_pitcher_name: string | null;
};

export type Game = {
  game_id: number;
  game_date: string;
  status: string;
  start_time_tbd: boolean;
  away: GameTeam;
  home: GameTeam;
};

export type GamesResponse = {
  date: string;
  games: Game[];
};

export type Score = { runs: number | null; hits: number | null; errors: number | null };

export type BattingLine = {
  player_id: number;
  name: string;
  position: string | null;
  at_bats: number | null;
  runs: number | null;
  hits: number | null;
  rbi: number | null;
  walks: number | null;
  strikeouts: number | null;
};

export type PitchingLine = {
  player_id: number;
  name: string;
  innings_pitched: string | null;
  hits: number | null;
  runs: number | null;
  earned_runs: number | null;
  walks: number | null;
  strikeouts: number | null;
  pitches: number | null;
};

export type TeamBox = {
  team_id: number;
  name: string;
  abbreviation: string | null;
  score: Score;
  batting: BattingLine[];
  pitching: PitchingLine[];
};

export type GameDetail = {
  game_id: number;
  game_date: string;
  status: string;
  venue: string | null;
  away: TeamBox;
  home: TeamBox;
  innings: { number: number; away_runs: number | null; home_runs: number | null }[];
  plays: {
    inning: number;
    half: string;
    event: string | null;
    description: string;
    is_scoring_play: boolean;
    away_score: number | null;
    home_score: number | null;
  }[];
};

export async function getGames(date: string, signal: AbortSignal): Promise<GamesResponse> {
  const query = new URLSearchParams({ date });
  const response = await fetch(`${apiBaseUrl}/games?${query}`, {
    headers: { Accept: 'application/json' },
    signal,
  });

  if (!response.ok) {
    let detail = `Games request failed (HTTP ${response.status}).`;
    if (response.headers.get('content-type')?.includes('application/json')) {
      const body: unknown = await response.json();
      if (typeof body === 'object' && body !== null && 'detail' in body && typeof body.detail === 'string') {
        detail = body.detail;
      }
    }
    throw new Error(detail);
  }

  const body: unknown = await response.json();
  if (typeof body !== 'object' || body === null || !('games' in body) || !Array.isArray(body.games)) {
    throw new Error('Games response was invalid.');
  }
  return body as GamesResponse;
}

export async function getGameDetail(gamePk: number, signal: AbortSignal): Promise<GameDetail> {
  const response = await fetch(`${apiBaseUrl}/games/${gamePk}`, {
    headers: { Accept: 'application/json' },
    signal,
  });
  if (!response.ok) {
    let detail = `Game request failed (HTTP ${response.status}).`;
    if (response.headers.get('content-type')?.includes('application/json')) {
      const body: unknown = await response.json();
      if (typeof body === 'object' && body !== null && 'detail' in body && typeof body.detail === 'string') {
        detail = body.detail;
      }
    }
    throw new Error(detail);
  }

  const body: unknown = await response.json();
  if (typeof body !== 'object' || body === null || !('game_id' in body) || body.game_id !== gamePk
      || !('away' in body) || !('home' in body) || !('innings' in body) || !Array.isArray(body.innings)
      || !('plays' in body) || !Array.isArray(body.plays)) {
    throw new Error('Game response was invalid.');
  }
  return body as GameDetail;
}
