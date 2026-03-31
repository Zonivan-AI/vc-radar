"""
Phase 3B: Enrich VC firms without websites via web search.

Searches DuckDuckGo/Serper for VC info and extracts description,
thesis, AUM, and website URL via LLM.

Usage:
    python -m pipeline.enricher_vc_search
    python -m pipeline.enricher_vc_search --dry-run
    python -m pipeline.enricher_vc_search --batch-size 100
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import re
import time
from pathlib import Path

import httpx
from dotenv import load_dotenv
from supabase import create_client

from pipeline.extractor import LLMClient, TokenUsage

_env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(_env_path)

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

MODEL_KEY = os.environ.get("PIPELINE_VC_MODEL", "deepseek/deepseek-chat")
SERPER_API_KEY = os.environ.get("SERPER_API_KEY", "")
SERPER_URL = "https://google.serper.dev/search"
MAX_CONCURRENT = 2  # Very low concurrency to avoid DDG rate limits

SYSTEM_PROMPT = """You are a VC research analyst. Given search results about a venture capital firm, extract:
- description: A concise 2-3 sentence description of the firm (who they are, what they invest in)
- thesis: Their investment thesis or approach in 1-2 sentences (null if not found)
- aum_usd: Assets under management in USD as integer (e.g., 5000000000 for $5B). null if not mentioned
- website: The firm's main website URL if found
- founded_year: Year founded (integer). null if not mentioned

Rules:
- Be factual, extract only what's clearly stated in the search results
- For AUM, convert: "$5B" → 5000000000, "$500M" → 500000000
- Use null for unavailable fields
- Do NOT make up information

Respond with ONLY a JSON object. No markdown."""


async def search_vc_serper(name: str, client: httpx.AsyncClient) -> str:
    """Search for a VC using Serper API."""
    if not SERPER_API_KEY:
        return ""
    try:
        resp = await client.post(
            SERPER_URL,
            headers={"X-API-KEY": SERPER_API_KEY, "Content-Type": "application/json"},
            json={"q": f'"{name}" venture capital firm', "num": 5},
        )
        if resp.status_code != 200:
            return ""
        data = resp.json()
        snippets = []
        for result in data.get("organic", [])[:5]:
            title = result.get("title", "")
            snippet = result.get("snippet", "")
            link = result.get("link", "")
            snippets.append(f"{title}: {snippet} ({link})")
        kg = data.get("knowledgeGraph", {})
        if kg:
            snippets.append(f"Knowledge Graph: {kg.get('title','')} - {kg.get('description','')}")
        return "\n".join(snippets)
    except Exception as e:
        logger.debug("Serper search failed for %s: %s", name, e)
        return ""


async def search_vc_ddg(name: str, client: httpx.AsyncClient) -> str:
    """Search for a VC using DuckDuckGo HTML (free)."""
    try:
        resp = await client.get(
            "https://html.duckduckgo.com/html/",
            params={"q": f'"{name}" venture capital'},
            headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"},
        )
        if resp.status_code != 200:
            return ""
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(resp.text, "html.parser")
        results = soup.find_all("div", class_="result")
        snippets = []
        for r in results[:5]:
            title_el = r.find("a", class_="result__a")
            snippet_el = r.find("a", class_="result__snippet")
            title = title_el.get_text(strip=True) if title_el else ""
            snippet = snippet_el.get_text(strip=True) if snippet_el else ""
            link = title_el.get("href", "") if title_el else ""
            if title or snippet:
                snippets.append(f"{title}: {snippet} ({link})")
        return "\n".join(snippets)
    except Exception as e:
        logger.debug("DDG search failed for %s: %s", name, e)
        return ""


async def search_vc(name: str, client: httpx.AsyncClient) -> str:
    """Search using Serper first (better results for VCs), fall back to DDG."""
    result = await search_vc_serper(name, client)
    if result:
        return result
    # Delay to avoid DDG rate limits
    await asyncio.sleep(2.0)
    return await search_vc_ddg(name, client)


async def extract_from_search(
    llm: LLMClient, search_text: str, vc_name: str, token_usage: TokenUsage
) -> dict:
    """Extract VC info from search results."""
    user_prompt = f"VC Firm: {vc_name}\n\nSearch results:\n{search_text}"
    try:
        text, inp, out = await llm.complete(MODEL_KEY, SYSTEM_PROMPT, user_prompt, max_tokens=512)
        token_usage.record(inp, out, MODEL_KEY)
        text = re.sub(r"^```(?:json)?\s*\n?", "", text.strip())
        text = re.sub(r"\n?```\s*$", "", text)
        return json.loads(text.strip())
    except Exception as e:
        logger.warning("Extraction failed for %s: %s", vc_name, e)
        return {}


async def main_async(args):
    sb = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_ROLE_KEY"])
    llm = LLMClient()
    token_usage = TokenUsage()

    # Fetch VCs without description AND without website
    print("Fetching VCs missing descriptions (no website)...")
    all_vcs = []
    batch_size = 1000
    offset = 0
    while True:
        batch = (
            sb.table("vc_firms")
            .select("id,name,description,website,aum_usd,founded_year")
            .is_("description", "null")
            .is_("website", "null")
            .range(offset, offset + batch_size - 1)
            .execute()
        )
        if not batch.data:
            break
        all_vcs.extend(batch.data)
        if len(batch.data) < batch_size:
            break
        offset += batch_size

    print(f"Found {len(all_vcs)} VCs without description or website")

    if args.batch_size:
        all_vcs = all_vcs[:args.batch_size]
        print(f"Processing first {len(all_vcs)} (--batch-size {args.batch_size})")

    if not all_vcs:
        print("Nothing to enrich!")
        return

    stats = {"searched": 0, "extracted": 0, "updated": 0, "failed": 0}
    semaphore = asyncio.Semaphore(MAX_CONCURRENT)
    http_client = httpx.AsyncClient(
        timeout=httpx.Timeout(15.0),
        limits=httpx.Limits(max_connections=MAX_CONCURRENT),
    )

    async def process_one(vc):
        async with semaphore:
            name = vc.get("name", "Unknown")
            vid = vc["id"]

            search_text = await search_vc(name, http_client)
            if not search_text:
                stats["failed"] += 1
                return

            stats["searched"] += 1
            result = await extract_from_search(llm, search_text, name, token_usage)
            desc = result.get("description")
            if not desc:
                stats["failed"] += 1
                return

            stats["extracted"] += 1

            if args.dry_run:
                aum = result.get("aum_usd")
                aum_str = f"${aum / 1e9:.1f}B" if aum and aum >= 1e9 else f"${aum / 1e6:.0f}M" if aum else "N/A"
                print(f"  [DRY] {name}: {desc[:60]}... | AUM={aum_str}")
                return

            update = {"description": desc}
            if result.get("thesis"):
                update["description"] = f"{desc} Investment thesis: {result['thesis']}"
            if result.get("website"):
                update["website"] = result["website"]
            if result.get("aum_usd") and not vc.get("aum_usd"):
                update["aum_usd"] = result["aum_usd"]
            if result.get("founded_year") and not vc.get("founded_year"):
                update["founded_year"] = result["founded_year"]

            try:
                sb.table("vc_firms").update(update).eq("id", vid).execute()
                stats["updated"] += 1
            except Exception as e:
                logger.warning("Update failed for %s: %s", name, e)
                stats["failed"] += 1

    tasks = [process_one(vc) for vc in all_vcs]
    for i in range(0, len(tasks), MAX_CONCURRENT * 2):
        batch = tasks[i:i + MAX_CONCURRENT * 2]
        await asyncio.gather(*batch)
        done = min(i + MAX_CONCURRENT * 2, len(tasks))
        print(f"  Progress: {done}/{len(tasks)} | "
              f"searched={stats['searched']} extracted={stats['extracted']} "
              f"updated={stats['updated']} failed={stats['failed']} "
              f"cost=${token_usage.estimated_cost_usd:.4f}")

    await http_client.aclose()
    await llm.close()

    serper_cost = stats["searched"] * 0.001

    print(f"\n{'[DRY RUN] ' if args.dry_run else ''}Results:")
    print(f"  Searched:    {stats['searched']}")
    print(f"  Extracted:   {stats['extracted']}")
    print(f"  Updated:     {stats['updated']}")
    print(f"  Failed:      {stats['failed']}")
    print(f"  LLM Cost:    ${token_usage.estimated_cost_usd:.4f}")
    print(f"  Serper Cost: ~${serper_cost:.2f}")
    print(f"  Total Cost:  ~${token_usage.estimated_cost_usd + serper_cost:.2f}")


def main():
    parser = argparse.ArgumentParser(description="Enrich VCs via web search")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--batch-size", type=int, default=0)
    args = parser.parse_args()
    asyncio.run(main_async(args))


if __name__ == "__main__":
    main()
