# MLB Analyzer Backend

Requires Python 3.10 or newer and `uv`.

From `backend/`:

```sh
uv sync --extra test
uv run uvicorn app.main:app --reload
```

`uv sync` creates the project-local `.venv` and installs versions from `uv.lock`. `uv run` uses that environment without activation. For an interactive shell, run `source .venv/bin/activate`.

The backend now uses a local SQLite database at `backend/data/mlb_analyzer.sqlite3` by default (ignored by Git). Set `MLB_DATABASE_URL` to use another SQLite URL or a PostgreSQL URL with a driver installed. Schema migrations run automatically on the first game request; they can also be run explicitly from `backend/` with `uv run alembic upgrade head`. The initial schema includes MLB players, teams, games, appearances, Statcast pitches, profile snapshots, ingestion runs, and a table for the exact raw MLB responses. Only the raw-response table is populated automatically so far; Statcast ingestion and profile persistence remain separate upcoming work.

Successful schedule and game requests, whether made through a raw or formatted route, refresh the corresponding local raw-response snapshot. Responses still fetch live data; the database is not yet an offline fallback or a historical archive. To inspect saved responses: `sqlite3 data/mlb_analyzer.sqlite3 'SELECT kind, resource_key, length(payload), fetched_at FROM mlb_payloads;'`.

Add a runtime dependency with `uv add package-name`, or a test-only dependency with `uv add --optional test package-name`. Run `uv sync --extra test` after pulling dependency changes.

The app is available at `http://127.0.0.1:8000`. `GET /health` returns `{"status":"ok"}`.

`GET /raw/mlb-stats/schedule?date=YYYY-MM-DD` fetches the MLB schedule for that date and returns the upstream JSON bytes unchanged. Upstream failures return HTTP 502. The repository script `scripts/mlb-stats-raw.py` prints this response from the backend.

`GET /raw/mlb-stats/games/{gamePk}` fetches the complete MLB live game feed for a game ID from the schedule, including `gameData.players` and live box-score player data when available. It returns the upstream JSON bytes unchanged. Run `python3 scripts/mlb-stats-raw.py --game-pk 123456` from the repository root to print it.

`GET /games?date=YYYY-MM-DD` extracts game IDs, start times, status, teams, scores, and probable pitcher names when present. A valid date with no games returns an empty `games` list. An invalid or unexpected upstream response returns HTTP 502.

`GET /games/{gamePk}` returns a formatted game detail with team totals, inning lines, batting and pitching box scores, and play summaries. Missing pregame stats produce empty lists and null scores.

The backend keeps HTTP handling in `app.api`, MLB payload schemas in `app.ingestion.mlb_schedule` and `app.ingestion.mlb_game`, normalized response contracts in `app.models.game_read`, and conversion in `app.services.schedule` and `app.services.game_detail`. `app.services.games.GameService` fetches data through a small source interface and serves both parsed and raw routes. Route exceptions are mapped to HTTP 502 in `app.main`; the service and parsers have no FastAPI dependency.

Run the test suite with:

```sh
uv run --extra test pytest
```

The packaged synthetic pitch-level Statcast fixture is `app/data/statcast_pitches.csv`; hand-checkable aggregate expectations are documented in `tests/fixtures/README.md`. The CSV is deliberately small and contains sampled appearances from two invented games.

The MVC Model layer includes a Statcast CSV adapter (`app.ingestion.statcast`), typed pitch observations, pure pitcher/hitter profile generators (`app.analytics.profiles`), configurable sample-size regression (`app.analytics.regression`), and a replaceable weighted matchup scorer (`app.matchup.model`). Fixture-backed matchup and profile Controllers now expose these results; the React matchup View is not wired yet. Domain models live in `app.models.domain` and have no API or persistence dependency. Usage and confidence values are fractions from 0 to 1; matchup scores range from 0 to 100. Each metric carries its own sample size. Environment variables use the `MLB_` prefix; for example, `MLB_APP_NAME` changes the OpenAPI title.

Fixture-backed endpoints use synthetic player IDs `900101`/`900102` (pitchers), `900201`/`900202` (hitters), and game IDs `9900001`/`9900002`:

```text
GET /matchups/900101/900202
GET /games/9900001/matchups
GET /pitchers/900101/profile?batter_side=L
GET /hitters/900202/profile
```

The single-matchup response includes a score band, confidence, per-pitch metrics and sample sizes, and the strongest directional explanation. The game response ranks its fixture hitters by score. Every response identifies `synthetic_fixture`; scores are contact-quality indices with `calibrated=false`, not outcome probabilities.

For fixture-backed experimentation, call `load_statcast_csv(path)`, then `build_pitcher_profile(pitcher, rows, batter_side=...)` and `build_hitter_profile(hitter, rows)`, then `WeightedMatchupModel().calculate(pitcher_profile, hitter_profile)`. The scorer's neutral xwOBA prior (`0.320`, `K=25`) is illustrative, not a measured current league baseline. The resulting score is a **contact-quality** opportunity index, not a hit probability, strikeout-aware projection, or betting edge; the tiny fixture should produce very low confidence. Profile xwOBA uses only rows with estimated contact xwOBA, hard-hit rate uses batted balls with known exit velocity, whiff rate uses swings, and strikeout rate uses completed appearances ending on that pitch type. Movement is converted from Statcast feet to inches. wOBA requires both `woba_value` and `woba_denom`; barrel rate requires Statcast's `launch_speed_angle` classification. Where the fixture lacks these fields, the corresponding raw metric and sample size remain unavailable/zero. A switch hitter's actual batting side must be chosen by the caller when building a pitcher split.

The next Model layer supports count-aware pitch selection (`app.analytics.selection`), zone-based location weighting (`app.analytics.location`), hitter response (`app.analytics.response`), conditional contact results (`app.analytics.contact`), and a compositional plate-appearance estimate (`app.matchup.outcomes`). Pass historical `PitchObservation` rows and typed players to `PlateAppearanceModel().estimate(rows, pitcher, hitter, before_date=game_date)`. `before_date` excludes the target date and later rows. The returned strikeout, walk, non-home-run hit, home run, out, hit-by-pitch, and unresolved shares sum to one; `hit_probability()` combines the two hit outcomes. `calibrated=False` is intentional: no held-out historical evaluation or league-rate prior exists yet. Missing data returns `status="unavailable"`, and `confidence` currently measures only handedness-matched pitch-count sufficiency. This model must not be presented as a validated game prediction or betting edge.

The parser accepts optional pre-pitch `balls`/`strikes`, `plate_x`, and `plate_z`. The small fixture lacks those continuous coordinates, so location currently uses Statcast `zone` with backoff. K-means or another coordinate-clustering method should be compared against this zone baseline only with a larger historical training set and held-out evaluation; see `MLB-65`.
