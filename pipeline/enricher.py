"""
Founder data enrichment using Serper API (Google search).

Searches for founders via Google, then uses the DataExtractor to parse
search results into structured founder profiles with confidence scoring.
"""

from __future__ import annotations

import asyncio
import logging
import os
from typing import Any

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
SERPER_RATE_LIMIT_SECONDS = 1.0  # Minimum delay between Serper calls
MAX_CONCURRENT_SEARCHES = 3
MAX_SEARCH_RESULTS = 10


# ---------------------------------------------------------------------------
# Enricher
# ---------------------------------------------------------------------------


class FounderEnricher:
    """Enriches portfolio company data with founder biographical details.

    Uses the Serper API to search Google for founder information, then passes
    the search results through the DataExtractor (Claude) for structured
    extraction.

    Usage::

        extractor = DataExtractor(api_key="sk-ant-...")
        enricher = FounderEnricher(serper_key="...", extractor=extractor)

        enriched = await enricher.enrich_company({
            "name": "Acme Corp",
            "founded_year": 2021,
            "founders": [{"full_name": "Jane Doe", "role": "primary"}],
        })
    """

    def __init__(
        self,
        serper_key: str | None = None,
        extractor: DataExtractor | None = None,
    ) -> None:
        resolved_key = serper_key or os.environ.get("SERPER_API_KEY")
        if not resolved_key:
            raise ValueError(
                "Serper API key required. Pass serper_key or set SERPER_API_KEY."
            )
        self._serper_key = resolved_key
        self._extractor = extractor
        self._validator = DataValidator()
        self._http_client: httpx.AsyncClient | None = None
        self._semaphore = asyncio.Semaphore(MAX_CONCURRENT_SEARCHES)
        self._search_count = 0
        logger.info("FounderEnricher initialized")

    async def _get_client(self) -> httpx.AsyncClient:
        """Lazily create the async HTTP client."""
        if self._http_client is None or self._http_client.is_closed:
            self._http_client = httpx.AsyncClient(
                timeout=httpx.Timeout(30.0),
                headers={
                    "X-API-KEY": self._serper_key,
                    "Content-Type": "application/json",
                },
            )
        return self._http_client

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._http_client and not self._http_client.is_closed:
            await self._http_client.aclose()
            self._http_client = None

    # -- Search --------------------------------------------------------------

    @retry(
        retry=retry_if_exception_type((httpx.HTTPStatusError, httpx.ConnectError)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=15),
        reraise=True,
    )
    async def search_founder(
        self, founder_name: str, company_name: str
    ) -> str:
        """Search Google via Serper API for information about a founder.

        Constructs targeted search queries to find biographical details,
        LinkedIn profiles, education, and prior experience.

        Args:
            founder_name: Full name of the founder.
            company_name: Name of the founder's company.

        Returns:
            Concatenated text snippets from search results.
        """
        async with self._semaphore:
            client = await self._get_client()

            # Build targeted queries
            queries = [
                f'"{founder_name}" "{company_name}" founder CEO LinkedIn',
                f'"{founder_name}" education university founder',
            ]

            all_snippets: list[str] = []

            for query in queries:
                logger.debug("Serper search: %s", query)

                response = await client.post(
                    SERPER_API_URL,
                    json={
                        "q": query,
                        "num": MAX_SEARCH_RESULTS,
                    },
                )
                response.raise_for_status()

                data = response.json()
                snippets = self._extract_snippets(data)
                all_snippets.extend(snippets)

                self._search_count += 1

                # Rate limiting between searches
                await asyncio.sleep(SERPER_RATE_LIMIT_SECONDS)

            combined = "\n\n---\n\n".join(all_snippets)
            logger.info(
                "Search for %r @ %r returned %d snippet(s), %d chars",
                founder_name,
                company_name,
                len(all_snippets),
                len(combined),
            )
            return combined

    def _extract_snippets(self, serper_response: dict) -> list[str]:
        """Extract text snippets from a Serper API response.

        Pulls from organic results, knowledge graph, and answer boxes.
        """
        snippets: list[str] = []

        # Knowledge graph
        kg = serper_response.get("knowledgeGraph", {})
        if kg:
            parts = []
            if kg.get("title"):
                parts.append(f"Title: {kg['title']}")
            if kg.get("description"):
                parts.append(f"Description: {kg['description']}")
            for attr_key, attr_val in kg.get("attributes", {}).items():
                parts.append(f"{attr_key}: {attr_val}")
            if parts:
                snippets.append("\n".join(parts))

        # Answer box
        answer = serper_response.get("answerBox", {})
        if answer:
            if answer.get("snippet"):
                snippets.append(f"Answer: {answer['snippet']}")
            elif answer.get("answer"):
                snippets.append(f"Answer: {answer['answer']}")

        # Organic results
        for result in serper_response.get("organic", []):
            parts = []
            if result.get("title"):
                parts.append(result["title"])
            if result.get("snippet"):
                parts.append(result["snippet"])
            if result.get("link"):
                parts.append(f"URL: {result['link']}")
            if parts:
                snippets.append("\n".join(parts))

        # People also ask
        for paa in serper_response.get("peopleAlsoAsk", []):
            if paa.get("snippet"):
                snippets.append(f"Q: {paa.get('question', '')}\nA: {paa['snippet']}")

        return snippets

    # -- Enrichment ----------------------------------------------------------

    async def enrich_company(self, company: dict) -> dict:
        """Enrich a single company dict with detailed founder data.

        For each founder listed in the company, searches Google and uses
        Claude to extract structured biographical data.

        Args:
            company: Company dict with at least 'name' and 'founders' keys.

        Returns:
            The company dict with enriched founder data.
        """
        company_name = company.get("name", "Unknown")
        founded_year = company.get("founded_year")
        founders_raw = company.get("founders", [])

        if not founders_raw:
            logger.info("Company %r has no founders to enrich", company_name)
            return company

        enriched_founders: list[dict] = []

        for founder_raw in founders_raw:
            founder_name = founder_raw.get("full_name", "")
            if not founder_name:
                logger.warning("Skipping founder with no name for company %r", company_name)
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
                    "Failed to enrich founder %r for %r: %s",
                    founder_name,
                    company_name,
                    exc,
                )
                # Keep original data on failure
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
        """Enrich a single founder with search + extraction.

        Args:
            founder_name: The founder's full name.
            founder_raw: Original founder dict from portfolio extraction.
            company_name: The company name for search context.
            founded_year: The company's founding year.

        Returns:
            Merged founder dict with enriched fields.
        """
        # Search for founder information
        search_text = await self.search_founder(founder_name, company_name)

        if not search_text.strip():
            logger.warning(
                "No search results for founder %r @ %r",
                founder_name,
                company_name,
            )
            return founder_raw

        # Use Claude to extract structured data from search results
        if self._extractor is None:
            logger.warning("No DataExtractor configured; returning raw founder data")
            return founder_raw

        extracted = await self._extractor.extract_founder_info(
            search_results=search_text,
            company_name=company_name,
            founded_year=founded_year,
        )

        # Merge: extracted data fills in blanks, original data takes precedence
        merged = self._merge_founder_data(original=founder_raw, extracted=extracted)

        # Compute age_at_founding if we have the data
        if merged.get("est_birth_year") and founded_year:
            merged["age_at_founding"] = founded_year - merged["est_birth_year"]

        # Validate and score confidence
        validated, warnings = self._validator.validate_founder(merged)
        if validated:
            merged["age_confidence"] = validated.age_confidence
            if warnings:
                logger.info(
                    "Founder %r enriched with warnings: %s", founder_name, warnings
                )

        logger.info(
            "Enriched founder %r: birth_year=%s, confidence=%s",
            founder_name,
            merged.get("est_birth_year"),
            merged.get("age_confidence", "Low"),
        )
        return merged

    def _merge_founder_data(self, original: dict, extracted: dict) -> dict:
        """Merge extracted founder data into original, preferring original non-null values.

        Args:
            original: Founder dict from portfolio extraction.
            extracted: Founder dict from search result extraction.

        Returns:
            Merged dict.
        """
        merged = dict(extracted)
        for key, value in original.items():
            if value is not None and value != "":
                merged[key] = value
        return merged

    # -- Batch enrichment ----------------------------------------------------

    async def enrich_batch(self, companies: list[dict]) -> list[dict]:
        """Enrich a batch of companies with founder data.

        Processes companies sequentially (founder searches run with bounded
        concurrency internally).

        Args:
            companies: List of company dicts.

        Returns:
            List of enriched company dicts.
        """
        enriched: list[dict] = []

        for i, company in enumerate(companies):
            logger.info(
                "Enriching company %d/%d: %s",
                i + 1,
                len(companies),
                company.get("name", "Unknown"),
            )
            try:
                result = await self.enrich_company(company)
                enriched.append(result)
            except Exception as exc:
                logger.error(
                    "Failed to enrich company %r: %s",
                    company.get("name"),
                    exc,
                )
                enriched.append(company)

        logger.info("Batch enrichment complete: %d companies processed", len(enriched))
        return enriched

    @property
    def search_count(self) -> int:
        """Total number of Serper API searches performed."""
        return self._search_count
