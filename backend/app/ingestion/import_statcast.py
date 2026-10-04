"""Command-line entry point for local Statcast imports."""

import argparse
from dataclasses import asdict
from datetime import date
import json
from pathlib import Path

from app.config import get_settings
from app.db.snapshots import upgrade_database
from app.db.statcast import StatcastRepository
from app.ingestion.statcast_source import CsvStatcastSource, PybaseballStatcastSource
from app.services.statcast_ingestion import StatcastImportError, StatcastIngestionService


def _date(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("date must use YYYY-MM-DD") from exc


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Import Statcast pitches into the local database")
    parser.add_argument("--start", required=True, type=_date)
    parser.add_argument("--end", required=True, type=_date)
    parser.add_argument("--csv", type=Path, help="Import from a local Statcast CSV instead of pybaseball")
    parser.add_argument("--refresh", action="store_true", help="Re-fetch completed dates")
    args = parser.parse_args(argv)
    if args.end < args.start:
        parser.error("--end must be on or after --start")

    database_url = get_settings().database_url
    upgrade_database(database_url)
    repository = StatcastRepository(database_url)
    source = CsvStatcastSource(args.csv) if args.csv else PybaseballStatcastSource()
    try:
        summary = StatcastIngestionService(source, repository).import_range(
            args.start, args.end, refresh=args.refresh,
        )
    except (StatcastImportError, OSError, RuntimeError) as exc:
        parser.exit(1, f"Statcast import failed: {exc}\n")
    print(json.dumps(asdict(summary), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
