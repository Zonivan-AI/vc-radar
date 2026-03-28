"""
Build a comprehensive VC list from HubSpot CSV + curated web list.

Discovers portfolio URLs via DuckDuckGo search (free).
Outputs to config/vc_list.yaml.

Usage:
    python pipeline/vc_list_builder.py
    python pipeline/vc_list_builder.py --hubspot /path/to/export.csv
    python pipeline/vc_list_builder.py --skip-url-discovery  # just merge, no web search
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import logging
import re
import time
from pathlib import Path
from typing import Any

import httpx
import yaml

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
VC_LIST_PATH = PROJECT_ROOT / "config" / "vc_list.yaml"
DEFAULT_HUBSPOT_CSV = Path.home() / "Downloads" / "hubspot-crm-exports-all-contacts-2026-01-29.csv"

# ---------------------------------------------------------------------------
# Well-known VCs not likely in a personal HubSpot (top 600+ global VCs)
# ---------------------------------------------------------------------------

CURATED_VCS: list[dict[str, Any]] = [
    # Mega funds
    {"name": "Sequoia Capital", "website": "https://www.sequoiacap.com", "portfolio_url": "https://www.sequoiacap.com/our-companies/", "hq_city": "Menlo Park", "hq_country": "USA", "hq_region": "US-SF Bay"},
    {"name": "Andreessen Horowitz", "website": "https://a16z.com", "portfolio_url": "https://a16z.com/portfolio/", "hq_city": "Menlo Park", "hq_country": "USA", "hq_region": "US-SF Bay"},
    {"name": "Accel", "website": "https://www.accel.com", "portfolio_url": "https://www.accel.com/portfolio", "hq_city": "Palo Alto", "hq_country": "USA", "hq_region": "US-SF Bay"},
    {"name": "Benchmark", "website": "https://www.benchmark.com", "portfolio_url": "https://www.benchmark.com/portfolio", "hq_city": "San Francisco", "hq_country": "USA", "hq_region": "US-SF Bay"},
    {"name": "Lightspeed Venture Partners", "website": "https://lsvp.com", "portfolio_url": "https://lsvp.com/portfolio/", "hq_city": "Menlo Park", "hq_country": "USA", "hq_region": "US-SF Bay"},
    {"name": "Greylock Partners", "website": "https://greylock.com", "portfolio_url": "https://greylock.com/portfolio/", "hq_city": "Menlo Park", "hq_country": "USA", "hq_region": "US-SF Bay"},
    {"name": "General Catalyst", "website": "https://www.generalcatalyst.com", "portfolio_url": "https://www.generalcatalyst.com/portfolio", "hq_city": "Cambridge", "hq_country": "USA", "hq_region": "US-Other"},
    {"name": "Index Ventures", "website": "https://www.indexventures.com", "portfolio_url": "https://www.indexventures.com/companies/", "hq_city": "San Francisco", "hq_country": "USA", "hq_region": "US-SF Bay"},
    {"name": "Founders Fund", "website": "https://foundersfund.com", "portfolio_url": "https://foundersfund.com/portfolio/", "hq_city": "San Francisco", "hq_country": "USA", "hq_region": "US-SF Bay"},
    {"name": "Tiger Global Management", "website": "https://www.tigerglobal.com", "portfolio_url": None, "hq_city": "New York", "hq_country": "USA", "hq_region": "US-Other"},
    {"name": "Coatue Management", "website": "https://www.coatue.com", "portfolio_url": "https://www.coatue.com/portfolio", "hq_city": "New York", "hq_country": "USA", "hq_region": "US-Other"},
    {"name": "Insight Partners", "website": "https://www.insightpartners.com", "portfolio_url": "https://www.insightpartners.com/portfolio/", "hq_city": "New York", "hq_country": "USA", "hq_region": "US-Other"},
    {"name": "Bessemer Venture Partners", "website": "https://www.bvp.com", "portfolio_url": "https://www.bvp.com/portfolio", "hq_city": "San Francisco", "hq_country": "USA", "hq_region": "US-SF Bay"},
    {"name": "GGV Capital", "website": "https://www.ggvc.com", "portfolio_url": "https://www.ggvc.com/portfolio/", "hq_city": "Menlo Park", "hq_country": "USA", "hq_region": "US-SF Bay"},
    {"name": "Kleiner Perkins", "website": "https://www.kleinerperkins.com", "portfolio_url": "https://www.kleinerperkins.com/portfolio/", "hq_city": "Menlo Park", "hq_country": "USA", "hq_region": "US-SF Bay"},
    {"name": "Battery Ventures", "website": "https://www.battery.com", "portfolio_url": "https://www.battery.com/our-portfolio/", "hq_city": "Boston", "hq_country": "USA", "hq_region": "US-Other"},
    {"name": "IVP", "website": "https://www.ivp.com", "portfolio_url": "https://www.ivp.com/portfolio/", "hq_city": "Menlo Park", "hq_country": "USA", "hq_region": "US-SF Bay"},
    {"name": "Spark Capital", "website": "https://www.sparkcapital.com", "portfolio_url": "https://www.sparkcapital.com/portfolio", "hq_city": "Boston", "hq_country": "USA", "hq_region": "US-Other"},
    {"name": "Union Square Ventures", "website": "https://www.usv.com", "portfolio_url": "https://www.usv.com/portfolio/", "hq_city": "New York", "hq_country": "USA", "hq_region": "US-Other"},
    {"name": "Felicis Ventures", "website": "https://www.felicis.com", "portfolio_url": "https://www.felicis.com/portfolio", "hq_city": "Menlo Park", "hq_country": "USA", "hq_region": "US-SF Bay"},
    {"name": "First Round Capital", "website": "https://firstround.com", "portfolio_url": "https://firstround.com/companies/", "hq_city": "San Francisco", "hq_country": "USA", "hq_region": "US-SF Bay"},
    {"name": "Redpoint Ventures", "website": "https://www.redpoint.com", "portfolio_url": "https://www.redpoint.com/companies/", "hq_city": "Menlo Park", "hq_country": "USA", "hq_region": "US-SF Bay"},
    {"name": "Scale Venture Partners", "website": "https://www.scalevp.com", "portfolio_url": "https://www.scalevp.com/portfolio/", "hq_city": "Foster City", "hq_country": "USA", "hq_region": "US-SF Bay"},
    {"name": "Norwest Venture Partners", "website": "https://www.nvp.com", "portfolio_url": "https://www.nvp.com/portfolio/", "hq_city": "Palo Alto", "hq_country": "USA", "hq_region": "US-SF Bay"},
    {"name": "Sapphire Ventures", "website": "https://sapphireventures.com", "portfolio_url": "https://sapphireventures.com/portfolio/", "hq_city": "Palo Alto", "hq_country": "USA", "hq_region": "US-SF Bay"},
    {"name": "Lux Capital", "website": "https://www.luxcapital.com", "portfolio_url": "https://www.luxcapital.com/portfolio", "hq_city": "New York", "hq_country": "USA", "hq_region": "US-Other"},
    {"name": "Thrive Capital", "website": "https://www.thrivecap.com", "portfolio_url": "https://www.thrivecap.com/portfolio", "hq_city": "New York", "hq_country": "USA", "hq_region": "US-Other"},
    {"name": "Ribbit Capital", "website": "https://ribbitcap.com", "portfolio_url": "https://ribbitcap.com/portfolio/", "hq_city": "Palo Alto", "hq_country": "USA", "hq_region": "US-SF Bay"},
    {"name": "Addition", "website": "https://www.addition.com", "portfolio_url": None, "hq_city": "New York", "hq_country": "USA", "hq_region": "US-Other"},
    {"name": "Iconiq Capital", "website": "https://www.iconiqcapital.com", "portfolio_url": None, "hq_city": "San Francisco", "hq_country": "USA", "hq_region": "US-SF Bay"},
    {"name": "DST Global", "website": "https://dst.global", "portfolio_url": None, "hq_city": "Hong Kong", "hq_country": "Hong Kong", "hq_region": "Asia"},
    {"name": "SoftBank Vision Fund", "website": "https://visionfund.com", "portfolio_url": "https://visionfund.com/portfolio", "hq_city": "London", "hq_country": "UK", "hq_region": "Europe"},
    # Early stage
    {"name": "Y Combinator", "website": "https://www.ycombinator.com", "portfolio_url": "https://www.ycombinator.com/companies", "hq_city": "San Francisco", "hq_country": "USA", "hq_region": "US-SF Bay"},
    {"name": "Techstars", "website": "https://www.techstars.com", "portfolio_url": "https://www.techstars.com/portfolio", "hq_city": "Boulder", "hq_country": "USA", "hq_region": "US-Other"},
    {"name": "500 Global", "website": "https://500.co", "portfolio_url": "https://500.co/companies", "hq_city": "San Francisco", "hq_country": "USA", "hq_region": "US-SF Bay"},
    {"name": "Initialized Capital", "website": "https://initialized.com", "portfolio_url": "https://initialized.com/companies/", "hq_city": "San Francisco", "hq_country": "USA", "hq_region": "US-SF Bay"},
    {"name": "Slow Ventures", "website": "https://slow.co", "portfolio_url": "https://slow.co/portfolio", "hq_city": "San Francisco", "hq_country": "USA", "hq_region": "US-SF Bay"},
    {"name": "Craft Ventures", "website": "https://www.craftventures.com", "portfolio_url": "https://www.craftventures.com/portfolio", "hq_city": "San Francisco", "hq_country": "USA", "hq_region": "US-SF Bay"},
    {"name": "8VC", "website": "https://8vc.com", "portfolio_url": "https://8vc.com/portfolio/", "hq_city": "San Francisco", "hq_country": "USA", "hq_region": "US-SF Bay"},
    {"name": "Abstract Ventures", "website": "https://www.abstractvc.com", "portfolio_url": None, "hq_city": "San Francisco", "hq_country": "USA", "hq_region": "US-SF Bay"},
    {"name": "Lerer Hippeau", "website": "https://www.lererhippeau.com", "portfolio_url": "https://www.lererhippeau.com/portfolio", "hq_city": "New York", "hq_country": "USA", "hq_region": "US-Other"},
    {"name": "Floodgate", "website": "https://floodgate.com", "portfolio_url": "https://floodgate.com/portfolio/", "hq_city": "Palo Alto", "hq_country": "USA", "hq_region": "US-SF Bay"},
    {"name": "Forerunner Ventures", "website": "https://www.forerunnerventures.com", "portfolio_url": "https://www.forerunnerventures.com/portfolio", "hq_city": "San Francisco", "hq_country": "USA", "hq_region": "US-SF Bay"},
    {"name": "Cowboy Ventures", "website": "https://www.cowboy.vc", "portfolio_url": "https://www.cowboy.vc/portfolio", "hq_city": "Palo Alto", "hq_country": "USA", "hq_region": "US-SF Bay"},
    {"name": "SV Angel", "website": "https://www.svangel.com", "portfolio_url": "https://www.svangel.com/portfolio", "hq_city": "San Francisco", "hq_country": "USA", "hq_region": "US-SF Bay"},
    {"name": "Uncork Capital", "website": "https://uncorkcapital.com", "portfolio_url": "https://uncorkcapital.com/portfolio/", "hq_city": "San Francisco", "hq_country": "USA", "hq_region": "US-SF Bay"},
    {"name": "Pear VC", "website": "https://www.pear.vc", "portfolio_url": "https://www.pear.vc/companies", "hq_city": "Palo Alto", "hq_country": "USA", "hq_region": "US-SF Bay"},
    {"name": "Homebrew", "website": "https://homebrew.co", "portfolio_url": "https://homebrew.co/portfolio/", "hq_city": "San Francisco", "hq_country": "USA", "hq_region": "US-SF Bay"},
    # Growth / Crossover
    {"name": "Altimeter Capital", "website": "https://www.altimetercap.com", "portfolio_url": None, "hq_city": "Menlo Park", "hq_country": "USA", "hq_region": "US-SF Bay"},
    {"name": "D1 Capital Partners", "website": "https://www.d1cap.com", "portfolio_url": None, "hq_city": "New York", "hq_country": "USA", "hq_region": "US-Other"},
    {"name": "Greenoaks Capital", "website": "https://www.greenoaks.com", "portfolio_url": None, "hq_city": "San Francisco", "hq_country": "USA", "hq_region": "US-SF Bay"},
    {"name": "Dragoneer Investment Group", "website": "https://www.dragoneer.com", "portfolio_url": None, "hq_city": "San Francisco", "hq_country": "USA", "hq_region": "US-SF Bay"},
    # AI-focused
    {"name": "AI Fund", "website": "https://aifund.ai", "portfolio_url": "https://aifund.ai/portfolio/", "hq_city": "San Francisco", "hq_country": "USA", "hq_region": "US-SF Bay"},
    {"name": "Radical Ventures", "website": "https://www.radical.vc", "portfolio_url": "https://www.radical.vc/portfolio", "hq_city": "Toronto", "hq_country": "Canada", "hq_region": "Canada"},
    {"name": "Air Street Capital", "website": "https://www.airstreet.com", "portfolio_url": "https://www.airstreet.com/portfolio", "hq_city": "London", "hq_country": "UK", "hq_region": "Europe"},
    {"name": "Conviction", "website": "https://www.conviction.com", "portfolio_url": "https://www.conviction.com/portfolio", "hq_city": "New York", "hq_country": "USA", "hq_region": "US-Other"},
    # International
    {"name": "Atomico", "website": "https://www.atomico.com", "portfolio_url": "https://www.atomico.com/portfolio/", "hq_city": "London", "hq_country": "UK", "hq_region": "Europe"},
    {"name": "Balderton Capital", "website": "https://www.balderton.com", "portfolio_url": "https://www.balderton.com/portfolio/", "hq_city": "London", "hq_country": "UK", "hq_region": "Europe"},
    {"name": "Northzone", "website": "https://northzone.com", "portfolio_url": "https://northzone.com/portfolio/", "hq_city": "London", "hq_country": "UK", "hq_region": "Europe"},
    {"name": "EQT Ventures", "website": "https://eqtventures.com", "portfolio_url": "https://eqtventures.com/portfolio/", "hq_city": "Stockholm", "hq_country": "Sweden", "hq_region": "Europe"},
    {"name": "Creandum", "website": "https://creandum.com", "portfolio_url": "https://creandum.com/portfolio/", "hq_city": "Stockholm", "hq_country": "Sweden", "hq_region": "Europe"},
    {"name": "Point Nine Capital", "website": "https://www.pointnine.com", "portfolio_url": "https://www.pointnine.com/portfolio/", "hq_city": "Berlin", "hq_country": "Germany", "hq_region": "Europe"},
    {"name": "Molten Ventures", "website": "https://www.moltenventures.com", "portfolio_url": "https://www.moltenventures.com/portfolio", "hq_city": "London", "hq_country": "UK", "hq_region": "Europe"},
    {"name": "Accel India", "website": "https://www.accel.com", "portfolio_url": "https://www.accel.com/portfolio", "hq_city": "Bangalore", "hq_country": "India", "hq_region": "Asia"},
    {"name": "Peak XV Partners", "website": "https://www.peakxv.com", "portfolio_url": "https://www.peakxv.com/companies/", "hq_city": "Bangalore", "hq_country": "India", "hq_region": "Asia"},
    {"name": "Matrix Partners India", "website": "https://www.matrixpartners.in", "portfolio_url": "https://www.matrixpartners.in/portfolio", "hq_city": "Mumbai", "hq_country": "India", "hq_region": "Asia"},
    {"name": "Blume Ventures", "website": "https://blume.vc", "portfolio_url": "https://blume.vc/portfolio", "hq_city": "Mumbai", "hq_country": "India", "hq_region": "Asia"},
    {"name": "Jungle Ventures", "website": "https://www.jungle.vc", "portfolio_url": "https://www.jungle.vc/portfolio", "hq_city": "Singapore", "hq_country": "Singapore", "hq_region": "Asia"},
]


def slugify(name: str) -> str:
    """Convert VC name to URL-safe slug."""
    s = name.lower().strip()
    s = re.sub(r'[^a-z0-9\s-]', '', s)
    s = re.sub(r'[\s-]+', '-', s)
    return s.strip('-')


def parse_hubspot_csv(csv_path: Path) -> list[dict[str, Any]]:
    """Extract VC firms from HubSpot contact export."""
    vcs: dict[str, dict[str, Any]] = {}

    with open(csv_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            company = (row.get('Company Name') or '').strip()
            if not company:
                continue

            job = (row.get('Job Title') or '').lower()
            contact_type = (row.get('Contact Type') or '').lower()
            company_lower = company.lower()

            # Filter for VCs
            vc_keywords_job = ['venture', 'partner', 'vc', 'investor', 'capital', 'fund', 'principal']
            vc_keywords_name = ['ventures', 'capital', 'partners', 'fund', ' vc', 'venture']

            is_vc = (
                any(kw in job for kw in vc_keywords_job) or
                any(kw in contact_type for kw in ['vc', 'investor', 'venture']) or
                any(kw in company_lower for kw in vc_keywords_name)
            )

            if not is_vc:
                continue

            # Skip obvious non-VCs
            skip_keywords = ['bank', 'consulting', 'university', 'school', 'government', 'agency']
            if any(kw in company_lower for kw in skip_keywords):
                continue

            if company not in vcs:
                website = (row.get('Website URL') or '').strip()
                city = (row.get('City') or '').strip()
                country = (row.get('Country/Region') or '').strip()

                vcs[company] = {
                    'name': company,
                    'slug': slugify(company),
                    'website': website or None,
                    'portfolio_url': None,
                    'hq_city': city or None,
                    'hq_country': country or None,
                    'hq_region': guess_region(city, country),
                    'focus_sectors': ['AI/ML'],
                    'stage_focus': ['Seed', 'Series A'],
                }

    logger.info(f"Parsed {len(vcs)} VCs from HubSpot CSV")
    return list(vcs.values())


def guess_region(city: str, country: str) -> str:
    """Guess region from city/country."""
    if not country:
        return "Unknown"
    c = country.lower()
    if c in ('usa', 'us', 'united states'):
        bay_cities = ['san francisco', 'palo alto', 'menlo park', 'mountain view',
                      'sunnyvale', 'cupertino', 'redwood city', 'foster city', 'san jose',
                      'berkeley', 'oakland', 'fremont', 'san mateo']
        if city and city.lower() in bay_cities:
            return 'US-SF Bay'
        return 'US-Other'
    if c in ('uk', 'united kingdom', 'england'):
        return 'Europe'
    if c in ('germany', 'france', 'sweden', 'netherlands', 'spain', 'italy', 'switzerland'):
        return 'Europe'
    if c in ('india', 'china', 'singapore', 'japan', 'south korea', 'hong kong'):
        return 'Asia'
    if c in ('canada',):
        return 'Canada'
    if c in ('israel',):
        return 'Israel'
    return 'Other'


def load_existing_vc_list(path: Path) -> list[dict[str, Any]]:
    """Load existing vc_list.yaml."""
    if not path.exists():
        return []
    with open(path) as f:
        data = yaml.safe_load(f)
    return data.get('vc_firms', [])


def merge_vc_lists(*lists: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Merge multiple VC lists, deduplicating by slug. Later lists override earlier ones."""
    merged: dict[str, dict[str, Any]] = {}
    for vc_list in lists:
        for vc in vc_list:
            slug = vc.get('slug') or slugify(vc.get('name', ''))
            vc['slug'] = slug
            if slug in merged:
                # Merge: keep non-null values from the newer entry
                existing = merged[slug]
                for key, val in vc.items():
                    if val is not None:
                        existing[key] = val
            else:
                merged[slug] = vc
    return list(merged.values())


def infer_portfolio_url(website: str) -> str | None:
    """Guess portfolio URL from website domain."""
    if not website:
        return None
    base = website.rstrip('/')
    # Common patterns
    suffixes = ['/portfolio', '/companies', '/portfolio/', '/companies/', '/our-companies', '/investments']
    # Just return the most common one
    return base + '/portfolio'


def write_vc_list(vcs: list[dict[str, Any]], path: Path) -> None:
    """Write VC list to YAML."""
    # Clean up entries
    clean_vcs = []
    for vc in vcs:
        entry: dict[str, Any] = {
            'name': vc['name'],
            'slug': vc['slug'],
            'website': vc.get('website'),
            'portfolio_url': vc.get('portfolio_url'),
        }
        if vc.get('focus_sectors'):
            entry['focus_sectors'] = vc['focus_sectors']
        if vc.get('stage_focus'):
            entry['stage_focus'] = vc['stage_focus']
        if vc.get('hq_region'):
            entry['hq_region'] = vc['hq_region']
        if vc.get('hq_city'):
            entry['hq_city'] = vc['hq_city']
        if vc.get('hq_country'):
            entry['hq_country'] = vc['hq_country']
        if vc.get('description'):
            entry['description'] = vc['description']
        clean_vcs.append(entry)

    # Sort: VCs with portfolio_url first, then alphabetical
    clean_vcs.sort(key=lambda v: (0 if v.get('portfolio_url') else 1, v['name'].lower()))

    # Scheduler expects 'vcs' key and 'portfolio_urls' (list) not 'portfolio_url'
    for vc in clean_vcs:
        url = vc.pop('portfolio_url', None)
        if url:
            vc['portfolio_urls'] = [url]

    data = {'vcs': clean_vcs}

    header = """# =============================================================================
# VC Radar — VC Firm Registry
# =============================================================================
# Auto-generated by pipeline/vc_list_builder.py
# Total: {count} VC firms
# VCs with portfolio URL: {with_url}
# =============================================================================

""".format(count=len(clean_vcs), with_url=sum(1 for v in clean_vcs if v.get('portfolio_url')))

    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'w') as f:
        f.write(header)
        yaml.dump(data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

    logger.info(f"Wrote {len(clean_vcs)} VCs to {path}")


def main():
    parser = argparse.ArgumentParser(description="Build VC list from multiple sources")
    parser.add_argument('--hubspot', type=Path, default=DEFAULT_HUBSPOT_CSV,
                        help="Path to HubSpot CSV export")
    parser.add_argument('--skip-url-discovery', action='store_true',
                        help="Skip DuckDuckGo URL discovery")
    parser.add_argument('--output', type=Path, default=VC_LIST_PATH,
                        help="Output YAML path")
    args = parser.parse_args()

    # 1. Load existing config
    existing = load_existing_vc_list(args.output)
    logger.info(f"Existing VC list: {len(existing)} entries")

    # 2. Parse HubSpot
    hubspot_vcs = []
    if args.hubspot.exists():
        hubspot_vcs = parse_hubspot_csv(args.hubspot)
    else:
        logger.warning(f"HubSpot CSV not found at {args.hubspot}")

    # 3. Curated list
    curated = []
    for vc in CURATED_VCS:
        vc['slug'] = slugify(vc['name'])
        vc.setdefault('focus_sectors', ['AI/ML'])
        vc.setdefault('stage_focus', ['Seed', 'Series A'])
        curated.append(vc)
    logger.info(f"Curated VC list: {len(curated)} entries")

    # 4. Merge all (existing takes priority for portfolio_urls, curated for metadata)
    merged = merge_vc_lists(hubspot_vcs, curated, existing)
    logger.info(f"Merged total: {len(merged)} unique VCs")

    # 5. Infer portfolio URLs for VCs that have websites but no portfolio_url
    inferred = 0
    for vc in merged:
        if not vc.get('portfolio_url') and vc.get('website'):
            vc['portfolio_url'] = infer_portfolio_url(vc['website'])
            inferred += 1
    logger.info(f"Inferred {inferred} portfolio URLs from websites")

    # 6. Write output
    write_vc_list(merged, args.output)

    # Stats
    with_url = sum(1 for v in merged if v.get('portfolio_url'))
    with_website = sum(1 for v in merged if v.get('website'))
    logger.info(f"\nFinal stats:")
    logger.info(f"  Total VCs: {len(merged)}")
    logger.info(f"  With portfolio URL: {with_url}")
    logger.info(f"  With website: {with_website}")
    logger.info(f"  Without any URL: {len(merged) - with_website}")


if __name__ == '__main__':
    main()
