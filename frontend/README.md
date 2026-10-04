# MLB Matchup Analyzer frontend

React + TypeScript application for the MLB Matchup Analyzer. The Games page shows the schedule, scores, and probable starters returned by `GET /api/games?date=YYYY-MM-DD`. Each game opens `/games/{gamePk}` with its line score, player box scores, and play log. `/mlb-stats/raw` shows the complete raw schedule response; `/mlb-stats/raw/games/{gamePk}` shows the full feed and individual player records.

## Requirements

- Node.js 20.17.0 or another Node 20 release compatible with Vite 6
- npm

## Local development

```sh
cd frontend
npm ci
cp .env.example .env.local
npm run dev
```

Open the URL printed by Vite. Both `/?date=2026-07-01` and `/mlb-stats/raw?date=2026-07-01` open a selected date; navigation between them preserves it. Vite proxies `/api` to `http://127.0.0.1:8000` by default. Set `VITE_API_BASE_URL` in `.env.local` to change the proxy target, then restart Vite. Production hosting must route `/api` to the backend as well.

## Build

```sh
npm run typecheck
npm run build
npm test
```

`npm run preview` serves the production build locally.
