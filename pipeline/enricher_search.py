"""
Phase 2B: Enrich company descriptions via web search (Serper + LLM).

For companies that have no website URL, searches the web for information
and extracts a description via LLM.

Usage:
    python -m pipeline.enricher_search
    python -m pipeline.enricher_search --dry-run
    python -m pipeline.enricher_search --batch-size 200
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
from dotenv import load_dotenv
from supabase import create_client

from pipeline.extractor import LLMClient, TokenUsage

_env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(_env_path)

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

MODEL_KEY = os.environ.get("PIPELINE_SEARCH_MODEL", "deepseek/deepseek-chat")
SERPER_API_KEY = os.environ.get("SERPER_API_KEY", "")
SERPER_URL = "https://google.serper.dev/search"
MAX_CONCURRENT = 8

SYSTEM_PROMPT = """You are a startup data extraction specialist. Given search results about a company, extract:
- description: A concise 1-2 sentence description of what the company does
- sector: Primary sector (AI/ML, Fintech, Healthcare, SaaS/Enterprise, DeepTech/Hardware, Climate/Energy, Consumer, Crypto/Web3, Cybersecurity, Edtech, Real Estate/PropTech, Other)
- website: The company's main website URL if found
- stage: Funding stage if mentioned (Pre-Seed, Seed, Series A, Series B, Series C, Series D, Growth)
- founded_year: Year founded if mentioned

Rules:
- Be factual, only extract what's clearly stated
- Use null for unavailable fields
- For sector, pick the most specific match

Respond with ONLY a JSON object. No markdown."""


async def search_company_ddg(name: str, client: httpx.AsyncClient) -> str:
    """Search for a company using DuckDuckGo HTML (free)."""
    try:
        resp = await client.get(
            "https://html.duckduckgo.com/html/",
            params={"q": f"{name} startup company"},
            headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"},
        )
        if resp.status_code != 200:
            return ""
        # Parse DDG HTML results
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


async def search_company_serper(name: str, client: httpx.AsyncClient) -> str:
    """Search for a company using Serper API ($0.001/query)."""
    if not SERPER_API_KEY:
        return ""
    try:
        resp = await client.post(
            SERPER_URL,
            headers={"X-API-KEY": SERPER_API_KEY, "Content-Type": "application/json"},
            json={"q": f"{name} startup company", "num": 5},
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


async def search_company(name: str, client: httpx.AsyncClient) -> str:
    """Search using DDG (free), fall back to Serper if available."""
    result = await search_company_ddg(name, client)
    if result:
        return result
    return await search_company_serper(name, client)


async def extract_from_search(
    llm: LLMClient, search_text: str, company_name: str, token_usage: TokenUsage
) -> dict:
    """Extract company info from search results."""
    user_prompt = f"Company: {company_name}\n\nSearch results:\n{search_text}"
    try:
        text, inp, out = await llm.complete(MODEL_KEY, SYSTEM_PROMPT, user_prompt, max_tokens=256)
        token_usage.record(inp, out, MODEL_KEY)
        text = re.sub(r"^```(?:json)?\s*\n?", "", text.strip())
        text = re.sub(r"\n?```\s*$", "", text)
        return json.loads(text.strip())
    except Exception as e:
        logger.warning("Extraction failed for %s: %s", company_name, e)
        return {}


async def main_async(args):
    sb = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_ROLE_KEY"])
    llm = LLMClient()
    token_usage = TokenUsage()

    # Fetch companies without description AND without website
    print("Fetching companies missing descriptions (no website)...")
    all_companies = []
    batch_size = 1000
    offset = 0
    while True:
        batch = (
            sb.table("portfolio_companies")
            .select("id,name,description,website,sector,stage,founded_year")
            .is_("description", "null")
            .is_("website", "null")
            .range(offset, offset + batch_size - 1)
            .execute()
        )
        if not batch.data:
            break
        all_companies.extend(batch.data)
        if len(batch.data) < batch_size:
            break
        offset += batch_size

    print(f"Found {len(all_companies)} companies without description or website")

    if args.batch_size:
        all_companies = all_companies[:args.batch_size]
        print(f"Processing first {len(all_companies)} (--batch-size {args.batch_size})")

    if not all_companies:
        print("Nothing to enrich!")
        return

    stats = {"searched": 0, "extracted": 0, "updated": 0, "failed": 0}
    semaphore = asyncio.Semaphore(MAX_CONCURRENT)
    http_client = httpx.AsyncClient(
        timeout=httpx.Timeout(15.0),
        limits=httpx.Limits(max_connections=MAX_CONCURRENT),
    )

    async def process_one(company):
        async with semaphore:
            name = company.get("name", "Unknown")
            cid = company["id"]

            search_text = await search_company(name, http_client)
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
                sector = result.get("sector", "?")
                print(f"  [DRY] {name}: {desc[:70]}... | sector={sector}")
                return

            update = {"description": desc}
            if result.get("website"):
                update["website"] = result["website"]
            if result.get("sector") and result["sector"] != "Other" and company.get("sector") in ("Other", None):
                update["sector"] = result["sector"]
            if result.get("stage") and not company.get("stage"):
                update["stage"] = result["stage"]
            if result.get("founded_year") and not company.get("founded_year"):
                update["founded_year"] = result["founded_year"]

            try:
                sb.table("portfolio_companies").update(update).eq("id", cid).execute()
                stats["updated"] += 1
            except Exception as e:
                logger.warning("Update failed for %s: %s", name, e)
                stats["failed"] += 1

    tasks = [process_one(c) for c in all_companies]
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

    # Estimate Serper cost
    serper_cost = stats["searched"] * 0.001  # ~$0.001/query

    print(f"\n{'[DRY RUN] ' if args.dry_run else ''}Results:")
    print(f"  Searched:    {stats['searched']}")
    print(f"  Extracted:   {stats['extracted']}")
    print(f"  Updated:     {stats['updated']}")
    print(f"  Failed:      {stats['failed']}")
    print(f"  LLM Cost:    ${token_usage.estimated_cost_usd:.4f}")
    print(f"  Serper Cost: ~${serper_cost:.2f}")
    print(f"  Total Cost:  ~${token_usage.estimated_cost_usd + serper_cost:.2f}")


def main():
    parser = argparse.ArgumentParser(description="Enrich companies via web search")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--batch-size", type=int, default=0)
    args = parser.parse_args()
    asyncio.run(main_async(args))


if __name__ == "__main__":
    main()
