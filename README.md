# MLB Matchup Analyzer

A baseball analytics application that loads live MLB schedules and formats game detail. The backend's fixture-backed Model layer turns pitch observations into pitcher and hitter profiles, a contact-quality matchup score, and uncalibrated plate-appearance outcome estimates. Fixture matchup and profile API responses are available; matchup views and calibrated outcome probabilities remain planned work.

The backend saves MLB schedule and game JSON in a local SQLite database and falls back to saved responses when MLB is unavailable. Statcast pitches can be imported locally from CSV or pybaseball; see `backend/STATCAST.md`.

## Repository layout

- `backend/`: FastAPI application, baseball domain models, and backend tests.
- `frontend/`: React and TypeScript user interface.
- `plan-doc.md`: ordered tickets, acceptance criteria, and release gates.
- `scripts/`: developer utilities, including the GitHub issue publisher.
- `cli/`: the `dug` command-line interface packaged as `dugout-mlb-data-analysis`.

The backend uses MVC-style boundaries: `backend/app/ingestion/` describes upstream MLB and Statcast formats, `backend/app/models/` holds normalized read and domain models, and `backend/app/services/` converts upstream data and runs game queries. FastAPI routes are thin HTTP Controllers; the React pages and `dug` format the results as Views. Baseball analytics and scoring live in `backend/app/analytics/` and `backend/app/matchup/`, independent of FastAPI and React. The scorer returns per-pitch explanations alongside its score and confidence.

## Local development

Requirements: Python 3.10+, [uv](https://docs.astral.sh/uv/), Node.js 20, and npm.

Start the backend in one terminal:

```sh
cd backend
uv sync --extra test
uv run uvicorn app.main:app --reload
```

The API runs at `http://127.0.0.1:8000`; `GET /health` reports its status. API docs are at `http://127.0.0.1:8000/docs`.

To inspect the unmodified MLB Stats API schedule JSON through the backend, leave the backend running and use a second terminal from the repository root:

```sh
python3 scripts/mlb-stats-raw.py --date 2026-07-01
```

Omit `--date` for today. Pass `--list-games --date 2026-07-01` to print game IDs and matchups for a date, or pass `--team SD --date 2026-07-01 --date 2026-07-02` to list games for one team across dates. Team filters accept MLB abbreviations, nicknames, and full names, such as `SD`, `Padres`, or `San Diego Padres`. Pass `--game-pk 123456` to fetch a particular game feed instead. The script calls the local backend and writes the JSON to stdout unless `--list-games` or `--team` is used. Use `--backend-url` if the backend runs on another host or port. It does not call MLB directly.

## Dug command-line package

For a local macOS install from the terminal:

```sh
make build-pkg
sudo installer -pkg ./dist/dugout-mlb-data-analysis-0.1.1.pkg -target /
dug --help
```

You can also open the `.pkg` in Finder for a graphical install. The package installs `/usr/local/bin/dug` and the Python modules under `/usr/local/lib/dugout-mlb-data-analysis`. It does not require Homebrew or publication. Python 3.10 or newer must be installed on the Mac; `dug` reports a clear error if it cannot find one. Rebuild the package after changing the CLI and reinstall it to update the command.

Build the Debian package from the repository root with `make build-deb`. This creates `dist/dugout-mlb-data-analysis_0.1.1_all.deb`. On Debian or Ubuntu with Python 3.10 or newer, install it with:

```sh
sudo apt install ./dist/dugout-mlb-data-analysis_0.1.1_all.deb
```

The package installs `/usr/bin/dug`. Start the backend separately, then run:

```sh
dug games list -d 2026-07-01 -d 2026-07-02 -t SD
dug games list -d 2026-07-01 -t Padres -f json
dug games show 123456
dug games show 123456 -v boxscore
dug games show 123456 -v plays -s
dug raw schedule -d 2026-07-01
dug raw game 123456
```

`-d`/`--date`, `-t`/`--team`, `-f`/`--format`, and `-u`/`--backend-url` are interchangeable short and long options. `games list` defaults to today, accepts repeated dates, and matches abbreviations, nicknames, or full team names. Its table includes status, scores, and probable starters. `games show` displays the parsed line score, batting and pitching tables, and play log; `-v`/`--view` selects `all`, `boxscore`, or `plays`, and `-s`/`--scoring-only` filters the play log. `-f json` returns the full parsed response. `-u` defaults to `http://127.0.0.1:8000` and goes after the subcommand. The `raw` commands return unmodified JSON; `games` commands use the backend's formatted API. For local use without installation, run `PYTHONPATH=cli python3 -m dugout` from the repository root.

Start the frontend in another terminal:

```sh
cd frontend
npm install
npm run dev
```

Vite prints the local URL and proxies `/api` requests to the backend. Set `VITE_API_BASE_URL` to change the backend target; see `frontend/README.md`. The Games page requests `GET /games?date=YYYY-MM-DD` and displays the schedule for the selected date. Selecting a game opens `/games/{gamePk}` with a formatted line score, box score, and play log. The `/mlb-stats/raw` pages retain the unmodified upstream JSON for inspection.

## Checks

```sh
cd backend
uv run --extra test pytest
```

```sh
cd frontend
npm run build
npm test
```

Tests cover domain validation, health and mocked MLB responses, plus deterministic fixture-backed parsing, profiles, regression, pitch selection, location, hitter response, and matchup scoring. Checks require no live MLB or Statcast calls.

## Delivery sequence

With the fixture Model layer and API responses in place, the next step is matchup UI views. Add live MLB/Statcast ingestion after the fixture path is deterministic. Outcome probability and read-only market comparison follow the calibration and provider gates in `plan-doc.md`.
