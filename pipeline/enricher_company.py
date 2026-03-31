"""
Phase 2: Enrich portfolio companies with descriptions.

Fetches company websites, extracts a one-line description via LLM,
and updates Supabase. Uses httpx for fast fetching with Playwright fallback
for JS-heavy sites.

Usage:
    python -m pipeline.enricher_company
    python -m pipeline.enricher_company --dry-run
    python -m pipeline.enricher_company --batch-size 100
    python -m pipeline.enricher_company --use-playwright
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import os
import re
from pathlib import Path

import httpx
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from markdownify import markdownify as md
from supabase import create_client

from pipeline.extractor import LLMClient, TokenUsage

_env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(_env_path)

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

# ─── Config ──────────────────────────────────────────────────────────────────

MODEL_KEY = os.environ.get("PIPELINE_COMPANY_MODEL", "deepseek/deepseek-chat")
MAX_CONCURRENT = 8
FETCH_TIMEOUT = 15.0
MAX_MARKDOWN_CHARS = 8_000

SYSTEM_PROMPT = """You are a data extraction specialist. Given text content from a company's website, extract a concise 1-2 sentence description of what the company does.

Rules:
- Focus on the product/service and target market
- Be factual and specific, not generic marketing language
- If the content is insufficient, return {"description": null}
- Also extract the company's sector if clearly evident

Respond with ONLY a JSON object: {"description": "...", "sector": "..."}
No markdown, no explanation."""

USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
]


# ─── HTML → Markdown ─────────────────────────────────────────────────────────

def html_to_markdown(html: str, max_chars: int = MAX_MARKDOWN_CHARS) -> str:
    """Convert HTML to clean markdown, stripping non-content elements."""
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup.find_all(
        ["script", "style", "noscript", "svg", "head", "footer",
         "nav", "iframe", "form", "button", "input", "select",
         "img", "figure", "picture", "video", "audio", "canvas"]
    ):
        tag.decompose()
    for tag in soup.find_all(attrs={"id": re.compile(
        r"^(cookie-?consent|cookie-?banner|gdpr|onetrust)", re.IGNORECASE
    )}):
        tag.decompose()

    markdown = md(str(soup), strip=["img", "figure", "picture", "video", "audio", "canvas"])
    markdown = re.sub(r"\n{3,}", "\n\n", markdown)
    markdown = re.sub(r" {2,}", " ", markdown)
    markdown = markdown.strip()
    return markdown[:max_chars] if len(markdown) > max_chars else markdown


# ─── Fetch page content ──────────────────────────────────────────────────────

async def fetch_page(url: str, client: httpx.AsyncClient) -> str | None:
    """Fetch a page via httpx. Returns HTML or None on failure."""
    if not url or not url.startswith("http"):
        return None
    try:
        resp = await client.get(url, follow_redirects=True)
        if resp.status_code < 400 and len(resp.text) > 500:
            return resp.text
    except Exception as e:
        logger.debug("Failed to fetch %s: %s", url, e)
    return None


# ─── Extract description via LLM ─────────────────────────────────────────────

async def extract_description(
    llm: LLMClient, markdown: str, company_name: str, token_usage: TokenUsage
) -> dict:
    """Extract description from markdown content using LLM."""
    user_prompt = f"Company: {company_name}\n\nWebsite content:\n{markdown}"
    try:
        text, inp, out = await llm.complete(MODEL_KEY, SYSTEM_PROMPT, user_prompt, max_tokens=256)
        token_usage.record(inp, out, MODEL_KEY)

        # Parse JSON
        text = re.sub(r"^```(?:json)?\s*\n?", "", text.strip())
        text = re.sub(r"\n?```\s*$", "", text)
        import json
        data = json.loads(text.strip())
        return data
    except Exception as e:
        logger.warning("LLM extraction failed for %s: %s", company_name, e)
        return {}


# ─── Main pipeline ────────────────────────────────────────────────────────────

async def enrich_batch(
    companies: list[dict],
    sb,
    llm: LLMClient,
    token_usage: TokenUsage,
    dry_run: bool = False,
    use_playwright: bool = False,
) -> dict:
    """Enrich a batch of companies with descriptions."""
    stats = {"fetched": 0, "extracted": 0, "updated": 0, "failed": 0}

    semaphore = asyncio.Semaphore(MAX_CONCURRENT)
    http_client = httpx.AsyncClient(
        timeout=httpx.Timeout(FETCH_TIMEOUT),
        headers={"User-Agent": USER_AGENTS[0]},
        limits=httpx.Limits(max_connections=MAX_CONCURRENT),
    )

    # Optional Playwright for JS-heavy sites
    scraper = None
    if use_playwright:
        from pipeline.scraper import VCScraper
        scraper = VCScraper()
        await scraper.init()

    async def process_one(company: dict):
        async with semaphore:
            cid = company["id"]
            name = company.get("name", "Unknown")
            website = company.get("website", "")

            # Fetch page
            html = await fetch_page(website, http_client)
            if not html and scraper:
                try:
                    html = await scraper.scrape_portfolio(website)
                except Exception:
                    pass

            if not html:
                stats["failed"] += 1
                return

            stats["fetched"] += 1
            markdown = html_to_markdown(html)
            if len(markdown) < 50:
                stats["failed"] += 1
                return

            # Extract description
            result = await extract_description(llm, markdown, name, token_usage)
            desc = result.get("description")
            if not desc:
                stats["failed"] += 1
                return

            stats["extracted"] += 1

            if dry_run:
                print(f"  [DRY] {name}: {desc[:80]}...")
                return

            # Update Supabase
            update = {"description": desc}
            sector = result.get("sector")
            if sector and company.get("sector") in ("Other", None, ""):
                update["sector"] = sector

            try:
                sb.table("portfolio_companies").update(update).eq("id", cid).execute()
                stats["updated"] += 1
            except Exception as e:
                logger.warning("DB update failed for %s: %s", name, e)
                stats["failed"] += 1

    # Process all companies
    tasks = [process_one(c) for c in companies]
    for i in range(0, len(tasks), MAX_CONCURRENT * 2):
        batch = tasks[i : i + MAX_CONCURRENT * 2]
        await asyncio.gather(*batch)
        done = min(i + MAX_CONCURRENT * 2, len(tasks))
        print(f"  Progress: {done}/{len(tasks)} | "
              f"fetched={stats['fetched']} extracted={stats['extracted']} "
              f"updated={stats['updated']} failed={stats['failed']} "
              f"cost=${token_usage.estimated_cost_usd:.4f}")

    await http_client.aclose()
    if scraper:
        await scraper.close()

    return stats


async def main_async(args):
    sb = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_ROLE_KEY"])
    llm = LLMClient()
    token_usage = TokenUsage()

    # Fetch companies that have a website but no description
    print("Fetching companies missing descriptions...")
    all_companies = []
    batch_size = 1000
    offset = 0
    while True:
        batch = (
            sb.table("portfolio_companies")
            .select("id,name,website,sector,description")
            .is_("description", "null")
            .not_.is_("website", "null")
            .range(offset, offset + batch_size - 1)
            .execute()
        )
        if not batch.data:
            break
        all_companies.extend(batch.data)
        if len(batch.data) < batch_size:
            break
        offset += batch_size

    # Also get companies with empty string descriptions
    offset = 0
    while True:
        batch = (
            sb.table("portfolio_companies")
            .select("id,name,website,sector,description")
            .eq("description", "")
            .not_.is_("website", "null")
            .range(offset, offset + batch_size - 1)
            .execute()
        )
        if not batch.data:
            break
        all_companies.extend(batch.data)
        if len(batch.data) < batch_size:
            break
        offset += batch_size

    # Filter to those with actual website URLs
    companies = [c for c in all_companies if c.get("website") and c["website"].startswith("http")]
    print(f"Found {len(companies)} companies with websites but no description")

    if args.batch_size:
        companies = companies[: args.batch_size]
        print(f"Processing first {len(companies)} (--batch-size {args.batch_size})")

    if not companies:
        print("Nothing to enrich!")
        return

    stats = await enrich_batch(
        companies, sb, llm, token_usage,
        dry_run=args.dry_run,
        use_playwright=args.use_playwright,
    )

    await llm.close()

    print(f"\n{'[DRY RUN] ' if args.dry_run else ''}Results:")
    print(f"  Fetched:   {stats['fetched']}")
    print(f"  Extracted: {stats['extracted']}")
    print(f"  Updated:   {stats['updated']}")
    print(f"  Failed:    {stats['failed']}")
    print(f"  Cost:      ${token_usage.estimated_cost_usd:.4f}")
    print(f"  Tokens:    {token_usage.total_tokens:,}")


def main():
    parser = argparse.ArgumentParser(description="Enrich company descriptions")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--batch-size", type=int, default=0)
    parser.add_argument("--use-playwright", action="store_true",
                        help="Use Playwright for JS-heavy sites (slower but more reliable)")
    args = parser.parse_args()
    asyncio.run(main_async(args))


if __name__ == "__main__":
    main()
