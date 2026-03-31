#!/usr/bin/env python3
"""
Portfolio URL Discovery & Fixer

Uses Serper (Google Search) to find the correct portfolio page URLs for VCs
whose URLs are stale/404ing. Updates vc_list.yaml with corrected URLs.

Usage:
    # Dry run — show what would be updated
    python scripts/fix_portfolio_urls.py --dry-run

    # Fix all VCs with broken URLs
    python scripts/fix_portfolio_urls.py

    # Fix specific VCs
    python scripts/fix_portfolio_urls.py --vcs accel benchmark battery-ventures

    # Also find URLs for VCs that have none
    python scripts/fix_portfolio_urls.py --include-missing
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import os
import re
import sys
from pathlib import Path

import httpx
import yaml
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("fix_urls")

SERPER_API_URL = "https://google.serper.dev/search"
VC_LIST_PATH = PROJECT_ROOT / "config" / "vc_list.yaml"


# ---------------------------------------------------------------------------
# URL checking
# ---------------------------------------------------------------------------

async def check_url(client: httpx.AsyncClient, url: str) -> tuple[str, int]:
    """Check if a URL is reachable. Returns (url, status_code)."""
    try:
        r = await client.head(url, follow_redirects=True, timeout=10.0)
        return url, r.status_code
    except Exception:
        try:
            r = await client.get(url, follow_redirects=True, timeout=10.0)
            return url, r.status_code
        except Exception:
            return url, 0


async def check_urls_batch(urls: list[str], concurrency: int = 10) -> dict[str, int]:
    """Check multiple URLs concurrently. Returns {url: status_code}."""
    results = {}
    semaphore = asyncio.Semaphore(concurrency)

    async with httpx.AsyncClient(
        headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"},
    ) as client:
        async def _check(url: str):
            async with semaphore:
                u, status = await check_url(client, url)
                results[u] = status

        await asyncio.gather(*[_check(u) for u in urls])

    return results


# ---------------------------------------------------------------------------
# Serper search for portfolio URLs
# ---------------------------------------------------------------------------

async def search_portfolio_url(
    client: httpx.AsyncClient,
    vc_name: str,
    vc_website: str | None = None,
    serper_key: str = "",
) -> str | None:
    """Use Serper to find the portfolio page URL for a VC."""
    # Build search queries
    queries = []
    if vc_website:
        domain = re.sub(r"https?://", "", vc_website).rstrip("/")
        queries.append(f"site:{domain} portfolio")
        queries.append(f"site:{domain} companies")
    queries.append(f"{vc_name} portfolio companies page")

    for query in queries:
        try:
            r = await client.post(
                SERPER_API_URL,
                headers={
                    "X-API-KEY": serper_key,
                    "Content-Type": "application/json",
                },
                json={"q": query, "num": 5},
                timeout=10.0,
            )
            r.raise_for_status()
            data = r.json()

            for result in data.get("organic", []):
                link = result.get("link", "")
                title = (result.get("title", "") + " " + result.get("snippet", "")).lower()

                # Look for portfolio-like URLs
                if any(kw in link.lower() for kw in ["/portfolio", "/companies", "/investments", "/our-companies"]):
                    # Verify it's from the VC's own domain (if we know it)
                    if vc_website:
                        domain = re.sub(r"https?://(www\.)?", "", vc_website).split("/")[0]
                        if domain.lower() in link.lower():
                            return link
                    else:
                        # Accept if title/snippet mentions portfolio
                        if any(kw in title for kw in ["portfolio", "companies", "investments"]):
                            return link

        except Exception as exc:
            logger.warning("Search failed for %r query %r: %s", vc_name, query, exc)

    return None


# ---------------------------------------------------------------------------
# Main logic
# ---------------------------------------------------------------------------

async def fix_urls(
    vc_slugs: list[str] | None = None,
    include_missing: bool = False,
    dry_run: bool = False,
) -> dict[str, str]:
    """Find and fix broken portfolio URLs.

    Returns:
        Dict of {slug: new_url} for VCs that were updated.
    """
    serper_key = os.environ.get("SERPER_API_KEY", "")
    if not serper_key:
        logger.error("SERPER_API_KEY not set in .env")
        return {}

    # Load VC list
    with open(VC_LIST_PATH) as f:
        data = yaml.safe_load(f)

    vcs = data.get("vcs", [])
    logger.info("Loaded %d VCs from %s", len(vcs), VC_LIST_PATH)

    # Determine which VCs to check
    to_check = []
    for vc in vcs:
        slug = vc.get("slug", "")
        urls = vc.get("portfolio_urls", [])

        if vc_slugs and slug not in vc_slugs:
            continue

        if urls:
            to_check.append(vc)
        elif include_missing:
            to_check.append(vc)

    if not to_check:
        logger.info("No VCs to check")
        return {}

    # Step 1: Check existing URLs for 404s
    logger.info("Checking %d VCs for broken URLs...", len(to_check))
    all_urls = []
    url_to_vc = {}
    for vc in to_check:
        for url in vc.get("portfolio_urls", []):
            all_urls.append(url)
            url_to_vc[url] = vc["slug"]

    url_statuses = await check_urls_batch(all_urls) if all_urls else {}

    # Identify broken VCs
    broken_vcs = []
    ok_count = 0
    for vc in to_check:
        urls = vc.get("portfolio_urls", [])
        if not urls:
            if include_missing:
                broken_vcs.append(vc)
                logger.info("  [MISSING] %s — no portfolio URLs", vc.get("name"))
            continue

        all_broken = all(url_statuses.get(u, 0) >= 400 or url_statuses.get(u, 0) == 0 for u in urls)
        if all_broken:
            broken_vcs.append(vc)
            statuses = [f"{u} → {url_statuses.get(u, '?')}" for u in urls]
            logger.info("  [BROKEN] %s — %s", vc.get("name"), "; ".join(statuses))
        else:
            ok_count += 1

    logger.info("Results: %d OK, %d broken/missing", ok_count, len(broken_vcs))

    if not broken_vcs:
        logger.info("All URLs are working!")
        return {}

    # Step 2: Search for correct URLs
    logger.info("\nSearching for correct portfolio URLs for %d VCs...", len(broken_vcs))
    updates = {}

    async with httpx.AsyncClient() as client:
        for vc in broken_vcs:
            slug = vc.get("slug", "")
            name = vc.get("name", slug)
            website = vc.get("website")

            new_url = await search_portfolio_url(client, name, website, serper_key)

            if new_url:
                logger.info("  [FOUND] %s → %s", name, new_url)
                updates[slug] = new_url
            else:
                logger.warning("  [NOT FOUND] %s — could not find portfolio URL", name)

            # Rate limit
            await asyncio.sleep(0.5)

    if not updates:
        logger.info("No new URLs found")
        return {}

    # Step 3: Update vc_list.yaml
    if dry_run:
        logger.info("\n[DRY RUN] Would update %d VCs:", len(updates))
        for slug, url in updates.items():
            logger.info("  %s → %s", slug, url)
        return updates

    logger.info("\nUpdating %d VCs in %s...", len(updates), VC_LIST_PATH)
    for vc in vcs:
        slug = vc.get("slug", "")
        if slug in updates:
            vc["portfolio_urls"] = [updates[slug]]

    with open(VC_LIST_PATH, "w") as f:
        yaml.dump(data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

    logger.info("Done! Updated %d portfolio URLs", len(updates))
    return updates


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Fix broken VC portfolio URLs")
    parser.add_argument("--vcs", nargs="*", help="Specific VC slugs to fix")
    parser.add_argument("--include-missing", action="store_true",
                        help="Also find URLs for VCs with no portfolio URLs")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show what would be updated without making changes")
    args = parser.parse_args()

    results = asyncio.run(fix_urls(
        vc_slugs=args.vcs,
        include_missing=args.include_missing,
        dry_run=args.dry_run,
    ))

    if results:
        print(f"\n{'Would update' if args.dry_run else 'Updated'} {len(results)} URLs")
    else:
        print("\nNo updates needed")


if __name__ == "__main__":
    main()
