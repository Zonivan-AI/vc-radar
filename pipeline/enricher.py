"""
Founder data enrichment using free/cheap search APIs.

Supports multiple search backends:
  - DuckDuckGo HTML scraping (FREE, no API key, default)
  - Serper API ($50/mo, higher quality)

Then uses the DataExtractor (cheap OSS models) to parse search results
into structured founder profiles.
"""

from __future__ import annotations

import asyncio
import logging
import os
import re
from typing import Any
from urllib.parse import quote_plus

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from pipeline.extractor import DataExtractor
from pipeline.validator import DataValidator, Founder

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SERPER_API_URL = "https://google.serper.dev/search"
DDG_HTML_URL = "https://html.duckduckgo.com/html/"
RATE_LIMIT_SECONDS = 1.5  # Minimum delay between searches
MAX_CONCURRENT_SEARCHES = 3
MAX_SEARCH_RESULTS = 10


# ---------------------------------------------------------------------------
# Search backends
# ---------------------------------------------------------------------------


class DuckDuckGoSearch:
    """Free search using DuckDuckGo HTML endpoint. No API key needed."""

    def __init__(self) -> None:
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(20.0),
                headers={
                    "User-Agent": (
                        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/122.0.0.0 Safari/537.36"
                    ),
                },
                follow_redirects=True,
            )
        return self._client

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    @retry(
        retry=retry_if_exception_type((httpx.ConnectError, httpx.ReadTimeout)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    async def search(self, query: str) -> list[str]:
        """Search DuckDuckGo and return text snippets."""
        client = await self._get_client()

        response = await client.post(
            DDG_HTML_URL,
            data={"q": query, "b": ""},
        )
        response.raise_for_status()
        html = response.text

        return self._extract_snippets(html)

    def _extract_snippets(self, html: str) -> list[str]:
        """Extract result snippets from DuckDuckGo HTML response."""
        snippets: list[str] = []

        # Extract result blocks: <a class="result__a" href="...">title</a>
        # and <a class="result__snippet">snippet text</a>
        titles = re.findall(
            r'class="result__a"[^>]*>([^<]+)</a>', html
        )
        snippet_texts = re.findall(
            r'class="result__snippet"[^>]*>(.*?)</(?:a|span)>',
            html,
            re.DOTALL,
        )
        urls = re.findall(
            r'class="result__url"[^>]*href="([^"]*)"',
            html,
        )

        for i, title in enumerate(titles[:MAX_SEARCH_RESULTS]):
            parts = [title.strip()]
            if i < len(snippet_texts):
                # Clean HTML tags from snippet
                snippet = re.sub(r"<[^>]+>", "", snippet_texts[i]).strip()
                parts.append(snippet)
            if i < len(urls):
                parts.append(f"URL: {urls[i]}")
            snippets.append("\n".join(parts))

        return snippets


class SerperSearch:
    """Google search via Serper API ($50/mo for 50k queries)."""

    def __init__(self, api_key: str) -> None:
        self._api_key = api_key
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(30.0),
                headers={
                    "X-API-KEY": self._api_key,
                    "Content-Type": "application/json",
                },
            )
        return self._client

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    @retry(
        retry=retry_if_exception_type((httpx.HTTPStatusError, httpx.ConnectError)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=15),
        reraise=True,
    )
    async def search(self, query: str) -> list[str]:
        """Search Google via Serper API."""
        client = await self._get_client()
        response = await client.post(
            SERPER_API_URL,
            json={"q": query, "num": MAX_SEARCH_RESULTS},
        )
        response.raise_for_status()
        return self._extract_snippets(response.json())

    def _extract_snippets(self, data: dict) -> list[str]:
        """Extract text snippets from Serper response."""
        snippets: list[str] = []

        # Knowledge graph
        kg = data.get("knowledgeGraph", {})
        if kg:
            parts = []
            if kg.get("title"):
                parts.append(f"Title: {kg['title']}")
            if kg.get("description"):
                parts.append(f"Description: {kg['description']}")
            for k, v in kg.get("attributes", {}).items():
                parts.append(f"{k}: {v}")
            if parts:
                snippets.append("\n".join(parts))

        # Answer box
        answer = data.get("answerBox", {})
        if answer:
            snippets.append(f"Answer: {answer.get('snippet') or answer.get('answer', '')}")

        # Organic results
        for r in data.get("organic", []):
            parts = [r["title"]] if r.get("title") else []
            if r.get("snippet"):
                parts.append(r["snippet"])
            if r.get("link"):
                parts.append(f"URL: {r['link']}")
            if parts:
                snippets.append("\n".join(parts))

        return snippets


# ---------------------------------------------------------------------------
# Enricher
# ---------------------------------------------------------------------------


class FounderEnricher:
    """Enriches portfolio company data with founder biographical details.

    Uses free DuckDuckGo search by default, with Serper as optional upgrade.
    Search results are processed by cheap OSS models via DataExtractor.

    Cost breakdown per founder:
      - DuckDuckGo + Llama 3.3:  ~$0.001 (basically free)
      - Serper + Llama 3.3:      ~$0.002 (Serper costs $0.001/query)
      - Serper + Claude Sonnet:  ~$0.15  (150x more expensive)
    """

    def __init__(
        self,
        serper_key: str | None = None,
        extractor: DataExtractor | None = None,
    ) -> None:
        resolved_key = serper_key or os.environ.get("SERPER_API_KEY", "")

        # Choose search backend: Serper if key provided, else free DDG
        if resolved_key:
            self._search_backend = SerperSearch(resolved_key)
            self._search_name = "Serper"
            logger.info("FounderEnricher using Serper (paid) search")
        else:
            self._search_backend = DuckDuckGoSearch()
            self._search_name = "DuckDuckGo"
            logger.info("FounderEnricher using DuckDuckGo (free) search")

        self._extractor = extractor
        self._validator = DataValidator()
        self._semaphore = asyncio.Semaphore(MAX_CONCURRENT_SEARCHES)
        self._search_count = 0

    async def close(self) -> None:
        """Close HTTP clients."""
        await self._search_backend.close()

    # -- Search --------------------------------------------------------------

    async def search_founder(
        self, founder_name: str, company_name: str
    ) -> str:
        """Search for founder info using the configured backend."""
        async with self._semaphore:
            queries = [
                f'"{founder_name}" "{company_name}" founder CEO LinkedIn',
                f'"{founder_name}" education university founder',
            ]

            all_snippets: list[str] = []

            for query in queries:
                try:
                    snippets = await self._search_backend.search(query)
                    all_snippets.extend(snippets)
                    self._search_count += 1
                except Exception as exc:
                    logger.warning(
                        "%s search failed for query %r: %s",
                        self._search_name, query, exc,
                    )

                await asyncio.sleep(RATE_LIMIT_SECONDS)

            combined = "\n\n---\n\n".join(all_snippets)
            logger.info(
                "[%s] %r @ %r: %d snippets, %d chars",
                self._search_name,
                founder_name,
                company_name,
                len(all_snippets),
                len(combined),
            )
            return combined

    # -- Enrichment ----------------------------------------------------------

    async def enrich_company(self, company: dict) -> dict:
        """Enrich a single company with detailed founder data."""
        company_name = company.get("name", "Unknown")
        founded_year = company.get("founded_year")
        founders_raw = company.get("founders", [])

        if not founders_raw:
            return company

        enriched_founders: list[dict] = []

        for founder_raw in founders_raw:
            founder_name = founder_raw.get("full_name", "")
            if not founder_name:
                enriched_founders.append(founder_raw)
                continue

            try:
                enriched = await self._enrich_single_founder(
                    founder_name=founder_name,
                    founder_raw=founder_raw,
                    company_name=company_name,
                    founded_year=founded_year,
                )
                enriched_founders.append(enriched)
            except Exception as exc:
                logger.error(
                    "Failed to enrich %r for %r: %s",
                    founder_name, company_name, exc,
                )
                enriched_founders.append(founder_raw)

        company["founders"] = enriched_founders
        return company

    async def _enrich_single_founder(
        self,
        founder_name: str,
        founder_raw: dict,
        company_name: str,
        founded_year: int | None,
    ) -> dict:
        """Enrich a single founder with search + LLM extraction."""
        search_text = await self.search_founder(founder_name, company_name)

        if not search_text.strip():
            logger.warning("No search results for %r @ %r", founder_name, company_name)
            return founder_raw

        if self._extractor is None:
            return founder_raw

        extracted = await self._extractor.extract_founder_info(
            search_results=search_text,
            company_name=company_name,
            founded_year=founded_year,
        )

        # Merge: original non-null values take precedence
        merged = dict(extracted)
        for key, value in founder_raw.items():
            if value is not None and value != "":
                merged[key] = value

        # Compute age_at_founding
        if merged.get("est_birth_year") and founded_year:
            merged["age_at_founding"] = founded_year - merged["est_birth_year"]

        # Validate and score confidence
        validated, warnings = self._validator.validate_founder(merged)
        if validated:
            merged["age_confidence"] = validated.age_confidence

        logger.info(
            "Enriched %r: birth_year=%s, confidence=%s",
            founder_name,
            merged.get("est_birth_year"),
            merged.get("age_confidence", "Low"),
        )
        return merged

    async def enrich_batch(self, companies: list[dict]) -> list[dict]:
        """Enrich a batch of companies sequentially."""
        enriched: list[dict] = []

        for i, company in enumerate(companies):
            logger.info(
                "Enriching %d/%d: %s",
                i + 1, len(companies), company.get("name", "Unknown"),
            )
            try:
                result = await self.enrich_company(company)
                enriched.append(result)
            except Exception as exc:
                logger.error("Failed to enrich %r: %s", company.get("name"), exc)
                enriched.append(company)

        logger.info("Batch enrichment complete: %d companies", len(enriched))
        return enriched

    @property
    def search_count(self) -> int:
        return self._search_count
