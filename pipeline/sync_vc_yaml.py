"""
Phase 0A: Sync all VC data from vc_list.yaml to Supabase.

Fixes the bug where hq_city, hq_country, hq_region, and stage_focus
were never written to the database.

Usage:
    python -m pipeline.sync_vc_yaml
    python -m pipeline.sync_vc_yaml --dry-run
"""

import argparse
import os
import re
import yaml
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client

_env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(_env_path)

VC_LIST_PATH = Path(__file__).resolve().parent.parent / "config" / "vc_list.yaml"


def _generate_slug(name: str) -> str:
    slug = name.lower().strip()
    slug = re.sub(r"[^a-z0-9\s-]", "", slug)
    slug = re.sub(r"[\s]+", "-", slug)
    slug = re.sub(r"-+", "-", slug)
    return slug.strip("-")


def main():
    parser = argparse.ArgumentParser(description="Sync VC YAML data to Supabase")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    sb = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_ROLE_KEY"])

    with open(VC_LIST_PATH) as f:
        data = yaml.safe_load(f)

    vcs = data.get("vcs", [])
    print(f"Loaded {len(vcs)} VCs from YAML")

    # Get existing VCs from DB
    existing = sb.table("vc_firms").select("id,slug,name").execute()
    slug_to_id = {r["slug"]: r["id"] for r in existing.data}
    name_to_id = {r["name"]: r["id"] for r in existing.data}
    print(f"Found {len(slug_to_id)} existing VCs in DB")

    updated = 0
    inserted = 0
    skipped = 0

    for vc in vcs:
        name = vc.get("name", "")
        slug = vc.get("slug", _generate_slug(name))

        row = {
            "name": name,
            "slug": slug,
            "website": vc.get("website"),
            "fund_stage": vc.get("stage_focus", vc.get("fund_stage", [])),
            "focus_sectors": vc.get("focus_sectors", []),
            "hq_city": vc.get("hq_city"),
            "hq_country": vc.get("hq_country"),
            "hq_region": vc.get("hq_region"),
        }
        # Remove None values for cleaner upserts
        row = {k: v for k, v in row.items() if v is not None}

        vc_id = slug_to_id.get(slug) or name_to_id.get(name)

        if args.dry_run:
            action = "UPDATE" if vc_id else "INSERT"
            has_city = bool(vc.get("hq_city"))
            has_stage = bool(vc.get("stage_focus"))
            print(f"  [{action}] {name} | city={has_city} stage={has_stage}")
            continue

        try:
            if vc_id:
                update_data = {k: v for k, v in row.items() if k != "slug"}
                sb.table("vc_firms").update(update_data).eq("id", vc_id).execute()
                updated += 1
            else:
                result = sb.table("vc_firms").insert(row).execute()
                if result.data:
                    inserted += 1
                else:
                    skipped += 1
        except Exception as e:
            print(f"  ERROR: {name}: {e}")
            skipped += 1

    if not args.dry_run:
        print(f"\nDone: {updated} updated, {inserted} inserted, {skipped} skipped")
    else:
        print("\n[DRY RUN] No changes made")


if __name__ == "__main__":
    main()
