"""
Phase 4B: Enrich company funding stages using LLM knowledge.

For companies with descriptions but no stage, asks LLM to infer
the funding stage from the description + company name.

Usage:
    python -m pipeline.enricher_stages
    python -m pipeline.enricher_stages --dry-run
    python -m pipeline.enricher_stages --batch-size 500
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

_env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(_env_path)

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

MODEL_KEY = os.environ.get("PIPELINE_STAGE_MODEL", "deepseek/deepseek-chat")
MAX_CONCURRENT = 5
BATCH_SIZE = 25

VALID_STAGES = {"Pre-Seed", "Seed", "Series A", "Series B", "Series C", "Series D", "Growth"}

SYSTEM_PROMPT = f"""You are a startup funding analyst. Given a list of companies with their names and descriptions, estimate their most likely current funding stage.

Valid stages: {', '.join(sorted(VALID_STAGES))}

Rules:
- ONLY assign a stage if you are reasonably confident based on your knowledge
- If you're not sure, skip the company entirely
- Consider company maturity signals: employee count, revenue stage, product maturity
- Large well-known companies (1000+ employees, public) = Growth
- Companies with major rounds mentioned in their description = use that stage
- Early-stage startups with basic products = Seed or Pre-Seed
- Do NOT guess randomly — skip if uncertain

Respond with ONLY a JSON array: [{{"id": "...", "stage": "..."}}]
No markdown, no explanation. Empty array [] if none are confident."""


async def classify_batch(
    companies: list[dict],
    llm: LLMClient,
    token_usage: TokenUsage,
) -> list[dict]:
    items = []
    for c in companies:
        desc = (c.get("description") or "")[:150]
        items.append(f"- id={c['id']} | {c['name']}: {desc}")

    user_prompt = f"Estimate funding stages for these {len(items)} companies:\n\n" + "\n".join(items)

    try:
        text, inp, out = await llm.complete(MODEL_KEY, SYSTEM_PROMPT, user_prompt, max_tokens=2048)
        token_usage.record(inp, out, MODEL_KEY)

        text = re.sub(r"^```(?:json)?\s*\n?", "", text.strip())
        text = re.sub(r"\n?```\s*$", "", text)

        parsed = json.loads(text.strip())
        if isinstance(parsed, dict):
            for key in ("companies", "results", "data"):
                if key in parsed and isinstance(parsed[key], list):
                    parsed = parsed[key]
                    break

        if not isinstance(parsed, list):
            return []

        results = []
        for item in parsed:
            if isinstance(item, dict) and "id" in item and "stage" in item:
                if item["stage"] in VALID_STAGES:
                    results.append(item)
        return results
    except Exception as e:
        logger.warning("Batch failed: %s", e)
        return []


async def main_async(args):
    sb = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_ROLE_KEY"])
    llm = LLMClient()
    token_usage = TokenUsage()

    # Fetch companies with descriptions but no stage
    print("Fetching companies with descriptions but no stage...")
    all_companies = []
    offset = 0
    while True:
        batch = (
            sb.table("portfolio_companies")
            .select("id,name,description,stage")
            .is_("stage", "null")
            .not_.is_("description", "null")
            .range(offset, offset + 999)
            .execute()
        )
        if not batch.data:
            break
        all_companies.extend(batch.data)
        if len(batch.data) < 1000:
            break
        offset += 1000

    # Filter to those with substantial descriptions
    all_companies = [c for c in all_companies if c.get("description") and len(c["description"]) > 20]
    print(f"Found {len(all_companies)} companies with descriptions but no stage")

    if args.batch_size:
        all_companies = all_companies[:args.batch_size]
        print(f"Processing first {len(all_companies)} (--batch-size {args.batch_size})")

    if not all_companies:
        print("Nothing to enrich!")
        return

    batches = [all_companies[i:i + BATCH_SIZE] for i in range(0, len(all_companies), BATCH_SIZE)]
    print(f"Processing {len(batches)} batches of ~{BATCH_SIZE} companies each")

    stats = {"classified": 0, "updated": 0, "skipped": 0}
    semaphore = asyncio.Semaphore(MAX_CONCURRENT)

    async def process_batch(batch_companies):
        async with semaphore:
            results = await classify_batch(batch_companies, llm, token_usage)
            stats["classified"] += len(results)
            stats["skipped"] += len(batch_companies) - len(results)

            for r in results:
                if args.dry_run:
                    name = next((c["name"] for c in batch_companies if c["id"] == r["id"]), "?")
                    print(f"  [DRY] {name} -> {r['stage']}")
                    continue

                try:
                    sb.table("portfolio_companies").update(
                        {"stage": r["stage"]}
                    ).eq("id", r["id"]).execute()
                    stats["updated"] += 1
                except Exception as e:
                    logger.warning("Update failed: %s", e)

    tasks = [process_batch(b) for b in batches]
    for i in range(0, len(tasks), MAX_CONCURRENT):
        chunk = tasks[i:i + MAX_CONCURRENT]
        await asyncio.gather(*chunk)
        done = min(i + MAX_CONCURRENT, len(tasks))
        print(f"  Progress: {done}/{len(batches)} batches | "
              f"classified={stats['classified']} updated={stats['updated']} "
              f"skipped={stats['skipped']} cost=${token_usage.estimated_cost_usd:.4f}")

    await llm.close()

    print(f"\n{'[DRY RUN] ' if args.dry_run else ''}Results:")
    print(f"  Classified:  {stats['classified']}/{len(all_companies)}")
    print(f"  Updated:     {stats['updated']}")
    print(f"  Skipped:     {stats['skipped']}")
    print(f"  Cost:        ${token_usage.estimated_cost_usd:.4f}")
    print(f"  Tokens:      {token_usage.total_tokens:,}")


def main():
    parser = argparse.ArgumentParser(description="Enrich company funding stages via LLM")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--batch-size", type=int, default=0)
    args = parser.parse_args()
    asyncio.run(main_async(args))


if __name__ == "__main__":
    main()
