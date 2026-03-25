#!/usr/bin/env python3
"""
Test script for pipeline speed optimizations.

Compares sequential vs parallel founder enrichment for 3 well-known companies
(Stripe, Airbnb, SpaceX) to measure the speedup from concurrent LLM calls.

Usage:
    python scripts/test_optimizations.py

    # With cloud enrichment (DeepSeek via OpenRouter)
    USE_CLOUD_ENRICHMENT=true python scripts/test_optimizations.py

Requirements:
    - LM Studio running locally (or set LMSTUDIO_API_URL to vllm-mlx endpoint)
    - Or OPENROUTER_API_KEY set for cloud models
    - pip install httpx tenacity pyyaml python-dotenv
"""

from __future__ import annotations

import asyncio
import logging
import os
import sys
import time
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv

load_dotenv(PROJECT_ROOT / ".env")

from pipeline.enricher import FounderEnricher, MAX_CONCURRENT_ENRICHMENTS
from pipeline.extractor import DataExtractor, USE_CLOUD_ENRICHMENT

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("test_optimizations")

# Suppress noisy HTTP logs
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)


# ---------------------------------------------------------------------------
# Test data: 3 companies with known founders
# ---------------------------------------------------------------------------

TEST_COMPANIES = [
    {
        "name": "Stripe",
        "website": "https://stripe.com",
        "founded_year": 2010,
        "founders": [
            {"full_name": "Patrick Collison"},
            {"full_name": "John Collison"},
        ],
    },
    {
        "name": "Airbnb",
        "website": "https://airbnb.com",
        "founded_year": 2008,
        "founders": [
            {"full_name": "Brian Chesky"},
            {"full_name": "Joe Gebbia"},
            {"full_name": "Nathan Blecharczyk"},
        ],
    },
    {
        "name": "SpaceX",
        "website": "https://spacex.com",
        "founded_year": 2002,
        "founders": [
            {"full_name": "Elon Musk"},
        ],
    },
]


# ---------------------------------------------------------------------------
# Sequential enrichment (baseline)
# ---------------------------------------------------------------------------

async def run_sequential(companies: list[dict], enricher: FounderEnricher) -> tuple[list[dict], float]:
    """Run enrichment sequentially (one founder at a time) — the old way."""
    import copy
    companies_copy = copy.deepcopy(companies)

    start = time.perf_counter()

    for company in companies_copy:
        company_name = company["name"]
        founded_year = company.get("founded_year")
        enriched_founders = []

        for founder_raw in company.get("founders", []):
            founder_name = founder_raw.get("full_name", "")
            if not founder_name:
                enriched_founders.append(founder_raw)
                continue

            try:
                enriched = await enricher._enrich_single_founder(
                    founder_name=founder_name,
                    founder_raw=founder_raw,
                    company_name=company_name,
                    founded_year=founded_year,
                )
                enriched_founders.append(enriched)
            except Exception as exc:
                logger.error("Sequential: failed %r: %s", founder_name, exc)
                enriched_founders.append(founder_raw)

        company["founders"] = enriched_founders

    elapsed = time.perf_counter() - start
    return companies_copy, elapsed


# ---------------------------------------------------------------------------
# Parallel enrichment (new way)
# ---------------------------------------------------------------------------

async def run_parallel(companies: list[dict], enricher: FounderEnricher) -> tuple[list[dict], float]:
    """Run enrichment with parallel founder processing — the new way."""
    import copy
    companies_copy = copy.deepcopy(companies)

    start = time.perf_counter()

    # Inject website URLs into founder dicts (matches enrich_batch behavior)
    for company in companies_copy:
        website = company.get("website", "")
        if website:
            for f in company.get("founders", []):
                if isinstance(f, dict):
                    f["company_website"] = website

    # Use the new enrich_company which does parallel founder enrichment
    for company in companies_copy:
        await enricher.enrich_company(company)

    elapsed = time.perf_counter() - start
    return companies_copy, elapsed


# ---------------------------------------------------------------------------
# Test search result pre-filtering
# ---------------------------------------------------------------------------

def test_snippet_filtering():
    """Test that snippet filtering reduces text size while keeping relevant content."""
    # Simulate search results: some relevant, some not
    relevant_snippet = (
        "Patrick Collison co-founded Stripe in 2010. He was born in 1988 in "
        "Limerick, Ireland. Collison attended MIT before dropping out to work on Stripe."
    )
    irrelevant_snippet = (
        "Online payment processing has grown significantly in recent years. "
        "The global digital payments market is expected to reach $15 trillion by 2027."
    )
    mixed_snippet = (
        "Forbes 30 Under 30 list featured Patrick Collison as one of the youngest "
        "billionaires in tech history."
    )

    test_text = "\n\n---\n\n".join([
        relevant_snippet,
        irrelevant_snippet,
        irrelevant_snippet,
        mixed_snippet,
        irrelevant_snippet,
    ])

    filtered = FounderEnricher._filter_relevant_snippets(test_text, "Patrick Collison")

    logger.info("=== Snippet Filtering Test ===")
    logger.info("Original text: %d chars", len(test_text))
    logger.info("Filtered text: %d chars", len(filtered))
    logger.info(
        "Reduction: %.1f%%",
        (1 - len(filtered) / len(test_text)) * 100 if test_text else 0,
    )

    # Verify relevant content is preserved
    assert "Patrick Collison" in filtered, "Relevant content was lost!"
    assert "co-founded Stripe" in filtered, "Key founder info was lost!"
    logger.info("PASS: Relevant content preserved after filtering")
    print()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

async def main():
    print("=" * 70)
    print("VC Radar Pipeline Optimization Test")
    print("=" * 70)
    print()
    print(f"Concurrent enrichment slots: {MAX_CONCURRENT_ENRICHMENTS}")
    print(f"Cloud enrichment (DeepSeek): {'ENABLED' if USE_CLOUD_ENRICHMENT else 'DISABLED'}")
    print(f"LM Studio URL: {os.environ.get('LMSTUDIO_API_URL', 'default')}")
    print()

    # Test 1: Snippet filtering (no network needed)
    test_snippet_filtering()

    # Test 2: Actual enrichment comparison (needs LM Studio or cloud API)
    total_founders = sum(len(c["founders"]) for c in TEST_COMPANIES)
    print(f"Test companies: {', '.join(c['name'] for c in TEST_COMPANIES)}")
    print(f"Total founders to enrich: {total_founders}")
    print()

    extractor = DataExtractor()
    enricher = FounderEnricher(extractor=extractor)

    try:
        # Run parallel (new way)
        print("--- Running PARALLEL enrichment ---")
        parallel_results, parallel_time = await run_parallel(TEST_COMPANIES, enricher)
        print(f"Parallel time: {parallel_time:.1f}s")
        print()

        # Run sequential (old way) for comparison
        print("--- Running SEQUENTIAL enrichment (baseline) ---")
        sequential_results, sequential_time = await run_sequential(TEST_COMPANIES, enricher)
        print(f"Sequential time: {sequential_time:.1f}s")
        print()

        # Compare results
        print("=" * 70)
        print("RESULTS COMPARISON")
        print("=" * 70)
        print()
        print(f"Sequential: {sequential_time:.1f}s")
        print(f"Parallel:   {parallel_time:.1f}s")

        if sequential_time > 0:
            speedup = sequential_time / parallel_time if parallel_time > 0 else float("inf")
            print(f"Speedup:    {speedup:.2f}x")
        print()

        # Print enrichment details
        for results, label in [(parallel_results, "Parallel"), (sequential_results, "Sequential")]:
            print(f"--- {label} Results ---")
            for company in results:
                print(f"\n  {company['name']}:")
                for founder in company.get("founders", []):
                    name = founder.get("full_name", "Unknown")
                    birth_year = founder.get("est_birth_year", "N/A")
                    confidence = founder.get("age_confidence", "N/A")
                    university = founder.get("university", "N/A")
                    print(f"    - {name}: birth={birth_year}, confidence={confidence}, edu={university}")
            print()

        print(f"Search API calls: {enricher.search_count}")
        print(f"Token usage: {extractor.token_usage.to_dict()}")

    except Exception as exc:
        logger.error("Test failed: %s", exc)
        logger.error(
            "Make sure LM Studio is running or OPENROUTER_API_KEY is set. "
            "You can also set USE_CLOUD_ENRICHMENT=true to use DeepSeek cloud."
        )
        raise

    finally:
        await enricher.close()
        await extractor.close()


if __name__ == "__main__":
    asyncio.run(main())
