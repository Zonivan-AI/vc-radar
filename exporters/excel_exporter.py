#!/usr/bin/env python3
"""
Meridian VC Intelligence Platform - Excel Exporter

Exports data from Supabase to a formatted Excel workbook matching the original
VC_Founder_Age_Analysis_All20VCs.xlsx format with two sheets:
  1. Portfolio Database - Full company/founder dataset
  2. Analysis Dashboard - Aggregated analytics

Usage:
    python exporters/excel_exporter.py                         # Export from Supabase
    python exporters/excel_exporter.py --output exports/report.xlsx
    python exporters/excel_exporter.py --from-json exports/seed_data/
"""

import argparse
import json
import logging
import os
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import openpyxl
from openpyxl.styles import (
    Alignment,
    Border,
    Font,
    GradientFill,
    NamedStyle,
    PatternFill,
    Side,
    numbers,
)
from openpyxl.utils import get_column_letter
from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("excel_exporter")

# ---------------------------------------------------------------------------
# Style Constants
# ---------------------------------------------------------------------------

# Colors
COLOR_BANNER_BG = "1B1F3B"       # Deep navy for banner
COLOR_BANNER_FG = "FFFFFF"       # White text
COLOR_HEADER_BG = "2D3250"       # Slightly lighter navy for headers
COLOR_HEADER_FG = "E8E8E8"       # Light gray text
COLOR_ALT_ROW = "F5F5FA"         # Very light lavender for alternating rows
COLOR_BORDER = "C0C0C0"          # Light gray borders
COLOR_SECTION_BG = "3A3F5C"      # Section header background
COLOR_SECTION_FG = "FFFFFF"      # Section header text

# Age heatmap colors (young -> mid -> veteran)
COLOR_AGE_YOUNG = "27AE60"       # Green: < 25
COLOR_AGE_EARLY = "8BC34A"       # Light green: 25-29
COLOR_AGE_MID = "FFC107"         # Amber: 30-34
COLOR_AGE_MATURE = "FF9800"      # Orange: 35-39
COLOR_AGE_EXPERIENCED = "FF5722" # Deep orange: 40-49
COLOR_AGE_VETERAN = "D32F2F"     # Red: 50+

# Confidence colors
COLOR_CONF_HIGH = "27AE60"       # Green
COLOR_CONF_MEDIUM = "FFC107"     # Amber
COLOR_CONF_LOW = "FF5722"        # Red-orange

# Fonts
FONT_BANNER = Font(name="Calibri", size=14, bold=True, color=COLOR_BANNER_FG)
FONT_HEADER = Font(name="Calibri", size=10, bold=True, color=COLOR_HEADER_FG)
FONT_DATA = Font(name="Calibri", size=10, color="333333")
FONT_DATA_BOLD = Font(name="Calibri", size=10, bold=True, color="333333")
FONT_SECTION = Font(name="Calibri", size=11, bold=True, color=COLOR_SECTION_FG)
FONT_FOOTER = Font(name="Calibri", size=9, italic=True, color="666666")

# Fills
FILL_BANNER = PatternFill(start_color=COLOR_BANNER_BG, end_color=COLOR_BANNER_BG, fill_type="solid")
FILL_HEADER = PatternFill(start_color=COLOR_HEADER_BG, end_color=COLOR_HEADER_BG, fill_type="solid")
FILL_ALT_ROW = PatternFill(start_color=COLOR_ALT_ROW, end_color=COLOR_ALT_ROW, fill_type="solid")
FILL_SECTION = PatternFill(start_color=COLOR_SECTION_BG, end_color=COLOR_SECTION_BG, fill_type="solid")

# Borders
THIN_BORDER = Border(
    left=Side(style="thin", color=COLOR_BORDER),
    right=Side(style="thin", color=COLOR_BORDER),
    top=Side(style="thin", color=COLOR_BORDER),
    bottom=Side(style="thin", color=COLOR_BORDER),
)

# Alignment
ALIGN_CENTER = Alignment(horizontal="center", vertical="center", wrap_text=False)
ALIGN_LEFT = Alignment(horizontal="left", vertical="center", wrap_text=True)
ALIGN_WRAP = Alignment(horizontal="left", vertical="top", wrap_text=True)


# ---------------------------------------------------------------------------
# Data Fetcher
# ---------------------------------------------------------------------------

class SupabaseFetcher:
    """Fetches data from Supabase for export."""

    def __init__(self):
        load_dotenv()
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_ANON_KEY")

        if not url or not key:
            raise EnvironmentError(
                "SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY (or SUPABASE_ANON_KEY) "
                "must be set in .env"
            )

        from supabase import create_client
        self.client = create_client(url, key)
        logger.info(f"Connected to Supabase: {url}")

    def fetch_all(self) -> dict:
        """Fetch all tables needed for the export."""
        data = {}

        logger.info("Fetching VC firms...")
        result = self.client.table("vc_firms").select("*").execute()
        data["vc_firms"] = result.data
        logger.info(f"  -> {len(data['vc_firms'])} VC firms")

        logger.info("Fetching portfolio companies...")
        result = self.client.table("portfolio_companies").select("*").execute()
        data["companies"] = result.data
        logger.info(f"  -> {len(data['companies'])} companies")

        logger.info("Fetching investments...")
        result = self.client.table("investments").select("*").execute()
        data["investments"] = result.data
        logger.info(f"  -> {len(data['investments'])} investments")

        logger.info("Fetching founders...")
        result = self.client.table("founders").select("*").execute()
        data["founders"] = result.data
        logger.info(f"  -> {len(data['founders'])} founders")

        return data


class JsonFetcher:
    """Fetches data from local JSON files (produced by seed.py --local-json)."""

    def __init__(self, json_dir: str):
        self.json_dir = Path(json_dir)
        if not self.json_dir.exists():
            raise FileNotFoundError(f"JSON directory not found: {self.json_dir}")
        logger.info(f"Reading JSON from: {self.json_dir}")

    def fetch_all(self) -> dict:
        """Read all JSON files into a data dict."""
        data = {}

        file_map = {
            "vc_firms": "vc_firms.json",
            "companies": "portfolio_companies.json",
            "investments": "investments.json",
            "founders": "founders.json",
        }

        for key, filename in file_map.items():
            filepath = self.json_dir / filename
            if filepath.exists():
                with open(filepath, "r", encoding="utf-8") as f:
                    data[key] = json.load(f)
                logger.info(f"  Loaded {len(data[key])} {key} from {filename}")
            else:
                logger.warning(f"  File not found: {filepath}, using empty list")
                data[key] = []

        return data


# ---------------------------------------------------------------------------
# Data Assembler
# ---------------------------------------------------------------------------

class DataAssembler:
    """Assembles fetched data into the flat row format for the Excel export."""

    def __init__(self, data: dict):
        self.data = data

        # Build lookup maps
        self.vc_by_id = {v["id"]: v for v in data.get("vc_firms", [])}
        self.company_by_id = {c["id"]: c for c in data.get("companies", [])}

        # Map company_id -> list of VC IDs (from investments)
        self.company_vcs: dict[str, list[str]] = defaultdict(list)
        for inv in data.get("investments", []):
            self.company_vcs[inv["company_id"]].append(inv["vc_id"])

        # Map company_id -> list of founders
        self.company_founders: dict[str, list[dict]] = defaultdict(list)
        for f in data.get("founders", []):
            self.company_founders[f["company_id"]].append(f)

    def _reconstruct_education_tier(self, founder: dict) -> Optional[str]:
        """Reconstruct the combined education tier string."""
        tier = founder.get("education_tier")
        university = founder.get("university")
        if not tier:
            return None
        if university:
            return f"{tier} ({university})"
        return tier

    def _reconstruct_status(self, company: dict) -> str:
        """Reconstruct the combined company status string."""
        status = company.get("status", "Active")
        detail = company.get("status_detail")
        if detail:
            return f"{status} ({detail})"
        return status

    def assemble_portfolio_rows(self) -> list[list[Any]]:
        """
        Assemble flat rows for the Portfolio Database sheet.
        Each row represents one company as seen by one VC, with founder data.
        """
        rows = []

        # Group by VC, then by company
        for inv in sorted(
            self.data.get("investments", []),
            key=lambda x: (
                self.vc_by_id.get(x["vc_id"], {}).get("name", ""),
                self.company_by_id.get(x["company_id"], {}).get("name", ""),
            ),
        ):
            vc = self.vc_by_id.get(inv["vc_id"], {})
            company = self.company_by_id.get(inv["company_id"], {})
            founders = self.company_founders.get(inv["company_id"], [])

            # Find primary founder
            primary = None
            cofounders = []
            for f in founders:
                if f.get("role") == "primary":
                    primary = f
                else:
                    cofounders.append(f)

            # Build the row
            row = [
                vc.get("name", ""),
                company.get("name", ""),
                company.get("sector", ""),
                company.get("city", ""),
                company.get("country", ""),
                company.get("region", ""),
                company.get("founded_year"),
                inv.get("stage") or company.get("stage", ""),
                self._reconstruct_status(company),
                primary.get("full_name", "") if primary else "",
                ", ".join(f["full_name"] for f in cofounders) if cofounders else "",
                primary.get("est_birth_year") if primary else None,
                primary.get("domain_exp_years") if primary else None,
                "Yes" if primary and primary.get("prior_founder") else "No" if primary else "",
                self._reconstruct_education_tier(primary) if primary else "",
                primary.get("age_at_founding") if primary else None,
                primary.get("current_age_2026") if primary else None,
                primary.get("age_confidence", "") if primary else "",
                primary.get("age_inference_method", "") if primary else "",
                primary.get("source_notes", "") if primary else "",
            ]
            rows.append(row)

        return rows

    def compute_vc_stats(self) -> list[dict]:
        """Compute per-VC statistics for the Analysis Dashboard."""
        vc_stats = {}

        for inv in self.data.get("investments", []):
            vc_id = inv["vc_id"]
            company_id = inv["company_id"]

            if vc_id not in vc_stats:
                vc = self.vc_by_id.get(vc_id, {})
                vc_stats[vc_id] = {
                    "name": vc.get("name", "Unknown"),
                    "companies": set(),
                    "ages": [],
                }

            vc_stats[vc_id]["companies"].add(company_id)

            # Get primary founder ages
            founders = self.company_founders.get(company_id, [])
            for f in founders:
                if f.get("role") == "primary" and f.get("age_at_founding"):
                    vc_stats[vc_id]["ages"].append(f["age_at_founding"])

        # Format results
        results = []
        for vc_id, stats in sorted(vc_stats.items(), key=lambda x: x[1]["name"]):
            avg_age = sum(stats["ages"]) / len(stats["ages"]) if stats["ages"] else None
            results.append({
                "name": stats["name"],
                "company_count": len(stats["companies"]),
                "avg_age": avg_age,
            })

        return results

    def compute_age_buckets(self) -> list[dict]:
        """Compute age bucket distribution."""
        buckets = defaultdict(int)
        bucket_order = ["<25", "25-29", "30-34", "35-39", "40-49", "50+"]

        for f in self.data.get("founders", []):
            if f.get("role") != "primary" or not f.get("age_at_founding"):
                continue
            age = f["age_at_founding"]
            if age < 25:
                buckets["<25"] += 1
            elif age <= 29:
                buckets["25-29"] += 1
            elif age <= 34:
                buckets["30-34"] += 1
            elif age <= 39:
                buckets["35-39"] += 1
            elif age <= 49:
                buckets["40-49"] += 1
            else:
                buckets["50+"] += 1

        total = sum(buckets.values())
        descriptions = {
            "<25": "Prodigy / Student drop-out",
            "25-29": "Early career (0-7 yrs exp)",
            "30-34": "Mid career (8-12 yrs exp)",
            "35-39": "Experienced (12-17 yrs exp)",
            "40-49": "Veteran / Domain expert",
            "50+": "Elder statesperson / Academic",
        }

        return [
            {
                "bucket": b,
                "description": descriptions.get(b, ""),
                "count": buckets.get(b, 0),
                "percentage": buckets.get(b, 0) / total if total > 0 else 0,
            }
            for b in bucket_order
        ]

    def compute_region_stats(self) -> list[dict]:
        """Compute per-region statistics."""
        region_data: dict[str, list[int]] = defaultdict(list)

        for f in self.data.get("founders", []):
            if f.get("role") != "primary" or not f.get("age_at_founding"):
                continue
            company = self.company_by_id.get(f["company_id"], {})
            region = company.get("region", "Other")
            if region:
                region_data[region].append(f["age_at_founding"])

        results = []
        for region in sorted(region_data.keys()):
            ages = region_data[region]
            results.append({
                "region": region,
                "count": len(ages),
                "avg_age": sum(ages) / len(ages) if ages else None,
            })

        return sorted(results, key=lambda x: x["count"], reverse=True)

    def compute_prior_founder_stats(self) -> list[dict]:
        """Compute prior founder vs first-time stats."""
        prior_ages = []
        first_ages = []

        for f in self.data.get("founders", []):
            if f.get("role") != "primary" or not f.get("age_at_founding"):
                continue
            if f.get("prior_founder"):
                prior_ages.append(f["age_at_founding"])
            else:
                first_ages.append(f["age_at_founding"])

        return [
            {
                "type": "Prior / Serial Founder (Yes)",
                "count": len(prior_ages),
                "avg_age": sum(prior_ages) / len(prior_ages) if prior_ages else None,
            },
            {
                "type": "First-Time Founder (No)",
                "count": len(first_ages),
                "avg_age": sum(first_ages) / len(first_ages) if first_ages else None,
            },
        ]

    def compute_confidence_stats(self) -> list[dict]:
        """Compute age confidence breakdown."""
        conf_counts: dict[str, int] = defaultdict(int)

        for f in self.data.get("founders", []):
            if f.get("role") != "primary":
                continue
            conf = f.get("age_confidence", "Low")
            if conf:
                conf_counts[conf] += 1

        total = sum(conf_counts.values())
        descriptions = {
            "High": "Exact age / birth year from Wikipedia, stated in press",
            "Medium": "LinkedIn graduation year -> +/-1-2 yr estimate",
            "Low": "Pattern inference from seniority / role titles",
        }

        return [
            {
                "level": level,
                "count": conf_counts.get(level, 0),
                "percentage": conf_counts.get(level, 0) / total if total > 0 else 0,
                "description": descriptions.get(level, ""),
            }
            for level in ["High", "Medium", "Low"]
        ]


# ---------------------------------------------------------------------------
# Excel Writer
# ---------------------------------------------------------------------------

class ExcelWriter:
    """Writes the formatted Excel workbook."""

    # Portfolio Database column headers
    PORTFOLIO_HEADERS = [
        "VC Firm",
        "Company",
        "Sector / Category",
        "City",
        "Country",
        "Region",
        "Founded Year",
        "Investment Stage",
        "Company Status",
        "Primary Founder",
        "Co-Founders",
        "Est. Birth Year",
        "Domain Exp (Yrs)",
        "Prior Founder?",
        "Education Tier",
        "Age at Founding",
        "Current Age (2026)",
        "Age Confidence",
        "Age Inference Method",
        "Source / Notes",
    ]

    # Column widths for Portfolio Database
    PORTFOLIO_WIDTHS = [
        20,   # VC Firm
        25,   # Company
        35,   # Sector / Category
        18,   # City
        10,   # Country
        14,   # Region
        14,   # Founded Year
        16,   # Investment Stage
        22,   # Company Status
        22,   # Primary Founder
        40,   # Co-Founders
        14,   # Est. Birth Year
        14,   # Domain Exp
        14,   # Prior Founder
        45,   # Education Tier
        16,   # Age at Founding
        16,   # Current Age
        16,   # Age Confidence
        30,   # Age Inference Method
        55,   # Source / Notes
    ]

    def __init__(self, output_path: str):
        self.output_path = Path(output_path)
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        self.wb = openpyxl.Workbook()

    def _get_age_fill(self, age: Optional[int]) -> Optional[PatternFill]:
        """Return a fill color based on founder age at founding."""
        if age is None:
            return None
        if age < 25:
            return PatternFill(start_color=COLOR_AGE_YOUNG, end_color=COLOR_AGE_YOUNG, fill_type="solid")
        elif age < 30:
            return PatternFill(start_color=COLOR_AGE_EARLY, end_color=COLOR_AGE_EARLY, fill_type="solid")
        elif age < 35:
            return PatternFill(start_color=COLOR_AGE_MID, end_color=COLOR_AGE_MID, fill_type="solid")
        elif age < 40:
            return PatternFill(start_color=COLOR_AGE_MATURE, end_color=COLOR_AGE_MATURE, fill_type="solid")
        elif age < 50:
            return PatternFill(start_color=COLOR_AGE_EXPERIENCED, end_color=COLOR_AGE_EXPERIENCED, fill_type="solid")
        else:
            return PatternFill(start_color=COLOR_AGE_VETERAN, end_color=COLOR_AGE_VETERAN, fill_type="solid")

    def _get_confidence_fill(self, confidence: Optional[str]) -> Optional[PatternFill]:
        """Return a fill color based on age confidence level."""
        if confidence == "High":
            return PatternFill(start_color=COLOR_CONF_HIGH, end_color=COLOR_CONF_HIGH, fill_type="solid")
        elif confidence == "Medium":
            return PatternFill(start_color=COLOR_CONF_MEDIUM, end_color=COLOR_CONF_MEDIUM, fill_type="solid")
        elif confidence == "Low":
            return PatternFill(start_color=COLOR_CONF_LOW, end_color=COLOR_CONF_LOW, fill_type="solid")
        return None

    def _apply_cell_style(
        self,
        ws,
        row: int,
        col: int,
        value: Any,
        font: Font = FONT_DATA,
        fill: Optional[PatternFill] = None,
        alignment: Alignment = ALIGN_LEFT,
        number_format: Optional[str] = None,
    ):
        """Write a value to a cell and apply styling."""
        cell = ws.cell(row=row, column=col, value=value)
        cell.font = font
        cell.alignment = alignment
        cell.border = THIN_BORDER
        if fill:
            cell.fill = fill
        if number_format:
            cell.number_format = number_format

    def write_portfolio_sheet(self, rows: list[list[Any]]) -> None:
        """Write the Portfolio Database sheet."""
        ws = self.wb.active
        ws.title = "Portfolio Database"
        num_cols = len(self.PORTFOLIO_HEADERS)

        # --- Banner Row ---
        ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=num_cols)
        banner_cell = ws.cell(
            row=1,
            column=1,
            value=(
                "VC PORTFOLIO FOUNDER AGE ANALYSIS  \u00b7  "
                f"Top {len(set(r[0] for r in rows if r[0]))} VCs  \u00b7  "
                f"AI/Tech  \u00b7  Exported {datetime.now().strftime('%Y-%m-%d')}"
            ),
        )
        banner_cell.font = FONT_BANNER
        banner_cell.fill = FILL_BANNER
        banner_cell.alignment = ALIGN_CENTER
        ws.row_dimensions[1].height = 36

        # --- Header Row ---
        for col_idx, header in enumerate(self.PORTFOLIO_HEADERS, start=1):
            self._apply_cell_style(
                ws, 2, col_idx, header,
                font=FONT_HEADER,
                fill=FILL_HEADER,
                alignment=ALIGN_CENTER,
            )
        ws.row_dimensions[2].height = 24

        # Freeze panes below header
        ws.freeze_panes = "A3"

        # Auto-filter on header row
        ws.auto_filter.ref = f"A2:{get_column_letter(num_cols)}2"

        # --- Data Rows ---
        for row_offset, row_data in enumerate(rows):
            row_num = row_offset + 3  # Data starts at row 3
            is_alt = row_offset % 2 == 1
            base_fill = FILL_ALT_ROW if is_alt else None

            for col_idx, value in enumerate(row_data, start=1):
                fill = base_fill

                # Special formatting for age columns
                if col_idx == 16:  # Age at Founding
                    age_fill = self._get_age_fill(value)
                    if age_fill:
                        fill = age_fill
                elif col_idx == 17:  # Current Age
                    age_fill = self._get_age_fill(value)
                    if age_fill:
                        fill = age_fill
                elif col_idx == 18:  # Age Confidence
                    conf_fill = self._get_confidence_fill(value)
                    if conf_fill:
                        fill = conf_fill

                # Number formatting
                num_fmt = None
                alignment = ALIGN_LEFT
                if col_idx in (7, 12, 13, 16, 17):  # Numeric columns
                    alignment = ALIGN_CENTER
                    num_fmt = "0"
                elif col_idx in (20,):  # Source / Notes - wrap text
                    alignment = ALIGN_WRAP

                self._apply_cell_style(
                    ws, row_num, col_idx, value,
                    fill=fill,
                    alignment=alignment,
                    number_format=num_fmt,
                )

        # --- Column Widths ---
        for col_idx, width in enumerate(self.PORTFOLIO_WIDTHS, start=1):
            ws.column_dimensions[get_column_letter(col_idx)].width = width

        logger.info(f"  Portfolio Database: {len(rows)} rows written")

    def write_analysis_dashboard(self, assembler: DataAssembler) -> None:
        """Write the Analysis Dashboard sheet."""
        ws = self.wb.create_sheet("Analysis Dashboard")
        num_cols = 14

        current_row = 1

        # === Banner ===
        ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=num_cols)
        banner = ws.cell(
            row=1, column=1,
            value=(
                "FOUNDER AGE ANALYSIS DASHBOARD  \u00b7  "
                "ALL 20 VCs  \u00b7  "
                "Do VCs Back Young or Experienced Founders?"
            ),
        )
        banner.font = FONT_BANNER
        banner.fill = FILL_BANNER
        banner.alignment = ALIGN_CENTER
        ws.row_dimensions[1].height = 36
        current_row = 3

        # === Section 1: Avg Age by VC Firm ===
        ws.merge_cells(start_row=current_row, start_column=1, end_row=current_row, end_column=5)
        section = ws.cell(
            row=current_row, column=1,
            value="AVG FOUNDER AGE AT FOUNDING  \u00b7  by VC Firm",
        )
        section.font = FONT_SECTION
        section.fill = FILL_SECTION
        current_row += 1

        # Headers
        vc_headers = ["VC Firm", "# Companies", "Avg Age at Founding", "Interpretation"]
        for col_idx, h in enumerate(vc_headers, start=1):
            self._apply_cell_style(ws, current_row, col_idx, h, font=FONT_HEADER, fill=FILL_HEADER)
        current_row += 1

        # VC stats data
        vc_stats = assembler.compute_vc_stats()
        for stat in vc_stats:
            self._apply_cell_style(ws, current_row, 1, stat["name"], font=FONT_DATA_BOLD)
            self._apply_cell_style(ws, current_row, 2, stat["company_count"], alignment=ALIGN_CENTER)
            self._apply_cell_style(
                ws, current_row, 3, stat["avg_age"],
                alignment=ALIGN_CENTER,
                number_format="0.0",
            )
            self._apply_cell_style(ws, current_row, 4, "")  # Interpretation left blank
            current_row += 1

        # Totals row
        all_ages = [s["avg_age"] for s in vc_stats if s["avg_age"]]
        total_companies = sum(s["company_count"] for s in vc_stats)
        grand_avg = sum(all_ages) / len(all_ages) if all_ages else 0
        self._apply_cell_style(ws, current_row, 1, "ALL VCs", font=FONT_DATA_BOLD)
        self._apply_cell_style(ws, current_row, 2, total_companies, alignment=ALIGN_CENTER, font=FONT_DATA_BOLD)
        self._apply_cell_style(
            ws, current_row, 3, grand_avg,
            alignment=ALIGN_CENTER,
            number_format="0.0",
            font=FONT_DATA_BOLD,
        )
        self._apply_cell_style(ws, current_row, 4, "Portfolio-wide average", font=FONT_DATA_BOLD)
        current_row += 3

        # === Section 2: Age Bucket Distribution ===
        ws.merge_cells(start_row=current_row, start_column=1, end_row=current_row, end_column=4)
        section = ws.cell(
            row=current_row, column=1,
            value="FOUNDER AGE BUCKET DISTRIBUTION  \u00b7  at Time of Founding (all VCs)",
        )
        section.font = FONT_SECTION
        section.fill = FILL_SECTION
        current_row += 1

        bucket_headers = ["Age Bucket", "Description", "Count", "% of Total"]
        for col_idx, h in enumerate(bucket_headers, start=1):
            self._apply_cell_style(ws, current_row, col_idx, h, font=FONT_HEADER, fill=FILL_HEADER)
        current_row += 1

        buckets = assembler.compute_age_buckets()
        for bucket in buckets:
            self._apply_cell_style(ws, current_row, 1, bucket["bucket"], font=FONT_DATA_BOLD)
            self._apply_cell_style(ws, current_row, 2, bucket["description"])
            self._apply_cell_style(ws, current_row, 3, bucket["count"], alignment=ALIGN_CENTER)
            self._apply_cell_style(
                ws, current_row, 4, bucket["percentage"],
                alignment=ALIGN_CENTER,
                number_format="0.0%",
            )
            current_row += 1

        current_row += 2

        # === Section 3: Region Analysis ===
        ws.merge_cells(start_row=current_row, start_column=1, end_row=current_row, end_column=4)
        section = ws.cell(
            row=current_row, column=1,
            value="REGION ANALYSIS  \u00b7  Avg Age at Founding by Geography",
        )
        section.font = FONT_SECTION
        section.fill = FILL_SECTION
        current_row += 1

        region_headers = ["Region", "Count", "Avg Age at Founding", "Trend Insight"]
        for col_idx, h in enumerate(region_headers, start=1):
            self._apply_cell_style(ws, current_row, col_idx, h, font=FONT_HEADER, fill=FILL_HEADER)
        current_row += 1

        region_stats = assembler.compute_region_stats()
        for stat in region_stats:
            self._apply_cell_style(ws, current_row, 1, stat["region"], font=FONT_DATA_BOLD)
            self._apply_cell_style(ws, current_row, 2, stat["count"], alignment=ALIGN_CENTER)
            self._apply_cell_style(
                ws, current_row, 3, stat["avg_age"],
                alignment=ALIGN_CENTER,
                number_format="0.0",
            )
            self._apply_cell_style(ws, current_row, 4, "")
            current_row += 1

        current_row += 2

        # === Section 4: Prior Founder vs First-Time ===
        ws.merge_cells(start_row=current_row, start_column=1, end_row=current_row, end_column=4)
        section = ws.cell(
            row=current_row, column=1,
            value="PRIOR FOUNDER vs. FIRST-TIME  \u00b7  Age & Conviction Split",
        )
        section.font = FONT_SECTION
        section.fill = FILL_SECTION
        current_row += 1

        prior_headers = ["Founder Type", "Count", "Avg Age at Founding", "Insight"]
        for col_idx, h in enumerate(prior_headers, start=1):
            self._apply_cell_style(ws, current_row, col_idx, h, font=FONT_HEADER, fill=FILL_HEADER)
        current_row += 1

        prior_stats = assembler.compute_prior_founder_stats()
        for stat in prior_stats:
            self._apply_cell_style(ws, current_row, 1, stat["type"], font=FONT_DATA_BOLD)
            self._apply_cell_style(ws, current_row, 2, stat["count"], alignment=ALIGN_CENTER)
            self._apply_cell_style(
                ws, current_row, 3, stat["avg_age"],
                alignment=ALIGN_CENTER,
                number_format="0.0",
            )
            self._apply_cell_style(ws, current_row, 4, "")
            current_row += 1

        current_row += 2

        # === Section 5: Confidence Breakdown ===
        ws.merge_cells(start_row=current_row, start_column=1, end_row=current_row, end_column=4)
        section = ws.cell(
            row=current_row, column=1,
            value="AGE INFERENCE CONFIDENCE BREAKDOWN  \u00b7  Data Quality Check",
        )
        section.font = FONT_SECTION
        section.fill = FILL_SECTION
        current_row += 1

        conf_headers = ["Confidence Level", "Count", "% of Total", "What It Means"]
        for col_idx, h in enumerate(conf_headers, start=1):
            self._apply_cell_style(ws, current_row, col_idx, h, font=FONT_HEADER, fill=FILL_HEADER)
        current_row += 1

        conf_stats = assembler.compute_confidence_stats()
        for stat in conf_stats:
            conf_fill = self._get_confidence_fill(stat["level"])
            self._apply_cell_style(ws, current_row, 1, stat["level"], font=FONT_DATA_BOLD, fill=conf_fill)
            self._apply_cell_style(ws, current_row, 2, stat["count"], alignment=ALIGN_CENTER)
            self._apply_cell_style(
                ws, current_row, 3, stat["percentage"],
                alignment=ALIGN_CENTER,
                number_format="0.0%",
            )
            self._apply_cell_style(ws, current_row, 4, stat["description"])
            current_row += 1

        current_row += 2

        # === Footer / Methodology ===
        ws.merge_cells(start_row=current_row, start_column=1, end_row=current_row, end_column=num_cols)
        footer1 = ws.cell(
            row=current_row, column=1,
            value=(
                "AGE HEATMAP IN PORTFOLIO DATABASE:  "
                "Young (<25) -> Mid (35) -> Veteran (55+)   |   "
                "CONFIDENCE:  High = Wikipedia/stated age   "
                "Medium = LinkedIn grad year   Low = Pattern-inference"
            ),
        )
        footer1.font = FONT_FOOTER
        footer1.alignment = ALIGN_WRAP
        current_row += 1

        ws.merge_cells(start_row=current_row, start_column=1, end_row=current_row, end_column=num_cols)
        footer2 = ws.cell(
            row=current_row, column=1,
            value=(
                "METHODOLOGY: Age triangulated via: (1) LinkedIn education -> "
                "birth yr = grad yr - 22  (2) Career timeline corroboration  "
                "(3) Public media (Forbes, Wikipedia, press stating age explicitly)  "
                "(4) Pattern inference on role seniority.  "
                f"Age at Founding = Founded Year - Est. Birth Year.  "
                f"Exported {datetime.now().strftime('%Y-%m-%d %H:%M')} by Meridian."
            ),
        )
        footer2.font = FONT_FOOTER
        footer2.alignment = ALIGN_WRAP

        # Column widths for dashboard
        dashboard_widths = [25, 15, 20, 50] + [12] * 10
        for col_idx, width in enumerate(dashboard_widths, start=1):
            if col_idx <= num_cols:
                ws.column_dimensions[get_column_letter(col_idx)].width = width

        logger.info(f"  Analysis Dashboard: written to row {current_row}")

    def save(self) -> str:
        """Save the workbook and return the output path."""
        self.wb.save(str(self.output_path))
        logger.info(f"Saved: {self.output_path}")
        return str(self.output_path)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Export Meridian data to a formatted Excel workbook."
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Output file path (default: exports/vc_analysis_YYYYMMDD.xlsx).",
    )
    parser.add_argument(
        "--from-json",
        default=None,
        metavar="DIR",
        help="Read from JSON files (produced by seed.py --local-json) instead of Supabase.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose (DEBUG) logging.",
    )

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Determine output path
    if args.output:
        output_path = args.output
    else:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = f"exports/vc_analysis_{timestamp}.xlsx"

    start_time = datetime.now()
    logger.info("=" * 60)
    logger.info("Meridian Excel Exporter")
    logger.info("=" * 60)

    try:
        # Step 1: Fetch data
        if args.from_json:
            fetcher = JsonFetcher(args.from_json)
        else:
            fetcher = SupabaseFetcher()

        data = fetcher.fetch_all()

        # Step 2: Assemble data
        logger.info("Assembling data...")
        assembler = DataAssembler(data)
        portfolio_rows = assembler.assemble_portfolio_rows()
        logger.info(f"  Assembled {len(portfolio_rows)} portfolio rows")

        # Step 3: Write Excel
        logger.info("Writing Excel workbook...")
        writer = ExcelWriter(output_path)
        writer.write_portfolio_sheet(portfolio_rows)
        writer.write_analysis_dashboard(assembler)
        saved_path = writer.save()

        elapsed = (datetime.now() - start_time).total_seconds()
        logger.info(f"Export complete in {elapsed:.1f}s: {saved_path}")

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
