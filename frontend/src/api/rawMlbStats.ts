import { apiBaseUrl } from '../config';

export async function getRawMlbSchedule(date: string, signal: AbortSignal): Promise<string> {
  const query = new URLSearchParams({ date });
  const response = await fetch(`${apiBaseUrl}/raw/mlb-stats/schedule?${query}`, {
    headers: { Accept: 'application/json' },
    signal,
  });

  if (!response.ok) {
    let detail = `Schedule request failed (HTTP ${response.status}).`;
    if (response.headers.get('content-type')?.includes('application/json')) {
      const body: unknown = await response.json();
      if (typeof body === 'object' && body !== null && 'detail' in body && typeof body.detail === 'string') {
        detail = body.detail;
      }
    }
    throw new Error(detail);
  }

  return response.text();
}

export async function getRawMlbGame(gamePk: number, signal: AbortSignal): Promise<string> {
  const response = await fetch(`${apiBaseUrl}/raw/mlb-stats/games/${gamePk}`, {
    headers: { Accept: 'application/json' },
    signal,
  });

  if (!response.ok) {
    let detail = `Game feed request failed (HTTP ${response.status}).`;
    if (response.headers.get('content-type')?.includes('application/json')) {
      const body: unknown = await response.json();
      if (typeof body === 'object' && body !== null && 'detail' in body && typeof body.detail === 'string') {
        detail = body.detail;
      }
    }
    throw new Error(detail);
  }

  return response.text();
}

export function formatRawJson(raw: string): string {
  try {
    return JSON.stringify(JSON.parse(raw), null, 2);
  } catch {
    return raw;
  }
}
