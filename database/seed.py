#!/usr/bin/env python3
"""
Meridian VC Intelligence Platform - Database Seeder

Seeds the Supabase database from the VC_Founder_Age_Analysis_All20VCs.xlsx file.
Handles the specific Excel format where Row 1 is a merged banner, Row 2 has
headers, and data starts at Row 3.

Usage:
    python database/seed.py                              # Seed Supabase (requires .env)
    python database/seed.py --dry-run                    # Print what would be inserted
    python database/seed.py --local-json                 # Export to JSON files
    python database/seed.py --local-json --output-dir exports/seed_data
    python database/seed.py --excel-path path/to/file.xlsx
"""

import argparse
import json
import logging
import os
import re
import sys
import uuid
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import openpyxl
from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# Default path to the Excel file (relative to project root)
DEFAULT_EXCEL_PATH = "VC_Founder_Age_Analysis_All20VCs.xlsx"

# Excel structure constants
BANNER_ROW = 1      # Merged banner row (0-indexed in openpyxl: row 1)
HEADER_ROW = 2      # Actual column headers
DATA_START_ROW = 3  # First data row

# Column mapping (1-indexed to match openpyxl)
COLUMNS = {
    "vc_firm": 1,
    "company": 2,
    "sector": 3,
    "city": 4,
    "country": 5,
    "region": 6,
    "founded_year": 7,
    "investment_stage": 8,
    "company_status": 9,
    "primary_founder": 10,
    "co_founders": 11,
    "est_birth_year": 12,
    "domain_exp_years": 13,
    "prior_founder": 14,
    "education_tier": 15,
    "age_at_founding": 16,
    "current_age_2026": 17,
    "age_confidence": 18,
    "age_inference_method": 19,
    "source_notes": 20,
}

# Valid enum values (matching schema.sql CHECK constraints)
VALID_STAGES = {
    "Pre-Seed", "Seed", "Early", "Series A", "Series B",
    "Series C", "Series D", "Series E", "Growth",
}
VALID_STATUSES = {"Active", "Acquired", "IPO", "Shutdown", "Unknown"}
VALID_EDUCATION_TIERS = {"Top-10", "Top-50", "Other"}
VALID_CONFIDENCE = {"High", "Medium", "Low"}
VALID_ROLES = {"primary", "co-founder"}

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("seed")


# ---------------------------------------------------------------------------
# Utility Functions
# ---------------------------------------------------------------------------

def generate_slug(text: str) -> str:
    """Generate a URL-friendly slug from text."""
    if not text:
        return ""
    slug = text.lower().strip()
    # Replace special characters
    slug = slug.replace("°", "")
    slug = re.sub(r"[^a-z0-9\s-]", "", slug)
    slug = re.sub(r"\s+", "-", slug)
    slug = re.sub(r"-+", "-", slug)
    return slug.strip("-")


def generate_uuid() -> str:
    """Generate a new UUID v4 string."""
    return str(uuid.uuid4())


def safe_int(value: Any) -> Optional[int]:
    """Safely convert a value to int, returning None on failure."""
    if value is None:
        return None
    try:
        return int(value)
    except (ValueError, TypeError):
        return None


def safe_str(value: Any) -> Optional[str]:
    """Safely convert a value to a stripped string, returning None if empty."""
    if value is None:
        return None
    s = str(value).strip()
    return s if s else None


def parse_education_tier(raw: Optional[str]) -> tuple[Optional[str], Optional[str]]:
    """
    Parse education tier string into (tier, university_detail).

    Examples:
        "Top-10 (Stanford CS)" -> ("Top-10", "Stanford CS")
        "Top-50 (London Math + Oxford/Cambridge)" -> ("Top-50", "London Math + Oxford/Cambridge")
        "Other (IT U Copenhagen)" -> ("Other", "IT U Copenhagen")
        "Other" -> ("Other", None)
        None -> (None, None)
    """
    if not raw:
        return None, None

    raw = raw.strip()

    # Match pattern: "Tier (detail)"
    match = re.match(r"^(Top-10|Top-50|Other)\s*(?:\((.+)\))?$", raw)
    if match:
        tier = match.group(1)
        detail = match.group(2)
        return tier, safe_str(detail)

    # Fallback: check if it starts with a known tier
    for tier in VALID_EDUCATION_TIERS:
        if raw.startswith(tier):
            remainder = raw[len(tier):].strip()
            if remainder.startswith("(") and remainder.endswith(")"):
                return tier, safe_str(remainder[1:-1])
            return tier, safe_str(remainder) if remainder else None

    logger.warning(f"Could not parse education tier: '{raw}'")
    return None, raw


def parse_company_status(raw: Optional[str]) -> tuple[str, Optional[str]]:
    """
    Parse company status string into (status, status_detail).

    Examples:
        "Active" -> ("Active", None)
        "Acquired (Amazon 2024)" -> ("Acquired", "Amazon 2024")
        "IPO (NASDAQ)" -> ("IPO", "NASDAQ")
        None -> ("Unknown", None)
    """
    if not raw:
        return "Unknown", None

    raw = raw.strip()

    # Match pattern: "Status (detail)"
    match = re.match(r"^(\w+)\s*(?:\((.+)\))?$", raw)
    if match:
        status = match.group(1)
        detail = match.group(2)

        # Normalize status to valid enum
        if status in VALID_STATUSES:
            return status, safe_str(detail)

        # Try case-insensitive match
        for valid in VALID_STATUSES:
            if status.lower() == valid.lower():
                return valid, safe_str(detail)

    # Fallback
    logger.warning(f"Could not parse company status: '{raw}', defaulting to 'Unknown'")
    return "Unknown", raw


def parse_co_founders(raw: Optional[str]) -> list[str]:
    """
    Parse comma-separated co-founder names.

    Examples:
        "Denis Yarats, Johnny Ho, Andy Konwinski" -> ["Denis Yarats", "Johnny Ho", "Andy Konwinski"]
        "Piotr Dabkowski" -> ["Piotr Dabkowski"]
        None -> []
        "" -> []
    """
    if not raw:
        return []

    raw = str(raw).strip()
    if not raw:
        return []

    # Split by comma, strip whitespace, filter empty
    names = [name.strip() for name in raw.split(",")]
    return [name for name in names if name]


def normalize_stage(raw: Optional[str]) -> Optional[str]:
    """Normalize investment stage to match schema CHECK constraint."""
    if not raw:
        return None

    raw = raw.strip()
    if raw in VALID_STAGES:
        return raw

    # Try case-insensitive match
    for valid in VALID_STAGES:
        if raw.lower() == valid.lower():
            return valid

    logger.warning(f"Unknown investment stage: '{raw}'")
    return None


# ---------------------------------------------------------------------------
# Excel Reader
# ---------------------------------------------------------------------------

class ExcelReader:
    """Reads the VC Founder Age Analysis Excel file."""

    def __init__(self, excel_path: str):
        self.excel_path = Path(excel_path)
        if not self.excel_path.exists():
            raise FileNotFoundError(f"Excel file not found: {self.excel_path}")

        logger.info(f"Loading Excel file: {self.excel_path}")
        self.wb = openpyxl.load_workbook(str(self.excel_path), data_only=True)
        self.ws = self.wb["Portfolio Database"]
        logger.info(
            f"Loaded sheet 'Portfolio Database': "
            f"{self.ws.max_row - DATA_START_ROW + 1} data rows, "
            f"{self.ws.max_column} columns"
        )

    def _cell(self, row: int, col_name: str) -> Any:
        """Get cell value by row number and column name."""
        return self.ws.cell(row=row, column=COLUMNS[col_name]).value

    def read_rows(self) -> list[dict]:
        """Read all data rows into a list of dictionaries."""
        rows = []
        for row_idx in range(DATA_START_ROW, self.ws.max_row + 1):
            # Skip completely empty rows
            vc_firm = safe_str(self._cell(row_idx, "vc_firm"))
            company = safe_str(self._cell(row_idx, "company"))
            if not vc_firm and not company:
                continue

            row_data = {
                "row_number": row_idx,
                "vc_firm": vc_firm,
                "company": company,
                "sector": safe_str(self._cell(row_idx, "sector")),
                "city": safe_str(self._cell(row_idx, "city")),
                "country": safe_str(self._cell(row_idx, "country")),
                "region": safe_str(self._cell(row_idx, "region")),
                "founded_year": safe_int(self._cell(row_idx, "founded_year")),
                "investment_stage": safe_str(self._cell(row_idx, "investment_stage")),
                "company_status": safe_str(self._cell(row_idx, "company_status")),
                "primary_founder": safe_str(self._cell(row_idx, "primary_founder")),
                "co_founders": safe_str(self._cell(row_idx, "co_founders")),
                "est_birth_year": safe_int(self._cell(row_idx, "est_birth_year")),
                "domain_exp_years": safe_int(self._cell(row_idx, "domain_exp_years")),
                "prior_founder": safe_str(self._cell(row_idx, "prior_founder")),
                "education_tier": safe_str(self._cell(row_idx, "education_tier")),
                "age_at_founding": safe_int(self._cell(row_idx, "age_at_founding")),
                "current_age_2026": safe_int(self._cell(row_idx, "current_age_2026")),
                "age_confidence": safe_str(self._cell(row_idx, "age_confidence")),
                "age_inference_method": safe_str(self._cell(row_idx, "age_inference_method")),
                "source_notes": safe_str(self._cell(row_idx, "source_notes")),
            }
            rows.append(row_data)

        logger.info(f"Read {len(rows)} data rows from Excel")
        return rows


# ---------------------------------------------------------------------------
# Data Transformer
# ---------------------------------------------------------------------------

class DataTransformer:
    """Transforms raw Excel rows into normalized database records."""

    def __init__(self):
        # Lookup maps: name -> record dict (with generated UUIDs)
        self.vc_firms: dict[str, dict] = {}
        self.companies: dict[str, dict] = {}  # keyed by company name
        self.investments: list[dict] = []
        self.founders: list[dict] = []

        # Track company-to-VCs for the investment junction
        self.company_vc_map: dict[str, set[str]] = defaultdict(set)

        # Stats
        self.stats = {
            "vc_firms": 0,
            "companies": 0,
            "investments": 0,
            "primary_founders": 0,
            "co_founders": 0,
            "parse_warnings": 0,
        }

    def transform(self, rows: list[dict]) -> None:
        """Transform all rows into normalized records."""
        logger.info("Transforming data...")

        for row in rows:
            self._process_row(row)

        self.stats["vc_firms"] = len(self.vc_firms)
        self.stats["companies"] = len(self.companies)
        self.stats["investments"] = len(self.investments)

        logger.info(
            f"Transform complete: "
            f"{self.stats['vc_firms']} VCs, "
            f"{self.stats['companies']} companies, "
            f"{self.stats['investments']} investments, "
            f"{self.stats['primary_founders']} primary founders, "
            f"{self.stats['co_founders']} co-founders"
        )

    def _process_row(self, row: dict) -> None:
        """Process a single Excel row."""
        vc_name = row["vc_firm"]
        company_name = row["company"]

        if not vc_name or not company_name:
            logger.warning(f"Row {row['row_number']}: Missing VC firm or company name, skipping")
            return

        # --- VC Firm ---
        if vc_name not in self.vc_firms:
            self.vc_firms[vc_name] = {
                "id": generate_uuid(),
                "name": vc_name,
                "slug": generate_slug(vc_name),
            }

        vc_id = self.vc_firms[vc_name]["id"]

        # --- Company ---
        # Parse status
        status, status_detail = parse_company_status(row["company_status"])
        stage = normalize_stage(row["investment_stage"])

        if company_name not in self.companies:
            self.companies[company_name] = {
                "id": generate_uuid(),
                "name": company_name,
                "slug": generate_slug(company_name),
                "sector": row["sector"],
                "city": row["city"],
                "country": row["country"],
                "region": row["region"],
                "founded_year": row["founded_year"],
                "stage": stage,
                "status": status,
                "status_detail": status_detail,
            }
        else:
            # Company already seen (possibly under another VC) -- update stage
            # if the new one is a later round
            existing = self.companies[company_name]
            if stage and not existing["stage"]:
                existing["stage"] = stage

        company_id = self.companies[company_name]["id"]

        # --- Investment junction ---
        # Avoid duplicates: same VC + same company
        vc_company_key = f"{vc_name}::{company_name}"
        if vc_company_key not in self.company_vc_map:
            self.company_vc_map[vc_company_key] = True
            self.investments.append({
                "id": generate_uuid(),
                "vc_id": vc_id,
                "company_id": company_id,
                "stage": stage,
            })

        # --- Primary Founder ---
        if row["primary_founder"]:
            education_tier, university = parse_education_tier(row["education_tier"])

            founder_record = {
                "id": generate_uuid(),
                "company_id": company_id,
                "full_name": row["primary_founder"],
                "role": "primary",
                "est_birth_year": row["est_birth_year"],
                "domain_exp_years": row["domain_exp_years"],
                "prior_founder": row["prior_founder"] == "Yes" if row["prior_founder"] else False,
                "education_tier": education_tier,
                "university": university,
                "age_at_founding": row["age_at_founding"],
                "current_age_2026": row["current_age_2026"],
                "age_confidence": row["age_confidence"] if row["age_confidence"] in VALID_CONFIDENCE else None,
                "age_inference_method": row["age_inference_method"],
                "source_notes": row["source_notes"],
            }
            self.founders.append(founder_record)
            self.stats["primary_founders"] += 1

        # --- Co-Founders ---
        co_founder_names = parse_co_founders(row["co_founders"])
        for cf_name in co_founder_names:
            cf_record = {
                "id": generate_uuid(),
                "company_id": company_id,
                "full_name": cf_name,
                "role": "co-founder",
                # Co-founders don't have individual age data in the Excel
                "est_birth_year": None,
                "domain_exp_years": None,
                "prior_founder": False,
                "education_tier": None,
                "university": None,
                "age_at_founding": None,
                "current_age_2026": None,
                "age_confidence": None,
                "age_inference_method": None,
                "source_notes": None,
            }
            self.founders.append(cf_record)
            self.stats["co_founders"] += 1

    def get_vc_firms_records(self) -> list[dict]:
        """Get VC firms ready for database insertion."""
        return list(self.vc_firms.values())

    def get_companies_records(self) -> list[dict]:
        """Get portfolio companies ready for database insertion."""
        return list(self.companies.values())

    def get_investments_records(self) -> list[dict]:
        """Get investment junction records."""
        return self.investments

    def get_founders_records(self) -> list[dict]:
        """Get founder records."""
        return self.founders


# ---------------------------------------------------------------------------
# Supabase Loader
# ---------------------------------------------------------------------------

class SupabaseLoader:
    """Loads transformed data into Supabase."""

    def __init__(self):
        load_dotenv()
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

        if not url or not key:
            raise EnvironmentError(
                "SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set in .env"
            )

        from supabase import create_client
        self.client = create_client(url, key)
        logger.info(f"Connected to Supabase: {url}")

    def _upsert_batch(self, table: str, records: list[dict], batch_size: int = 100) -> int:
        """Insert records in batches, returning count of inserted rows."""
        total = 0
        for i in range(0, len(records), batch_size):
            batch = records[i : i + batch_size]
            try:
                result = self.client.table(table).upsert(batch).execute()
                total += len(batch)
                logger.debug(f"  {table}: inserted batch {i // batch_size + 1} ({len(batch)} rows)")
            except Exception as e:
                logger.error(f"  {table}: batch {i // batch_size + 1} failed: {e}")
                # Log first record for debugging
                if batch:
                    logger.error(f"  First record in failed batch: {json.dumps(batch[0], indent=2, default=str)}")
                raise
        return total

    def load(self, transformer: DataTransformer) -> dict:
        """Load all transformed data into Supabase. Returns stats dict."""
        stats = {}

        # Order matters: vc_firms and companies first (referenced by investments/founders)
        logger.info("Loading VC firms...")
        stats["vc_firms"] = self._upsert_batch("vc_firms", transformer.get_vc_firms_records())
        logger.info(f"  -> {stats['vc_firms']} VC firms loaded")

        logger.info("Loading portfolio companies...")
        stats["companies"] = self._upsert_batch("portfolio_companies", transformer.get_companies_records())
        logger.info(f"  -> {stats['companies']} companies loaded")

        logger.info("Loading investments...")
        stats["investments"] = self._upsert_batch("investments", transformer.get_investments_records())
        logger.info(f"  -> {stats['investments']} investments loaded")

        logger.info("Loading founders...")
        stats["founders"] = self._upsert_batch("founders", transformer.get_founders_records())
        logger.info(f"  -> {stats['founders']} founders loaded")

        # Refresh materialized views
        logger.info("Refreshing materialized views...")
        try:
            self.client.rpc("refresh_materialized_views").execute()
            logger.info("  -> Materialized views refreshed")
        except Exception as e:
            logger.warning(f"  -> Could not refresh materialized views: {e}")

        return stats


# ---------------------------------------------------------------------------
# JSON Exporter (--local-json mode)
# ---------------------------------------------------------------------------

class JsonExporter:
    """Exports transformed data to local JSON files."""

    def __init__(self, output_dir: str):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"JSON export directory: {self.output_dir}")

    def export(self, transformer: DataTransformer) -> dict:
        """Export all data to JSON files. Returns stats dict."""
        stats = {}

        datasets = {
            "vc_firms.json": transformer.get_vc_firms_records(),
            "portfolio_companies.json": transformer.get_companies_records(),
            "investments.json": transformer.get_investments_records(),
            "founders.json": transformer.get_founders_records(),
        }

        for filename, records in datasets.items():
            filepath = self.output_dir / filename
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(records, f, indent=2, ensure_ascii=False, default=str)

            table_name = filename.replace(".json", "")
            stats[table_name] = len(records)
            logger.info(f"  Exported {len(records)} records to {filepath}")

        return stats


# ---------------------------------------------------------------------------
# Dry Run Reporter
# ---------------------------------------------------------------------------

class DryRunReporter:
    """Prints what would be inserted without actually doing it."""

    @staticmethod
    def report(transformer: DataTransformer) -> None:
        """Print a detailed summary of what would be inserted."""
        print("\n" + "=" * 70)
        print("DRY RUN - No data will be written")
        print("=" * 70)

        # VC Firms
        vcs = transformer.get_vc_firms_records()
        print(f"\n--- VC Firms ({len(vcs)}) ---")
        for vc in sorted(vcs, key=lambda x: x["name"]):
            print(f"  {vc['name']} (slug: {vc['slug']})")

        # Companies
        companies = transformer.get_companies_records()
        print(f"\n--- Portfolio Companies ({len(companies)}) ---")
        for co in sorted(companies, key=lambda x: x["name"]):
            status_str = co["status"]
            if co.get("status_detail"):
                status_str += f" ({co['status_detail']})"
            print(
                f"  {co['name']} | {co.get('sector', 'N/A')} | "
                f"{co.get('city', '?')}, {co.get('country', '?')} | "
                f"{co.get('founded_year', '?')} | {co.get('stage', '?')} | {status_str}"
            )

        # Investments
        investments = transformer.get_investments_records()
        print(f"\n--- Investments ({len(investments)}) ---")
        # Build lookup for display
        vc_lookup = {v["id"]: v["name"] for v in vcs}
        co_lookup = {c["id"]: c["name"] for c in companies}
        for inv in investments:
            vc_name = vc_lookup.get(inv["vc_id"], "?")
            co_name = co_lookup.get(inv["company_id"], "?")
            print(f"  {vc_name} -> {co_name} (stage: {inv.get('stage', '?')})")

        # Founders
        founders = transformer.get_founders_records()
        primary = [f for f in founders if f["role"] == "primary"]
        cofounders = [f for f in founders if f["role"] == "co-founder"]

        print(f"\n--- Founders ({len(founders)} total: {len(primary)} primary, {len(cofounders)} co-founders) ---")
        for f in sorted(primary, key=lambda x: x["full_name"]):
            age_str = f"age {f['age_at_founding']}" if f.get("age_at_founding") else "age ?"
            edu_str = f"{f['education_tier']}" if f.get("education_tier") else "edu ?"
            if f.get("university"):
                edu_str += f" ({f['university']})"
            co_name = co_lookup.get(f["company_id"], "?")
            print(f"  [PRIMARY] {f['full_name']} @ {co_name} | {age_str} | {edu_str}")

        print(f"\n  Co-founders (showing first 20 of {len(cofounders)}):")
        for f in sorted(cofounders, key=lambda x: x["full_name"])[:20]:
            co_name = co_lookup.get(f["company_id"], "?")
            print(f"  [CO-FOUNDER] {f['full_name']} @ {co_name}")
        if len(cofounders) > 20:
            print(f"  ... and {len(cofounders) - 20} more")

        # Summary
        print("\n" + "=" * 70)
        print("SUMMARY")
        print("=" * 70)
        print(f"  VC Firms:           {len(vcs)}")
        print(f"  Portfolio Companies: {len(companies)}")
        print(f"  Investments:        {len(investments)}")
        print(f"  Primary Founders:   {len(primary)}")
        print(f"  Co-Founders:        {len(cofounders)}")
        print(f"  Total Founders:     {len(founders)}")
        print("=" * 70)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def find_excel_file(explicit_path: Optional[str] = None) -> str:
    """Locate the Excel file, trying multiple paths."""
    candidates = []

    if explicit_path:
        candidates.append(Path(explicit_path))
    else:
        # Try relative to CWD and project root patterns
        candidates.extend([
            Path(DEFAULT_EXCEL_PATH),
            Path("..") / DEFAULT_EXCEL_PATH,
            Path(__file__).parent.parent / DEFAULT_EXCEL_PATH,
        ])

    for path in candidates:
        resolved = path.resolve()
        if resolved.exists():
            return str(resolved)

    tried = ", ".join(str(c.resolve()) for c in candidates)
    raise FileNotFoundError(
        f"Could not find Excel file. Tried: {tried}\n"
        f"Use --excel-path to specify the location."
    )


def main():
    parser = argparse.ArgumentParser(
        description="Seed the Meridian database from the VC Founder Age Analysis Excel file."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would be inserted without writing to the database.",
    )
    parser.add_argument(
        "--local-json",
        action="store_true",
        help="Export data to local JSON files instead of Supabase.",
    )
    parser.add_argument(
        "--output-dir",
        default="exports/seed_data",
        help="Output directory for JSON export (default: exports/seed_data).",
    )
    parser.add_argument(
        "--excel-path",
        default=None,
        help=f"Path to the Excel file (default: auto-detect '{DEFAULT_EXCEL_PATH}').",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose (DEBUG) logging.",
    )

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    start_time = datetime.now()
    logger.info("=" * 60)
    logger.info("Meridian Database Seeder")
    logger.info("=" * 60)

    try:
        # Step 1: Find and read the Excel file
        excel_path = find_excel_file(args.excel_path)
        reader = ExcelReader(excel_path)
        rows = reader.read_rows()

        if not rows:
            logger.error("No data rows found in Excel file!")
            sys.exit(1)

        # Step 2: Transform data
        transformer = DataTransformer()
        transformer.transform(rows)

        # Step 3: Load or export
        if args.dry_run:
            DryRunReporter.report(transformer)
        elif args.local_json:
            exporter = JsonExporter(args.output_dir)
            stats = exporter.export(transformer)
            logger.info(f"JSON export complete: {stats}")
        else:
            loader = SupabaseLoader()
            stats = loader.load(transformer)
            logger.info(f"Supabase load complete: {stats}")

        elapsed = (datetime.now() - start_time).total_seconds()
        logger.info(f"Done in {elapsed:.1f}s")

    except FileNotFoundError as e:
        logger.error(str(e))
        sys.exit(1)
    except EnvironmentError as e:
        logger.error(str(e))
        sys.exit(1)
    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
