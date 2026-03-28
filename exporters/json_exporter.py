#!/usr/bin/env python3
"""
Meridian VC Intelligence Platform — JSON Exporter

Exports all core tables from Supabase to JSON files for dashboard static fallback.
Writes individual table files plus a combined data.json.

Usage:
    python exporters/json_exporter.py
    python exporters/json_exporter.py --output-dir dashboard/public/data
    python exporters/json_exporter.py --output-dir /tmp/meridian-export
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from supabase import create_client, Client

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------

DEFAULT_OUTPUT_DIR = Path(__file__).resolve().parent.parent / "dashboard" / "public" / "data"

# Tables to export (in dependency order)
TABLES: list[str] = [
    "vc_firms",
    "portfolio_companies",
    "founders",
    "investments",
]

# Output file names, keyed by table
OUTPUT_FILENAMES: dict[str, str] = {
    "vc_firms": "vc_firms.json",
    "portfolio_companies": "companies.json",
    "founders": "founders.json",
    "investments": "investments.json",
}


# ---------------------------------------------------------------------------
# JSON serialisation helpers
# ---------------------------------------------------------------------------


class _DatetimeEncoder(json.JSONEncoder):
    """Encode datetime / date objects to ISO strings for JSON serialisation."""

    def default(self, obj: Any) -> Any:
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        return super().default(obj)


def _dump(data: Any) -> str:
    return json.dumps(data, cls=_DatetimeEncoder, ensure_ascii=False, indent=2)


# ---------------------------------------------------------------------------
# Supabase client
# ---------------------------------------------------------------------------


def _build_client() -> Client:
    """Create a Supabase client using service-role credentials from env."""
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

    if not url:
        raise ValueError(
            "SUPABASE_URL is not set. "
            "Add it to your .env file or export it before running."
        )
    if not key:
        raise ValueError(
            "SUPABASE_SERVICE_ROLE_KEY is not set. "
            "Add it to your .env file or export it before running."
        )

    logger.info("Connecting to Supabase: %s", url)
    return create_client(url, key)


# ---------------------------------------------------------------------------
# Export logic
# ---------------------------------------------------------------------------


def _fetch_table(client: Client, table: str) -> list[dict[str, Any]]:
    """Fetch all rows from a Supabase table, paginating if needed.

    Supabase's default page size is 1 000 rows; we loop until exhausted.
    """
    rows: list[dict[str, Any]] = []
    page_size = 1_000
    offset = 0

    while True:
        response = (
            client.table(table)
            .select("*")
            .range(offset, offset + page_size - 1)
            .execute()
        )
        batch: list[dict[str, Any]] = response.data or []
        rows.extend(batch)

        logger.debug(
            "Fetched %d rows from '%s' (offset=%d)", len(batch), table, offset
        )

        if len(batch) < page_size:
            # Last page — we're done
            break
        offset += page_size

    logger.info("Fetched %d total rows from '%s'", len(rows), table)
    return rows


def export_all(
    client: Client,
    output_dir: Path,
) -> dict[str, int]:
    """Export all tables to JSON files in output_dir.

    Returns a mapping of table -> row count for reporting.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    logger.info("Writing JSON files to %s", output_dir)

    table_data: dict[str, list[dict[str, Any]]] = {}
    row_counts: dict[str, int] = {}

    # Fetch and write individual table files
    for table in TABLES:
        try:
            rows = _fetch_table(client, table)
        except Exception as exc:
            logger.error("Failed to fetch table '%s': %s", table, exc)
            rows = []

        table_data[table] = rows
        row_counts[table] = len(rows)

        filename = OUTPUT_FILENAMES[table]
        out_path = output_dir / filename
        out_path.write_text(_dump(rows), encoding="utf-8")
        logger.info("Wrote %s (%d rows) → %s", filename, len(rows), out_path)

    # Write combined data.json
    combined: dict[str, Any] = {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "row_counts": row_counts,
        "vc_firms": table_data["vc_firms"],
        "companies": table_data["portfolio_companies"],
        "founders": table_data["founders"],
        "investments": table_data["investments"],
    }
    combined_path = output_dir / "data.json"
    combined_path.write_text(_dump(combined), encoding="utf-8")
    logger.info(
        "Wrote combined data.json (%d total rows) → %s",
        sum(row_counts.values()),
        combined_path,
    )

    return row_counts


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export Supabase tables to JSON files for dashboard static fallback.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help=(
            f"Directory to write JSON files into. "
            f"Defaults to {DEFAULT_OUTPUT_DIR}"
        ),
    )
    parser.add_argument(
        "--env-file",
        type=Path,
        default=Path(".env"),
        help="Path to .env file (default: .env in cwd)",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable DEBUG-level logging",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = _parse_args(argv)

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Load environment variables from .env file
    env_path = args.env_file
    if env_path.exists():
        load_dotenv(env_path)
        logger.info("Loaded environment from %s", env_path)
    else:
        load_dotenv()  # Fall back to searching parent directories
        logger.debug("No explicit .env found at %s; tried auto-discovery", env_path)

    try:
        client = _build_client()
    except ValueError as exc:
        logger.error("%s", exc)
        sys.exit(1)

    try:
        row_counts = export_all(client, args.output_dir)
    except Exception as exc:
        logger.error("Export failed: %s", exc, exc_info=True)
        sys.exit(1)

    # Summary
    print("\nExport complete:")
    for table, count in row_counts.items():
        filename = OUTPUT_FILENAMES[table]
        print(f"  {filename:<25} {count:>6} rows")
    print(f"\nOutput directory: {args.output_dir.resolve()}")


if __name__ == "__main__":
    main()
