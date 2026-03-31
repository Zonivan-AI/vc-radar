"""
Phase 3A: Enrich VC firms with descriptions, thesis, and AUM.

Scrapes VC websites (/about, /thesis, /approach pages) and extracts
structured information via LLM.

Usage:
    python -m pipeline.enricher_vc
    python -m pipeline.enricher_vc --dry-run
    python -m pipeline.enricher_vc --batch-size 50
"""

from __future__ import annotations

import argparse
import asyncio
import json
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

MODEL_KEY = os.environ.get("PIPELINE_VC_MODEL", "deepseek/deepseek-chat")
MAX_CONCURRENT = 6
FETCH_TIMEOUT = 15.0
MAX_MARKDOWN_CHARS = 12_000

# Pages to try for each VC site (in priority order)
ABOUT_PATHS = [
    "/about", "/about-us", "/about/", "/about-us/",
    "/thesis", "/investment-thesis", "/approach",
    "/philosophy", "/strategy", "/team",
    "/who-we-are", "/what-we-do",
    "",  # homepage as last resort
]

SYSTEM_PROMPT = """You are a VC research analyst. Given text content from a venture capital firm's website, extract:

1. description: A concise 2-3 sentence description of the firm (who they are, what they do, their focus)
2. thesis: Their investment thesis or approach in 1-2 sentences (what they look for in startups)
3. aum_usd: Assets under management in USD (integer, e.g., 5000000000 for $5B). Use null if not mentioned.
4. founded_year: Year the firm was founded (integer). Use null if not mentioned.
5. check_size_min: Minimum check size in USD (integer). Use null if not mentioned.
6. check_size_max: Maximum check size in USD (integer). Use null if not mentioned.

Rules:
- Be factual, extract only what's stated or clearly implied
- For AUM, convert common formats: "$5B" → 5000000000, "$500M" → 500000000
- If content is insufficient, return null for that field
- Do NOT make up information

Respond with ONLY a JSON object. No markdown, no explanation."""

USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
]


# ─── HTML → Markdown ─────────────────────────────────────────────────────────

def html_to_markdown(html: str, max_chars: int = MAX_MARKDOWN_CHARS) -> str:
    """Convert HTML to clean markdown."""
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


# ─── Fetch VC about pages ────────────────────────────────────────────────────

async def fetch_vc_content(website: str, client: httpx.AsyncClient) -> str:
    """Try multiple paths on the VC website to find about/thesis content."""
    if not website or not website.startswith("http"):
        return ""

    base = website.rstrip("/")
    all_content = []

    for path in ABOUT_PATHS:
        url = f"{base}{path}"
        try:
            resp = await client.get(url, follow_redirects=True)
            if resp.status_code < 400 and len(resp.text) > 500:
                mk = html_to_markdown(resp.text, max_chars=MAX_MARKDOWN_CHARS // 2)
                if len(mk) > 100:
                    all_content.append(f"--- Page: {path or '/'} ---\n{mk}")
                    # Stop after getting 2 good pages to save tokens
                    if len(all_content) >= 2:
                        break
        except Exception:
            continue

    combined = "\n\n".join(all_content)
    return combined[:MAX_MARKDOWN_CHARS] if len(combined) > MAX_MARKDOWN_CHARS else combined


# ─── LLM extraction ──────────────────────────────────────────────────────────

async def extract_vc_info(
    llm: LLMClient, markdown: str, vc_name: str, token_usage: TokenUsage
) -> dict:
    """Extract VC info from website content using LLM."""
    user_prompt = f"VC Firm: {vc_name}\n\nWebsite content:\n{markdown}"
    try:
        text, inp, out = await llm.complete(MODEL_KEY, SYSTEM_PROMPT, user_prompt, max_tokens=512)
        token_usage.record(inp, out, MODEL_KEY)

        text = re.sub(r"^```(?:json)?\s*\n?", "", text.strip())
        text = re.sub(r"\n?```\s*$", "", text)
        return json.loads(text.strip())
    except Exception as e:
        logger.warning("LLM extraction failed for %s: %s", vc_name, e)
        return {}


# ─── Main pipeline ────────────────────────────────────────────────────────────

async def enrich_vcs(
    vcs: list[dict],
    sb,
    llm: LLMClient,
    token_usage: TokenUsage,
    dry_run: bool = False,
) -> dict:
    """Enrich a list of VCs with descriptions and thesis."""
    stats = {"fetched": 0, "extracted": 0, "updated": 0, "failed": 0}

    semaphore = asyncio.Semaphore(MAX_CONCURRENT)
    http_client = httpx.AsyncClient(
        timeout=httpx.Timeout(FETCH_TIMEOUT),
        headers={"User-Agent": USER_AGENTS[0]},
        limits=httpx.Limits(max_connections=MAX_CONCURRENT),
    )

    async def process_one(vc: dict):
        async with semaphore:
            vid = vc["id"]
            name = vc.get("name", "Unknown")
            website = vc.get("website", "")

            content = await fetch_vc_content(website, http_client)
            if not content or len(content) < 100:
                stats["failed"] += 1
                return

            stats["fetched"] += 1

            result = await extract_vc_info(llm, content, name, token_usage)
            desc = result.get("description")
            if not desc:
                stats["failed"] += 1
                return

            stats["extracted"] += 1

            if dry_run:
                thesis = result.get("thesis", "")
                aum = result.get("aum_usd")
                aum_str = f"${aum / 1e9:.1f}B" if aum and aum >= 1e9 else f"${aum / 1e6:.0f}M" if aum else "N/A"
                print(f"  [DRY] {name}: {desc[:60]}... | thesis={bool(thesis)} | AUM={aum_str}")
                return

            # Build update dict
            update = {"description": desc}
            if result.get("thesis"):
                # Store thesis in description if it adds value
                update["description"] = f"{desc} Investment thesis: {result['thesis']}"
            if result.get("aum_usd"):
                update["aum_usd"] = result["aum_usd"]
            if result.get("founded_year") and not vc.get("founded_year"):
                update["founded_year"] = result["founded_year"]

            try:
                sb.table("vc_firms").update(update).eq("id", vid).execute()
                stats["updated"] += 1
            except Exception as e:
                logger.warning("DB update failed for %s: %s", name, e)
                stats["failed"] += 1

    # Process in waves
    tasks = [process_one(vc) for vc in vcs]
    for i in range(0, len(tasks), MAX_CONCURRENT * 2):
        batch = tasks[i : i + MAX_CONCURRENT * 2]
        await asyncio.gather(*batch)
        done = min(i + MAX_CONCURRENT * 2, len(tasks))
        print(f"  Progress: {done}/{len(tasks)} | "
              f"fetched={stats['fetched']} extracted={stats['extracted']} "
              f"updated={stats['updated']} failed={stats['failed']} "
              f"cost=${token_usage.estimated_cost_usd:.4f}")

    await http_client.aclose()
    return stats


async def main_async(args):
    sb = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_ROLE_KEY"])
    llm = LLMClient()
    token_usage = TokenUsage()

    # Fetch VCs with website but no description
    print("Fetching VCs missing descriptions...")
    all_vcs = []
    batch_size = 1000
    offset = 0
    while True:
        batch = (
            sb.table("vc_firms")
            .select("id,name,website,description,founded_year,aum_usd")
            .is_("description", "null")
            .not_.is_("website", "null")
            .range(offset, offset + batch_size - 1)
            .execute()
        )
        if not batch.data:
            break
        all_vcs.extend(batch.data)
        if len(batch.data) < batch_size:
            break
        offset += batch_size

    # Also get VCs with empty descriptions
    offset = 0
    while True:
        batch = (
            sb.table("vc_firms")
            .select("id,name,website,description,founded_year,aum_usd")
            .eq("description", "")
            .not_.is_("website", "null")
            .range(offset, offset + batch_size - 1)
            .execute()
        )
        if not batch.data:
            break
        all_vcs.extend(batch.data)
        if len(batch.data) < batch_size:
            break
        offset += batch_size

    # Filter to those with actual URLs
    vcs = [v for v in all_vcs if v.get("website") and v["website"].startswith("http")]
    print(f"Found {len(vcs)} VCs with websites but no description")

    if args.batch_size:
        vcs = vcs[: args.batch_size]
        print(f"Processing first {len(vcs)} (--batch-size {args.batch_size})")

    if not vcs:
        print("Nothing to enrich!")
        return

    stats = await enrich_vcs(vcs, sb, llm, token_usage, dry_run=args.dry_run)
    await llm.close()

    print(f"\n{'[DRY RUN] ' if args.dry_run else ''}Results:")
    print(f"  Fetched:   {stats['fetched']}")
    print(f"  Extracted: {stats['extracted']}")
    print(f"  Updated:   {stats['updated']}")
    print(f"  Failed:    {stats['failed']}")
    print(f"  Cost:      ${token_usage.estimated_cost_usd:.4f}")
    print(f"  Tokens:    {token_usage.total_tokens:,}")


def main():
    parser = argparse.ArgumentParser(description="Enrich VC firm descriptions")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--batch-size", type=int, default=0)
    args = parser.parse_args()
    asyncio.run(main_async(args))


if __name__ == "__main__":
    main()
