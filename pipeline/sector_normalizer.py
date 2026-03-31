"""
Phase 1: Normalize messy sector names into a clean taxonomy.

Consolidates duplicates like "AI/ML" vs "AI" vs "Artificial Intelligence"
into 12 canonical sectors.

Usage:
    python -m pipeline.sector_normalizer
    python -m pipeline.sector_normalizer --dry-run
"""

import argparse
import os
import re
from pathlib import Path
from collections import Counter
from dotenv import load_dotenv
from supabase import create_client

_env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(_env_path)

# ─── Canonical taxonomy ──────────────────────────────────────────────────────

CANONICAL_SECTORS = [
    "AI/ML",
    "Fintech",
    "Healthcare",
    "SaaS/Enterprise",
    "DeepTech/Hardware",
    "Climate/Energy",
    "Consumer",
    "Crypto/Web3",
    "Cybersecurity",
    "Edtech",
    "Real Estate/PropTech",
    "Other",
]

# ─── Static mapping (case-insensitive) ────────────────────────────────────────

_RAW_MAP = {
    # AI/ML
    "ai": "AI/ML", "ai/ml": "AI/ML", "ml": "AI/ML",
    "artificial intelligence": "AI/ML", "machine learning": "AI/ML",
    "generative ai": "AI/ML", "deep learning": "AI/ML",
    "data science": "AI/ML", "nlp": "AI/ML",
    "computer vision": "AI/ML", "robotics": "AI/ML",
    "autonomy": "AI/ML", "intelligent collaboration": "AI/ML",
    "automated workflows": "AI/ML",

    # Fintech
    "fintech": "Fintech", "financial technology": "Fintech",
    "financial services": "Fintech", "payments": "Fintech",
    "insurance": "Fintech", "insurtech": "Fintech",
    "banking": "Fintech", "neobank": "Fintech",
    "lending": "Fintech", "wealth management": "Fintech",
    "defi": "Fintech",

    # Healthcare
    "healthcare": "Healthcare", "health": "Healthcare",
    "healthtech": "Healthcare", "biotech": "Healthcare",
    "medtech": "Healthcare", "digital health": "Healthcare",
    "life sciences": "Healthcare", "pharma": "Healthcare",
    "genomics": "Healthcare", "therapeutics": "Healthcare",
    "mental health": "Healthcare",

    # SaaS/Enterprise
    "saas": "SaaS/Enterprise", "enterprise": "SaaS/Enterprise",
    "b2b": "SaaS/Enterprise", "b2b saas": "SaaS/Enterprise",
    "enterprise software": "SaaS/Enterprise", "developer tools": "SaaS/Enterprise",
    "devtools": "SaaS/Enterprise", "productivity": "SaaS/Enterprise",
    "collaboration": "SaaS/Enterprise", "hr tech": "SaaS/Enterprise",
    "martech": "SaaS/Enterprise", "sales tech": "SaaS/Enterprise",
    "b2b services": "SaaS/Enterprise", "platforms & infrastructure": "SaaS/Enterprise",
    "applications": "SaaS/Enterprise", "infrastructure": "SaaS/Enterprise",
    "scalable infrastructure": "SaaS/Enterprise",

    # DeepTech/Hardware
    "deeptech": "DeepTech/Hardware", "deep tech": "DeepTech/Hardware",
    "hardware": "DeepTech/Hardware", "semiconductors": "DeepTech/Hardware",
    "quantum computing": "DeepTech/Hardware", "space": "DeepTech/Hardware",
    "aerospace": "DeepTech/Hardware", "defense": "DeepTech/Hardware",
    "manufacturing": "DeepTech/Hardware", "3d printing": "DeepTech/Hardware",
    "iot": "DeepTech/Hardware", "chips": "DeepTech/Hardware",

    # Climate/Energy
    "climate": "Climate/Energy", "cleantech": "Climate/Energy",
    "climate tech": "Climate/Energy", "energy": "Climate/Energy",
    "sustainability": "Climate/Energy", "green energy": "Climate/Energy",
    "renewable energy": "Climate/Energy", "ev": "Climate/Energy",
    "electric vehicles": "Climate/Energy", "carbon": "Climate/Energy",
    "agtech": "Climate/Energy", "agriculture": "Climate/Energy",
    "food": "Climate/Energy", "foodtech": "Climate/Energy",

    # Consumer
    "consumer": "Consumer", "d2c": "Consumer", "dtc": "Consumer",
    "e-commerce": "Consumer", "ecommerce": "Consumer",
    "marketplace": "Consumer", "social": "Consumer",
    "gaming": "Consumer", "media": "Consumer",
    "entertainment": "Consumer", "travel": "Consumer",
    "brands & experiences": "Consumer", "creator economy": "Consumer",
    "fashion": "Consumer", "beauty": "Consumer",
    "fitness": "Consumer", "sports": "Consumer",

    # Crypto/Web3
    "crypto": "Crypto/Web3", "web3": "Crypto/Web3",
    "blockchain": "Crypto/Web3", "nft": "Crypto/Web3",
    "decentralized": "Crypto/Web3", "dao": "Crypto/Web3",

    # Cybersecurity
    "cybersecurity": "Cybersecurity", "security": "Cybersecurity",
    "infosec": "Cybersecurity", "information security": "Cybersecurity",
    "identity": "Cybersecurity", "privacy": "Cybersecurity",

    # Edtech
    "edtech": "Edtech", "education": "Edtech",
    "learning": "Edtech", "e-learning": "Edtech",

    # Real Estate/PropTech
    "real estate": "Real Estate/PropTech", "proptech": "Real Estate/PropTech",
    "property": "Real Estate/PropTech", "construction": "Real Estate/PropTech",
    "contech": "Real Estate/PropTech",

    # Logistics/Supply Chain → SaaS/Enterprise (B2B vertical)
    "logistics": "SaaS/Enterprise", "supply chain": "SaaS/Enterprise",
    "transportation": "SaaS/Enterprise", "mobility": "SaaS/Enterprise",
    "fleet": "SaaS/Enterprise",

    # Legal → SaaS/Enterprise
    "legaltech": "SaaS/Enterprise", "legal": "SaaS/Enterprise",
    "regtech": "SaaS/Enterprise", "compliance": "SaaS/Enterprise",

    # Additional common mappings
    "apps & services": "SaaS/Enterprise", "software infra & models": "SaaS/Enterprise",
    "data & analytics": "SaaS/Enterprise", "data analytics": "SaaS/Enterprise",
    "marketing technology": "SaaS/Enterprise", "marketing tech": "SaaS/Enterprise",
    "human resources technology": "SaaS/Enterprise", "hr/workforce": "SaaS/Enterprise",
    "information technology": "SaaS/Enterprise", "engineering": "DeepTech/Hardware",
    "industrials": "DeepTech/Hardware", "personal systems": "Consumer",
    "dex & trading": "Crypto/Web3", "custody & wallets": "Crypto/Web3",
    "layer 2": "Crypto/Web3", "asset management": "Fintech",
    "finance": "Fintech", "batteries": "Climate/Energy",
    "other impact": "Climate/Energy", "hospitality technology": "SaaS/Enterprise",
    "cloud": "SaaS/Enterprise", "api": "SaaS/Enterprise",
    "analytics": "SaaS/Enterprise", "database": "SaaS/Enterprise",
    "storage": "SaaS/Enterprise", "networking": "SaaS/Enterprise",
    "communication": "SaaS/Enterprise", "telecom": "SaaS/Enterprise",
    "adtech": "SaaS/Enterprise", "advertising": "SaaS/Enterprise",
}

# Build case-insensitive lookup
SECTOR_MAP = {k.lower().strip(): v for k, v in _RAW_MAP.items()}


def normalize_sector(raw: str) -> str:
    """Normalize a single sector string to canonical form."""
    if not raw:
        return "Other"
    key = raw.lower().strip()
    if key in SECTOR_MAP:
        return SECTOR_MAP[key]
    # Try partial matches
    for pattern, canonical in SECTOR_MAP.items():
        if pattern in key or key in pattern:
            return canonical
    return "Other"


def main():
    parser = argparse.ArgumentParser(description="Normalize company sectors")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    sb = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_ROLE_KEY"])

    # Fetch all distinct sectors
    all_companies = []
    batch_size = 1000
    offset = 0
    while True:
        batch = sb.table("portfolio_companies").select("id,sector").range(offset, offset + batch_size - 1).execute()
        if not batch.data:
            break
        all_companies.extend(batch.data)
        if len(batch.data) < batch_size:
            break
        offset += batch_size

    print(f"Loaded {len(all_companies)} companies")

    # Count raw sectors
    raw_sectors = Counter(c.get("sector") or "Unknown" for c in all_companies)
    print(f"\n{len(raw_sectors)} unique raw sectors")

    # Build normalization plan
    updates = {}  # raw_sector -> canonical_sector
    unmapped = []
    for raw, count in raw_sectors.most_common():
        canonical = normalize_sector(raw)
        if raw != canonical:
            updates[raw] = canonical
        if canonical == "Other" and raw not in ("Unknown", "Other", None, ""):
            unmapped.append((raw, count))

    print(f"\nMappings to apply: {len(updates)}")
    print(f"Unmapped sectors ({len(unmapped)}):")
    for raw, count in sorted(unmapped, key=lambda x: -x[1])[:20]:
        print(f"  {raw}: {count}")

    # Show canonical distribution
    canonical_counts = Counter()
    for c in all_companies:
        raw = c.get("sector") or "Unknown"
        canonical_counts[normalize_sector(raw)] += 1
    print(f"\nCanonical sector distribution:")
    for sector, count in canonical_counts.most_common():
        print(f"  {sector}: {count}")

    if args.dry_run:
        print("\n[DRY RUN] No changes made")
        return

    # Apply updates in batches by raw sector
    total_updated = 0
    for raw_sector, canonical in updates.items():
        if raw_sector == canonical:
            continue
        try:
            # Update all companies with this raw sector
            result = sb.table("portfolio_companies").update(
                {"sector": canonical}
            ).eq("sector", raw_sector).execute()
            count = len(result.data) if result.data else 0
            total_updated += count
            if count > 0:
                print(f"  '{raw_sector}' -> '{canonical}': {count} companies")
        except Exception as e:
            print(f"  ERROR updating '{raw_sector}': {e}")

    # Also normalize NULL/empty to "Other"
    try:
        result = sb.table("portfolio_companies").update(
            {"sector": "Other"}
        ).is_("sector", "null").execute()
        null_count = len(result.data) if result.data else 0
        total_updated += null_count
        print(f"  NULL -> 'Other': {null_count} companies")
    except Exception as e:
        print(f"  ERROR updating NULLs: {e}")

    print(f"\nDone: {total_updated} companies updated")


if __name__ == "__main__":
    main()
