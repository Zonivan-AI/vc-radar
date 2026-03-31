"""
Phase 5: Compute derived VC intelligence from portfolio data.

Calculates per-VC metrics like sector distribution, stage focus,
average founding year, geographic spread, and portfolio size.
Stores results in vc_firms table fields or a separate analytics table.

Usage:
    python -m pipeline.compute_vc_intelligence
    python -m pipeline.compute_vc_intelligence --dry-run
"""

from __future__ import annotations

import argparse
import json
import os
from collections import Counter
from pathlib import Path

from dotenv import load_dotenv
from supabase import create_client

_env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(_env_path)


def main():
    parser = argparse.ArgumentParser(description="Compute derived VC intelligence")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    sb = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_ROLE_KEY"])

    # Load all investments
    print("Loading investments...")
    investments = []
    offset = 0
    while True:
        batch = sb.table("investments").select("vc_id,company_id,stage,lead_investor").range(offset, offset + 999).execute()
        if not batch.data:
            break
        investments.extend(batch.data)
        if len(batch.data) < 1000:
            break
        offset += 1000
    print(f"  {len(investments)} investments loaded")

    # Load all companies
    print("Loading companies...")
    companies = {}
    offset = 0
    while True:
        batch = sb.table("portfolio_companies").select(
            "id,sector,stage,founded_year,city,country"
        ).range(offset, offset + 999).execute()
        if not batch.data:
            break
        for c in batch.data:
            companies[c["id"]] = c
        if len(batch.data) < 1000:
            break
        offset += 1000
    print(f"  {len(companies)} companies loaded")

    # Load VCs
    print("Loading VCs...")
    vcs = []
    offset = 0
    while True:
        batch = sb.table("vc_firms").select("id,name,slug,focus_sectors,fund_stage").range(offset, offset + 999).execute()
        if not batch.data:
            break
        vcs.extend(batch.data)
        if len(batch.data) < 1000:
            break
        offset += 1000
    print(f"  {len(vcs)} VCs loaded")

    # Build VC -> companies mapping
    vc_companies = {}
    for inv in investments:
        vc_id = inv["vc_id"]
        cid = inv["company_id"]
        if vc_id not in vc_companies:
            vc_companies[vc_id] = []
        if cid in companies:
            vc_companies[vc_id].append(companies[cid])

    # Compute intelligence per VC
    updated = 0
    for vc in vcs:
        vc_id = vc["id"]
        portfolio = vc_companies.get(vc_id, [])
        if not portfolio:
            continue

        # Sector distribution
        sectors = Counter(c.get("sector", "Other") for c in portfolio if c.get("sector"))
        top_sectors = [s for s, _ in sectors.most_common(5)]

        # Stage distribution
        stages = Counter(c.get("stage") for c in portfolio if c.get("stage"))
        top_stages = [s for s, _ in stages.most_common(3)]

        # Geographic spread
        countries = Counter(c.get("country") for c in portfolio if c.get("country"))
        top_countries = [c for c, _ in countries.most_common(3)]

        # Founded year stats
        years = [c["founded_year"] for c in portfolio if c.get("founded_year")]
        avg_year = round(sum(years) / len(years)) if years else None
        recent_count = sum(1 for y in years if y >= 2020)

        # Update focus_sectors if currently empty
        current_sectors = vc.get("focus_sectors") or []
        update = {}

        if not current_sectors and top_sectors:
            update["focus_sectors"] = top_sectors

        # Update fund_stage if currently empty
        current_stages = vc.get("fund_stage") or []
        if not current_stages and top_stages:
            update["fund_stage"] = top_stages

        if not update:
            continue

        if args.dry_run:
            print(f"  [DRY] {vc['name']}: portfolio={len(portfolio)} "
                  f"sectors={top_sectors[:3]} stages={top_stages[:2]} "
                  f"countries={top_countries[:2]}")
            continue

        try:
            sb.table("vc_firms").update(update).eq("id", vc_id).execute()
            updated += 1
        except Exception as e:
            print(f"  ERROR {vc['name']}: {e}")

    print(f"\n{'[DRY RUN] ' if args.dry_run else ''}Updated {updated} VCs with derived intelligence")

    # Print summary
    total_with_portfolio = sum(1 for vc in vcs if vc["id"] in vc_companies)
    print(f"\nSummary:")
    print(f"  VCs with portfolio data: {total_with_portfolio}/{len(vcs)}")
    print(f"  VCs updated: {updated}")

    # Refresh materialized views
    if not args.dry_run:
        try:
            sb.rpc("refresh_materialized_views", {}).execute()
            print("  Materialized views refreshed")
        except Exception:
            pass


if __name__ == "__main__":
    main()
