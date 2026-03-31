"""
Discover portfolio URLs for VCs that don't have them.

Three strategies:
1. For VCs with a website: probe common portfolio page paths
2. For VCs without: try common domain patterns (name.com, name.vc, etc.)
3. Fallback: use WebFetch or manual curation

Usage:
    python pipeline/url_discoverer.py                    # discover all missing
    python pipeline/url_discoverer.py --limit 50         # first 50 only
    python pipeline/url_discoverer.py --dry-run           # just show what would be updated
    python pipeline/url_discoverer.py --probe-only        # only probe VCs with known websites
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import re
import time
from pathlib import Path
from urllib.parse import urlparse

import httpx
import yaml
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
VC_LIST_PATH = PROJECT_ROOT / "config" / "vc_list.yaml"

# Common portfolio page suffixes (ordered by likelihood)
PORTFOLIO_PATHS = [
    "/portfolio",
    "/portfolio/",
    "/companies",
    "/companies/",
    "/our-companies",
    "/our-companies/",
    "/our-portfolio",
    "/our-portfolio/",
    "/investments",
    "/investments/",
    "/portfolio-companies",
]

# Common VC domain TLDs
DOMAIN_TLDS = [".com", ".vc", ".co", ".io", ".capital", ".ventures"]

# User agent
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


def name_to_domain_guesses(name: str) -> list[str]:
    """Generate likely domain names from a VC firm name."""
    # Clean name
    clean = name.lower().strip()
    # Remove common suffixes
    for suffix in [" ventures", " capital", " partners", " management", " fund",
                   " group", " labs", " studio", " vc", " investments"]:
        if clean.endswith(suffix):
            clean = clean[:-len(suffix)].strip()

    # Generate slug variants
    slug = re.sub(r'[^a-z0-9\s]', '', clean)
    slug_hyphen = re.sub(r'\s+', '-', slug).strip('-')
    slug_none = re.sub(r'\s+', '', slug)

    domains = set()
    for base in [slug_hyphen, slug_none]:
        if not base:
            continue
        for tld in DOMAIN_TLDS:
            domains.add(f"https://www.{base}{tld}")
            domains.add(f"https://{base}{tld}")

    # Also try the full name with common patterns
    full_slug = re.sub(r'[^a-z0-9\s]', '', name.lower())
    full_slug = re.sub(r'\s+', '', full_slug)
    if full_slug != slug_none:
        for tld in [".com", ".vc", ".co"]:
            domains.add(f"https://www.{full_slug}{tld}")
            domains.add(f"https://{full_slug}{tld}")

    return list(domains)


async def check_url_exists(client: httpx.AsyncClient, url: str) -> bool:
    """Check if a URL returns a valid response."""
    try:
        resp = await client.head(url, follow_redirects=True, timeout=8)
        return resp.status_code < 400
    except Exception:
        return False


async def probe_portfolio_url(client: httpx.AsyncClient, website: str) -> str | None:
    """Try common portfolio page paths on a known website."""
    base = website.rstrip("/")

    for path in PORTFOLIO_PATHS:
        url = base + path
        try:
            resp = await client.get(url, follow_redirects=True, timeout=10)
            if resp.status_code == 200:
                text = resp.text.lower()
                # Check for portfolio signals
                portfolio_signals = ["portfolio", "companies", "investments", "backed",
                                     "our companies", "portfolio companies", "invest"]
                if any(signal in text for signal in portfolio_signals) and len(text) > 1500:
                    return str(resp.url)  # Use final URL after redirects
        except Exception:
            continue

    return None


async def discover_website(client: httpx.AsyncClient, vc_name: str) -> str | None:
    """Try to discover a VC's website by guessing domain names."""
    guesses = name_to_domain_guesses(vc_name)

    # Try them concurrently in small batches
    for i in range(0, len(guesses), 4):
        batch = guesses[i:i+4]
        tasks = [check_url_exists(client, url) for url in batch]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for url, ok in zip(batch, results):
            if ok is True:
                return url

    return None


async def discover_urls(
    limit: int | None = None,
    dry_run: bool = False,
    probe_only: bool = False,
) -> None:
    """Main discovery loop."""
    # Load current config
    with open(VC_LIST_PATH) as f:
        data = yaml.safe_load(f)
    vcs = data.get("vcs", [])

    # Find VCs without portfolio URLs
    missing = [v for v in vcs if not v.get("portfolio_urls")]
    logger.info(f"Total VCs without portfolio URLs: {len(missing)}")

    if limit:
        missing = missing[:limit]
        logger.info(f"Processing first {limit}")

    # Split into with-website and without-website
    with_website = [v for v in missing if v.get("website")]
    without_website = [v for v in missing if not v.get("website")]

    logger.info(f"  With website (probe): {len(with_website)}")
    logger.info(f"  Without website (guess+probe): {len(without_website)}")

    found_count = 0
    website_found_count = 0
    updated_vcs = {v["slug"]: v for v in vcs}  # index by slug for updates

    async with httpx.AsyncClient(headers=HEADERS) as client:
        # Phase 1: Probe VCs that have websites
        logger.info("\n=== Phase 1: Probing known websites ===")
        for i, vc in enumerate(with_website):
            name = vc["name"]
            website = vc["website"]
            logger.info(f"[{i+1}/{len(with_website)}] Probing {name} ({website})")

            portfolio_url = await probe_portfolio_url(client, website)
            if portfolio_url:
                found_count += 1
                if not dry_run:
                    updated_vcs[vc["slug"]]["portfolio_urls"] = [portfolio_url]
                logger.info(f"  ✓ Found: {portfolio_url}")
            else:
                logger.info(f"  ✗ No portfolio page found")

            await asyncio.sleep(0.5)  # gentle rate limit

        if probe_only:
            logger.info(f"\n=== Results (probe only) ===")
            logger.info(f"Discovered {found_count} new portfolio URLs from {len(with_website)} VCs with websites")
        else:
            # Phase 2: Guess domains for VCs without websites
            logger.info(f"\n=== Phase 2: Guessing domains for {len(without_website)} VCs ===")
            for i, vc in enumerate(without_website):
                name = vc["name"]
                logger.info(f"[{i+1}/{len(without_website)}] Guessing domain for {name}")

                website = await discover_website(client, name)
                if website:
                    website_found_count += 1
                    if not dry_run:
                        updated_vcs[vc["slug"]]["website"] = website
                    logger.info(f"  ~ Found website: {website}")

                    # Now probe for portfolio page
                    portfolio_url = await probe_portfolio_url(client, website)
                    if portfolio_url:
                        found_count += 1
                        if not dry_run:
                            updated_vcs[vc["slug"]]["portfolio_urls"] = [portfolio_url]
                        logger.info(f"  ✓ Found portfolio: {portfolio_url}")
                else:
                    logger.info(f"  ✗ No website found")

                await asyncio.sleep(0.3)

            logger.info(f"\n=== Results ===")
            logger.info(f"Websites discovered: {website_found_count}")
            logger.info(f"Portfolio URLs discovered: {found_count}")

    if not dry_run and found_count > 0:
        # Write updated config
        updated_list = list(updated_vcs.values())
        updated_list.sort(key=lambda v: (0 if v.get("portfolio_urls") else 1, v["name"].lower()))
        data["vcs"] = updated_list

        with_url_count = sum(1 for v in updated_list if v.get("portfolio_urls"))
        header = f"""# =============================================================================
# VC Radar — VC Firm Registry
# =============================================================================
# Auto-updated by pipeline/url_discoverer.py
# Total: {len(updated_list)} VC firms
# VCs with portfolio URL: {with_url_count}
# =============================================================================

"""
        with open(VC_LIST_PATH, "w") as f:
            f.write(header)
            yaml.dump(data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

        logger.info(f"Updated {VC_LIST_PATH}")


def main():
    parser = argparse.ArgumentParser(description="Discover portfolio URLs for VCs")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of VCs to process")
    parser.add_argument("--dry-run", action="store_true", help="Don't write changes")
    parser.add_argument("--probe-only", action="store_true", help="Only probe VCs with known websites")
    args = parser.parse_args()

    asyncio.run(discover_urls(limit=args.limit, dry_run=args.dry_run, probe_only=args.probe_only))


if __name__ == "__main__":
    main()
