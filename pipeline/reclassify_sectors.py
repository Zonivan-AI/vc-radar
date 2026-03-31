"""
Phase 1B: Reclassify 'Other' sector companies using descriptions + LLM.

For companies with descriptions, uses LLM to assign proper sectors.
For companies without descriptions, uses name-based heuristics.

Usage:
    python -m pipeline.reclassify_sectors
    python -m pipeline.reclassify_sectors --dry-run
    python -m pipeline.reclassify_sectors --batch-size 100
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
from pipeline.sector_normalizer import CANONICAL_SECTORS, normalize_sector

_env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(_env_path)

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

MODEL_KEY = os.environ.get("PIPELINE_SECTOR_MODEL", "deepseek/deepseek-chat")
MAX_CONCURRENT = 10

# Batch classification prompt — classify multiple companies at once for efficiency
SYSTEM_PROMPT = f"""You are a startup sector classifier. Given a list of companies with their names and descriptions, classify each into exactly one canonical sector.

Canonical sectors: {', '.join(CANONICAL_SECTORS)}

Rules:
- Use ONLY the canonical sectors listed above
- If a company clearly fits multiple sectors, pick the primary one
- "Other" should only be used if the company truly doesn't fit any sector
- Be specific: a payments company is "Fintech", not "SaaS/Enterprise"
- AI-first companies are "AI/ML" even if they serve enterprise customers

Respond with ONLY a JSON array of objects: [{{"id": "...", "sector": "..."}}]
No markdown, no explanation."""


async def classify_batch(
    companies: list[dict],
    llm: LLMClient,
    token_usage: TokenUsage,
) -> list[dict]:
    """Classify a batch of companies (up to 20) in a single LLM call."""
    items = []
    for c in companies:
        desc = c.get("description") or ""
        name = c.get("name", "Unknown")
        items.append(f"- id={c['id']} | {name}: {desc[:150]}")

    user_prompt = f"Classify these {len(items)} companies:\n\n" + "\n".join(items)

    try:
        text, inp, out = await llm.complete(MODEL_KEY, SYSTEM_PROMPT, user_prompt, max_tokens=2048)
        token_usage.record(inp, out, MODEL_KEY)

        text = re.sub(r"^```(?:json)?\s*\n?", "", text.strip())
        text = re.sub(r"\n?```\s*$", "", text)

        # Handle wrapper objects
        parsed = json.loads(text.strip())
        if isinstance(parsed, dict):
            for key in ("companies", "results", "data", "classifications"):
                if key in parsed and isinstance(parsed[key], list):
                    parsed = parsed[key]
                    break

        if not isinstance(parsed, list):
            return []

        # Validate sectors
        results = []
        for item in parsed:
            if isinstance(item, dict) and "id" in item and "sector" in item:
                sector = item["sector"]
                if sector in CANONICAL_SECTORS and sector != "Other":
                    results.append({"id": item["id"], "sector": sector})
        return results
    except Exception as e:
        logger.warning("Batch classification failed: %s", e)
        return []


async def main_async(args):
    sb = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_ROLE_KEY"])
    llm = LLMClient()
    token_usage = TokenUsage()

    # Fetch all 'Other' sector companies
    print("Fetching 'Other' sector companies...")
    all_companies = []
    batch_size = 1000
    offset = 0
    while True:
        batch = (
            sb.table("portfolio_companies")
            .select("id,name,description,sector")
            .eq("sector", "Other")
            .range(offset, offset + batch_size - 1)
            .execute()
        )
        if not batch.data:
            break
        all_companies.extend(batch.data)
        if len(batch.data) < batch_size:
            break
        offset += batch_size

    print(f"Found {len(all_companies)} companies in 'Other' sector")

    # Split into those with and without descriptions
    with_desc = [c for c in all_companies if c.get("description") and len(c["description"]) > 10]
    no_desc = [c for c in all_companies if not c.get("description") or len(c["description"]) <= 10]

    print(f"  With description: {len(with_desc)} (LLM classify)")
    print(f"  Without description: {len(no_desc)} (name-based heuristic)")

    if args.batch_size:
        with_desc = with_desc[:args.batch_size]

    # --- Phase A: Name-based reclassification (free, instant) ---
    name_updates = 0
    for c in no_desc:
        new_sector = normalize_sector(c.get("name", ""))
        if new_sector != "Other":
            if args.dry_run:
                print(f"  [DRY-NAME] {c['name']} -> {new_sector}")
            else:
                try:
                    sb.table("portfolio_companies").update({"sector": new_sector}).eq("id", c["id"]).execute()
                    name_updates += 1
                except Exception:
                    pass

    print(f"\nName-based reclassification: {name_updates} updated")

    # --- Phase B: LLM-based reclassification (batched, cheap) ---
    if not with_desc:
        print("No companies with descriptions to reclassify via LLM")
        await llm.close()
        return

    llm_updates = 0
    llm_batches = [with_desc[i:i+20] for i in range(0, len(with_desc), 20)]

    semaphore = asyncio.Semaphore(MAX_CONCURRENT)

    async def process_batch(batch_companies):
        nonlocal llm_updates
        async with semaphore:
            results = await classify_batch(batch_companies, llm, token_usage)
            for r in results:
                if args.dry_run:
                    # Find company name
                    name = next((c["name"] for c in batch_companies if c["id"] == r["id"]), "?")
                    print(f"  [DRY-LLM] {name} -> {r['sector']}")
                else:
                    try:
                        sb.table("portfolio_companies").update(
                            {"sector": r["sector"]}
                        ).eq("id", r["id"]).execute()
                        llm_updates += 1
                    except Exception as e:
                        logger.warning("Update failed: %s", e)

    tasks = [process_batch(b) for b in llm_batches]
    for i in range(0, len(tasks), MAX_CONCURRENT):
        chunk = tasks[i:i + MAX_CONCURRENT]
        await asyncio.gather(*chunk)
        done = min(i + MAX_CONCURRENT, len(tasks))
        print(f"  LLM Progress: {done}/{len(llm_batches)} batches | "
              f"updated={llm_updates} cost=${token_usage.estimated_cost_usd:.4f}")

    await llm.close()

    print(f"\n{'[DRY RUN] ' if args.dry_run else ''}Results:")
    print(f"  Name-based updates: {name_updates}")
    print(f"  LLM-based updates:  {llm_updates}")
    print(f"  Total reclassified: {name_updates + llm_updates}")
    print(f"  Cost: ${token_usage.estimated_cost_usd:.4f}")
    print(f"  Tokens: {token_usage.total_tokens:,}")


def main():
    parser = argparse.ArgumentParser(description="Reclassify 'Other' sector companies")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--batch-size", type=int, default=0)
    args = parser.parse_args()
    asyncio.run(main_async(args))


if __name__ == "__main__":
    main()
