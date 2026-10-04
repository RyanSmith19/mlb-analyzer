# Local Statcast imports

Run these commands from `backend/`. Imports use the SQLite database at `data/mlb_analyzer.sqlite3` by default. Set `MLB_DATABASE_URL` to choose another local SQLite file.

Import the packaged synthetic fixture without installing pybaseball:

```sh
uv run python -m app.ingestion.import_statcast --start 2026-07-01 --end 2026-07-02 --csv app/data/statcast_pitches.csv
```

For live Baseball Savant data, install the optional ingestion dependencies and choose a small date range:

```sh
uv sync --extra ingestion
uv run --extra ingestion python -m app.ingestion.import_statcast --start 2026-10-03 --end 2026-10-03
```

The importer requests one day at a time through pybaseball, normalizes each row into `PitchObservation`, and stores validated pitches in `statcast_pitches`. A pitch is identified by `(game_id, at_bat_number, pitch_number)`, so repeated imports do not duplicate it. `source_fields` retains the source row as text values for fields the current model does not understand yet.

When Baseball Savant reports estimated contact xwOBA without exit velocity, the normalized observation leaves xwOBA null because it cannot be validated as contact data. The source value remains in `source_fields` for inspection.

Each date has an `ingestion_runs` record with inserted, skipped, and failed counts. Completed dates are skipped on a rerun; failed and empty dates are retried. Use `--refresh` to request completed dates again, for example when Statcast later revises a game's data. A successful refresh transaction replaces that date's pitches, including removing pitches absent from the revised source; its inserted count is the number written, not the number newly discovered. Rows without a pitch type are skipped as non-modelable events. A day with other invalid rows is marked failed and will be retried after the source data or parser is corrected. Earlier successful days stay committed if a later date fails.

Inspect local state:

```sh
sqlite3 data/mlb_analyzer.sqlite3 'SELECT game_date, count(*) FROM statcast_pitches GROUP BY game_date ORDER BY game_date;'
sqlite3 data/mlb_analyzer.sqlite3 'SELECT start_date, status, inserted_count, skipped_count, failed_count FROM ingestion_runs ORDER BY id DESC LIMIT 20;'
```

Pitch records are stored locally but are not yet served through an API or used by the fixture-backed matchup endpoints. MLB schedule/game responses are stored separately in `mlb_payloads`; the normal game routes use those saved responses when MLB is unreachable and mark them with `X-Data-Source: stored`.
