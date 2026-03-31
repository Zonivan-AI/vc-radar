"""
Phase 2C: Enrich company descriptions using LLM knowledge (no web search).

Sends batches of company names to the LLM and asks it to describe known startups.
Cheap and fast — no search API needed.

Usage:
    python -m pipeline.enricher_company_llm
    python -m pipeline.enricher_company_llm --dry-run
    python -m pipeline.enricher_company_llm --batch-size 500
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import re
from pathlib import Path

from dotenv import load_dotenv
from supabase import create_client

from pipeline.extractor import LLMClient, TokenUsage
from pipeline.sector_normalizer import CANONICAL_SECTORS

_env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(_env_path)

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

MODEL_KEY = os.environ.get("PIPELINE_COMPANY_MODEL", "deepseek/deepseek-chat")
MAX_CONCURRENT = 5
BATCH_SIZE = 20  # Companies per LLM call

SYSTEM_PROMPT = f"""You are a startup research analyst with extensive knowledge of the startup ecosystem.

Given a list of company names, provide information about each company you recognize as a startup or tech company. For companies you don't recognize or aren't sure about, skip them entirely.

For each recognized company, provide:
- id: The ID from the input (pass through exactly)
- description: 1-2 sentence description of what the company does
- sector: One of: {', '.join(CANONICAL_SECTORS)}
- stage: Funding stage if known (Pre-Seed, Seed, Series A, Series B, Series C, Series D, Growth), null if unknown
- website: Main website URL if known, null if unknown
- founded_year: Year founded as integer, null if unknown

Rules:
- ONLY include companies you are confident about — do NOT guess or hallucinate
- If you're not sure about a company, omit it from the response
- Many names are common words — only include if you're confident it's a known startup
- Use canonical sectors only

Respond with ONLY a JSON array of objects. No markdown, no explanation.
Return an empty array [] if you don't recognize any companies."""


async def classify_batch(
    companies: list[dict],
    llm: LLMClient,
    token_usage: TokenUsage,
) -> list[dict]:
    """Get LLM knowledge about a batch of companies."""
    items = [f"- id={c['id']} | {c['name']}" for c in companies]
    user_prompt = f"Provide information about these {len(items)} startups/companies:\n\n" + "\n".join(items)

    try:
        text, inp, out = await llm.complete(MODEL_KEY, SYSTEM_PROMPT, user_prompt, max_tokens=4096)
        token_usage.record(inp, out, MODEL_KEY)

        text = re.sub(r"^```(?:json)?\s*\n?", "", text.strip())
        text = re.sub(r"\n?```\s*$", "", text)

        parsed = json.loads(text.strip())
        if isinstance(parsed, dict):
            for key in ("companies", "results", "data", "startups"):
                if key in parsed and isinstance(parsed[key], list):
                    parsed = parsed[key]
                    break

        if not isinstance(parsed, list):
            return []

        results = []
        for item in parsed:
            if isinstance(item, dict) and "id" in item and "description" in item:
                desc = item.get("description", "")
                if desc and len(desc) > 20:
                    # Validate sector
                    sector = item.get("sector")
                    if sector and sector not in CANONICAL_SECTORS:
                        item["sector"] = None
                    results.append(item)
        return results
    except Exception as e:
        logger.warning("Batch classification failed: %s", e)
        return []


async def main_async(args):
    sb = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_ROLE_KEY"])
    llm = LLMClient()
    token_usage = TokenUsage()

    # Fetch companies without descriptions
    print("Fetching companies missing descriptions...")
    all_companies = []
    offset = 0
    while True:
        batch = (
            sb.table("portfolio_companies")
            .select("id,name,description,sector,stage,website,founded_year")
            .is_("description", "null")
            .range(offset, offset + 999)
            .execute()
        )
        if not batch.data:
            break
        all_companies.extend(batch.data)
        if len(batch.data) < 1000:
            break
        offset += 1000

    print(f"Found {len(all_companies)} companies without descriptions")

    if args.batch_size:
        all_companies = all_companies[:args.batch_size]
        print(f"Processing first {len(all_companies)} (--batch-size {args.batch_size})")

    if not all_companies:
        print("Nothing to enrich!")
        return

    batches = [all_companies[i:i + BATCH_SIZE] for i in range(0, len(all_companies), BATCH_SIZE)]
    print(f"Processing {len(batches)} batches of ~{BATCH_SIZE} companies each")

    stats = {"recognized": 0, "updated": 0, "skipped": 0}
    semaphore = asyncio.Semaphore(MAX_CONCURRENT)

    async def process_batch(batch_companies):
        async with semaphore:
            results = await classify_batch(batch_companies, llm, token_usage)
            stats["recognized"] += len(results)
            stats["skipped"] += len(batch_companies) - len(results)

            for r in results:
                if args.dry_run:
                    desc = r.get("description", "")[:60]
                    sector = r.get("sector", "?")
                    print(f"  [DRY] {r.get('id','?')[:8]}...: {desc}... | {sector}")
                    continue

                update = {"description": r["description"]}
                if r.get("website") and not next(
                    (c.get("website") for c in batch_companies if c["id"] == r["id"]), None
                ):
                    update["website"] = r["website"]
                if r.get("sector") and r["sector"] in CANONICAL_SECTORS:
                    # Only update if current is Other or null
                    current = next(
                        (c.get("sector") for c in batch_companies if c["id"] == r["id"]), None
                    )
                    if current in ("Other", None):
                        update["sector"] = r["sector"]
                if r.get("stage") and not next(
                    (c.get("stage") for c in batch_companies if c["id"] == r["id"]), None
                ):
                    update["stage"] = r["stage"]
                if r.get("founded_year") and not next(
                    (c.get("founded_year") for c in batch_companies if c["id"] == r["id"]), None
                ):
                    update["founded_year"] = r["founded_year"]

                try:
                    sb.table("portfolio_companies").update(update).eq("id", r["id"]).execute()
                    stats["updated"] += 1
                except Exception as e:
                    logger.warning("Update failed for %s: %s", r.get("id"), e)

    tasks = [process_batch(b) for b in batches]
    for i in range(0, len(tasks), MAX_CONCURRENT):
        chunk = tasks[i:i + MAX_CONCURRENT]
        await asyncio.gather(*chunk)
        done = min(i + MAX_CONCURRENT, len(tasks))
        print(f"  Progress: {done}/{len(batches)} batches | "
              f"recognized={stats['recognized']} updated={stats['updated']} "
              f"skipped={stats['skipped']} cost=${token_usage.estimated_cost_usd:.4f}")

    await llm.close()

    print(f"\n{'[DRY RUN] ' if args.dry_run else ''}Results:")
    print(f"  Recognized:  {stats['recognized']}/{len(all_companies)}")
    print(f"  Updated:     {stats['updated']}")
    print(f"  Skipped:     {stats['skipped']}")
    print(f"  Cost:        ${token_usage.estimated_cost_usd:.4f}")
    print(f"  Tokens:      {token_usage.total_tokens:,}")


def main():
    parser = argparse.ArgumentParser(description="Enrich companies via LLM knowledge")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--batch-size", type=int, default=0)
    args = parser.parse_args()
    asyncio.run(main_async(args))


if __name__ == "__main__":
    main()
