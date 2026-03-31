"""
Phase 3C: Enrich VC firms using LLM knowledge (no web search).

Sends batches of VC names to the LLM and asks it to describe known firms.
Cheap and fast — no search API needed.

Usage:
    python -m pipeline.enricher_vc_llm
    python -m pipeline.enricher_vc_llm --dry-run
    python -m pipeline.enricher_vc_llm --batch-size 100
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

MODEL_KEY = os.environ.get("PIPELINE_VC_MODEL", "deepseek/deepseek-chat")
MAX_CONCURRENT = 5
BATCH_SIZE = 15  # VCs per LLM call

SYSTEM_PROMPT = """You are a VC research analyst with deep knowledge of the venture capital industry.

Given a list of VC firm names, provide information about each firm you recognize. For firms you don't recognize or aren't sure about, skip them entirely.

For each recognized firm, provide:
- id: The ID from the input (pass through exactly)
- description: 2-3 sentence description of the firm
- thesis: Investment thesis in 1-2 sentences (null if unknown)
- aum_usd: Assets under management in USD as integer (null if unknown)
- website: Main website URL (null if unknown)
- founded_year: Year founded as integer (null if unknown)

Rules:
- ONLY include firms you are confident about — do NOT guess or hallucinate
- If you're not sure about a firm, omit it from the response
- For AUM, use approximate known figures: "$5B" → 5000000000
- Be accurate about websites — only include URLs you're confident about

Respond with ONLY a JSON array of objects. No markdown, no explanation.
Return an empty array [] if you don't recognize any firms."""


async def classify_batch(
    vcs: list[dict],
    llm: LLMClient,
    token_usage: TokenUsage,
) -> list[dict]:
    """Get LLM knowledge about a batch of VC firms."""
    items = [f"- id={v['id']} | {v['name']}" for v in vcs]
    user_prompt = f"Provide information about these {len(items)} VC firms:\n\n" + "\n".join(items)

    try:
        text, inp, out = await llm.complete(MODEL_KEY, SYSTEM_PROMPT, user_prompt, max_tokens=4096)
        token_usage.record(inp, out, MODEL_KEY)

        text = re.sub(r"^```(?:json)?\s*\n?", "", text.strip())
        text = re.sub(r"\n?```\s*$", "", text)

        parsed = json.loads(text.strip())
        if isinstance(parsed, dict):
            for key in ("firms", "results", "data", "vcs"):
                if key in parsed and isinstance(parsed[key], list):
                    parsed = parsed[key]
                    break

        if not isinstance(parsed, list):
            return []

        results = []
        for item in parsed:
            if isinstance(item, dict) and "id" in item and "description" in item:
                if item.get("description") and len(item["description"]) > 20:
                    results.append(item)
        return results
    except Exception as e:
        logger.warning("Batch classification failed: %s", e)
        return []


async def main_async(args):
    sb = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_ROLE_KEY"])
    llm = LLMClient()
    token_usage = TokenUsage()

    # Fetch VCs without descriptions
    print("Fetching VCs missing descriptions...")
    all_vcs = []
    offset = 0
    while True:
        batch = (
            sb.table("vc_firms")
            .select("id,name,description,website,aum_usd,founded_year")
            .is_("description", "null")
            .range(offset, offset + 999)
            .execute()
        )
        if not batch.data:
            break
        all_vcs.extend(batch.data)
        if len(batch.data) < 1000:
            break
        offset += 1000

    print(f"Found {len(all_vcs)} VCs without descriptions")

    if args.batch_size:
        all_vcs = all_vcs[:args.batch_size]
        print(f"Processing first {len(all_vcs)} (--batch-size {args.batch_size})")

    if not all_vcs:
        print("Nothing to enrich!")
        return

    # Split into batches
    batches = [all_vcs[i:i + BATCH_SIZE] for i in range(0, len(all_vcs), BATCH_SIZE)]
    print(f"Processing {len(batches)} batches of ~{BATCH_SIZE} VCs each")

    stats = {"recognized": 0, "updated": 0, "skipped": 0}
    semaphore = asyncio.Semaphore(MAX_CONCURRENT)

    async def process_batch(batch_vcs):
        async with semaphore:
            results = await classify_batch(batch_vcs, llm, token_usage)
            stats["recognized"] += len(results)
            stats["skipped"] += len(batch_vcs) - len(results)

            for r in results:
                if args.dry_run:
                    desc = r.get("description", "")[:60]
                    aum = r.get("aum_usd")
                    aum_str = f"${aum / 1e9:.1f}B" if aum and aum >= 1e9 else f"${aum / 1e6:.0f}M" if aum else "N/A"
                    print(f"  [DRY] {r.get('id','?')[:8]}...: {desc}... | AUM={aum_str}")
                    continue

                update = {}
                desc = r.get("description", "")
                if r.get("thesis"):
                    desc = f"{desc} Investment thesis: {r['thesis']}"
                update["description"] = desc

                if r.get("website"):
                    update["website"] = r["website"]
                if r.get("aum_usd"):
                    update["aum_usd"] = r["aum_usd"]
                if r.get("founded_year"):
                    update["founded_year"] = r["founded_year"]

                try:
                    sb.table("vc_firms").update(update).eq("id", r["id"]).execute()
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
    print(f"  Recognized:  {stats['recognized']}/{len(all_vcs)}")
    print(f"  Updated:     {stats['updated']}")
    print(f"  Skipped:     {stats['skipped']}")
    print(f"  Cost:        ${token_usage.estimated_cost_usd:.4f}")
    print(f"  Tokens:      {token_usage.total_tokens:,}")


def main():
    parser = argparse.ArgumentParser(description="Enrich VCs via LLM knowledge")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--batch-size", type=int, default=0)
    args = parser.parse_args()
    asyncio.run(main_async(args))


if __name__ == "__main__":
    main()
