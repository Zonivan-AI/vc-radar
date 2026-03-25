"""
Founder data enrichment using free/cheap search APIs.

Supports multiple search backends:
  - DuckDuckGo HTML scraping (FREE, no API key, default)
  - Exa semantic search ($0.005/query, best for news/funding rounds)
  - Serper API ($50/mo, Google results)

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
EXA_API_URL = "https://api.exa.ai/search"
RATE_LIMIT_SECONDS = 1.5  # Minimum delay between searches
MAX_CONCURRENT_SEARCHES = 3
MAX_SEARCH_RESULTS = 10
MAX_CONCURRENT_ENRICHMENTS = 4  # LM Studio supports 4 concurrent slots (continuous batching)
MAX_SEARCH_TEXT_CHARS = 15_000  # Cap search text sent to LLM (was ~30K, most is irrelevant)


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


class ExaSearch:
    """Semantic search via Exa API — best for news, funding rounds, updates.

    Pricing: ~$0.005/search (1-10 results with contents).
    Great for: "Company X raises Series A", "founder leaves company", etc.

    Exa uses neural/semantic search, so natural language queries work better
    than keyword-stuffed ones (unlike Google/DDG).
    """

    def __init__(self, api_key: str) -> None:
        self._api_key = api_key
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(30.0),
                headers={
                    "x-api-key": self._api_key,
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
        """Semantic search via Exa. Returns text snippets with highlights."""
        client = await self._get_client()
        response = await client.post(
            EXA_API_URL,
            json={
                "query": query,
                "numResults": MAX_SEARCH_RESULTS,
                "type": "auto",  # let Exa choose neural vs keyword
                "contents": {
                    "highlights": {
                        "numSentences": 3,
                        "highlightsPerUrl": 2,
                    },
                    "text": {
                        "maxCharacters": 500,
                    },
                },
            },
        )
        response.raise_for_status()
        return self._extract_snippets(response.json())

    async def search_news(
        self,
        query: str,
        days_back: int = 90,
    ) -> list[str]:
        """Search recent news/articles about a topic.

        This is Exa's killer feature — finds recent funding announcements,
        acquisitions, product launches, etc. that keyword search misses.
        """
        from datetime import datetime, timedelta

        start_date = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")

        client = await self._get_client()
        response = await client.post(
            EXA_API_URL,
            json={
                "query": query,
                "numResults": MAX_SEARCH_RESULTS,
                "type": "neural",  # neural is better for news
                "startPublishedDate": start_date,
                "contents": {
                    "highlights": {
                        "numSentences": 3,
                        "highlightsPerUrl": 2,
                    },
                    "text": {
                        "maxCharacters": 500,
                    },
                },
            },
        )
        response.raise_for_status()
        return self._extract_snippets(response.json())

    def _extract_snippets(self, data: dict) -> list[str]:
        """Extract text from Exa API response."""
        snippets: list[str] = []

        for result in data.get("results", []):
            parts = []
            if result.get("title"):
                parts.append(result["title"])
            if result.get("publishedDate"):
                parts.append(f"Published: {result['publishedDate'][:10]}")

            # Highlights are the most useful (Exa's unique feature)
            for highlight in result.get("highlights", []):
                parts.append(highlight)

            # Fallback to text extract
            if not result.get("highlights") and result.get("text"):
                parts.append(result["text"][:500])

            if result.get("url"):
                parts.append(f"URL: {result['url']}")

            if parts:
                snippets.append("\n".join(parts))

        return snippets


# ---------------------------------------------------------------------------
# Enricher
# ---------------------------------------------------------------------------


class FounderEnricher:
    """Enriches portfolio company data with founder biographical details.

    Search backend priority (uses first available key):
      1. Exa   ($0.005/query) — best quality, semantic search, news
      2. Serper ($0.001/query) — Google results
      3. DuckDuckGo (free)     — no API key needed

    Cost breakdown per founder (2 searches each):
      - DuckDuckGo + Llama 3.3:  ~$0.001 (basically free)
      - Exa + Llama 3.3:         ~$0.011 ($0.01 search + $0.001 LLM)
      - Serper + Llama 3.3:      ~$0.003
      - Serper + Claude Sonnet:  ~$0.15  (150x more expensive)
    """

    def __init__(
        self,
        serper_key: str | None = None,
        exa_key: str | None = None,
        extractor: DataExtractor | None = None,
    ) -> None:
        resolved_exa = exa_key or os.environ.get("EXA_API_KEY", "")
        resolved_serper = serper_key or os.environ.get("SERPER_API_KEY", "")

        # Choose search backend: Exa > Serper > DuckDuckGo
        if resolved_exa:
            self._search_backend = ExaSearch(resolved_exa)
            self._search_name = "Exa"
            logger.info("FounderEnricher using Exa (semantic, $0.005/query)")
        elif resolved_serper:
            self._search_backend = SerperSearch(resolved_serper)
            self._search_name = "Serper"
            logger.info("FounderEnricher using Serper (Google, $0.001/query)")
        else:
            self._search_backend = DuckDuckGoSearch()
            self._search_name = "DuckDuckGo"
            logger.info("FounderEnricher using DuckDuckGo (free)")

        # Keep Exa reference for news queries even if not primary backend
        self._exa: ExaSearch | None = (
            ExaSearch(resolved_exa) if resolved_exa else None
        )

        self._extractor = extractor
        self._validator = DataValidator()
        self._semaphore = asyncio.Semaphore(MAX_CONCURRENT_SEARCHES)
        self._search_count = 0

    async def close(self) -> None:
        """Close HTTP clients."""
        await self._search_backend.close()
        if self._exa and self._exa is not self._search_backend:
            await self._exa.close()

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

    # -- Founder Discovery ---------------------------------------------------

    async def _discover_founders(self, company_name: str, website: str | None = None) -> list[dict]:
        """Discover founder names for a company via search."""
        query = f'"{company_name}" founders CEO co-founder'
        try:
            search_text = await self.search_founder(company_name + " founders", company_name)
            if not search_text or len(search_text) < 100:
                return []

            # Use LLM to extract founder names from search results
            system_prompt = (
                f"Extract the founder/co-founder names of '{company_name}' from the text below. "
                "Return ONLY a JSON object: {\"founders\": [\"Name 1\", \"Name 2\"]}. "
                "Only include actual founders/co-founders, not employees or investors. "
                "If no founders found, return {\"founders\": []}."
            )
            text, in_tok, out_tok = await self._extractor._llm.complete(
                model_key=self._extractor._founder_model,
                system_prompt=system_prompt,
                user_prompt=search_text[:15000],
            )
            self._extractor.token_usage.record(in_tok, out_tok, self._extractor._founder_model)

            # Parse response
            import json, re
            text = re.sub(r"^```(?:json)?\s*\n?", "", text.strip())
            text = re.sub(r"\n?```\s*$", "", text)
            data = json.loads(text)
            names = data.get("founders", [])
            return [{"full_name": name} for name in names if isinstance(name, str) and name.strip()]
        except Exception as exc:
            logger.warning("Founder discovery failed for '%s': %s", company_name, exc)
            return []

    # -- Enrichment ----------------------------------------------------------

    async def enrich_company(self, company: dict) -> dict:
        """Enrich a single company with detailed founder data.

        Processes up to MAX_CONCURRENT_ENRICHMENTS founders concurrently using
        asyncio.Semaphore to match LM Studio's continuous batching slots (4).
        """
        company_name = company.get("name", "Unknown")
        founded_year = company.get("founded_year")
        founders_raw = company.get("founders", [])

        # If no founders listed, try to discover them
        if not founders_raw:
            discovered = await self._discover_founders(company_name, company.get("website"))
            if discovered:
                logger.info("Discovered %d founders for '%s'", len(discovered), company_name)
                founders_raw = discovered
                company["founders"] = founders_raw
            else:
                return company

        # Separate founders that need enrichment from those that don't
        enrichment_sem = asyncio.Semaphore(MAX_CONCURRENT_ENRICHMENTS)

        async def _enrich_with_limit(founder_raw: dict) -> dict:
            founder_name = founder_raw.get("full_name", "")
            if not founder_name:
                return founder_raw

            async with enrichment_sem:
                try:
                    return await self._enrich_single_founder(
                        founder_name=founder_name,
                        founder_raw=founder_raw,
                        company_name=company_name,
                        founded_year=founded_year,
                    )
                except Exception as exc:
                    logger.error(
                        "Failed to enrich %r for %r: %s",
                        founder_name, company_name, exc,
                    )
                    return founder_raw

        # Fire off all founder enrichments concurrently (bounded by semaphore)
        enriched_founders = await asyncio.gather(
            *[_enrich_with_limit(f) for f in founders_raw]
        )

        company["founders"] = list(enriched_founders)
        return company

    async def _enrich_single_founder(
        self,
        founder_name: str,
        founder_raw: dict,
        company_name: str,
        founded_year: int | None,
    ) -> dict:
        """Enrich a single founder with search + LLM extraction.

        Optimization: tries company website /about and /team pages first to find
        founder info before falling back to expensive search + LLM cycle.
        """
        # Step 1: Try scraping company website for founder info (cheap/free)
        company_website = founder_raw.get("company_website") or ""
        website_text = ""
        if company_website:
            website_text = await self._scrape_company_about_page(company_website, founder_name)

        # Step 2: Fall back to search if website didn't yield enough info
        search_text = ""
        if len(website_text) < 200:
            search_text = await self.search_founder(founder_name, company_name)

        combined_text = "\n\n".join(filter(None, [website_text, search_text]))

        if not combined_text.strip():
            logger.warning("No search results for %r @ %r", founder_name, company_name)
            return founder_raw

        if self._extractor is None:
            return founder_raw

        # Pre-filter: only keep snippets that mention the founder's name (optimization #5)
        filtered_text = self._filter_relevant_snippets(combined_text, founder_name)

        extracted = await self._extractor.extract_founder_info(
            search_results=filtered_text,
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

    # -- Company website scraping (optimization #4) --------------------------

    async def _scrape_company_about_page(
        self, website_url: str, founder_name: str
    ) -> str:
        """Try to scrape /about or /team page from a company website.

        This is a cheap alternative to search+LLM: if the company's own website
        lists founder bios, we can skip the Exa/DDG search entirely.

        Returns extracted text if useful, empty string otherwise.
        """
        if not website_url:
            return ""

        # Normalize URL
        base_url = website_url.rstrip("/")
        if not base_url.startswith("http"):
            base_url = f"https://{base_url}"

        # Try common paths where founder info lives
        paths_to_try = ["/about", "/team", "/about-us", "/our-team", "/leadership"]

        async with httpx.AsyncClient(
            timeout=httpx.Timeout(10.0),
            follow_redirects=True,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/122.0.0.0 Safari/537.36"
                ),
            },
        ) as client:
            for path in paths_to_try:
                try:
                    url = f"{base_url}{path}"
                    resp = await client.get(url)
                    if resp.status_code != 200:
                        continue

                    # Extract text content (simple regex strip)
                    text = re.sub(r"<[^>]+>", " ", resp.text)
                    text = re.sub(r"\s+", " ", text).strip()

                    # Check if founder name appears in the page
                    name_parts = founder_name.lower().split()
                    if any(part in text.lower() for part in name_parts if len(part) > 2):
                        # Found relevant content — extract a reasonable chunk around the name
                        logger.info(
                            "Found founder info on %s for %r",
                            url, founder_name,
                        )
                        # Return up to 5K chars of relevant text
                        return text[:5000]

                except Exception as exc:
                    logger.debug("Failed to scrape %s%s: %s", base_url, path, exc)
                    continue

        return ""

    # -- Search result pre-filtering (optimization #5) -----------------------

    @staticmethod
    def _filter_relevant_snippets(text: str, founder_name: str) -> str:
        """Filter search results to only include snippets mentioning the founder.

        This reduces LLM input from ~30K chars to ~15K chars while keeping
        all relevant information. Safe because we only drop snippets that
        don't mention the founder at all.
        """
        if not text or not founder_name:
            return text[:MAX_SEARCH_TEXT_CHARS]

        snippets = text.split("\n\n---\n\n")
        name_parts = [p.lower() for p in founder_name.split() if len(p) > 2]
        last_name = founder_name.split()[-1].lower() if founder_name.split() else ""

        relevant: list[str] = []
        other: list[str] = []

        for snippet in snippets:
            snippet_lower = snippet.lower()
            # Check if any part of the founder's name appears
            if (
                last_name and last_name in snippet_lower
            ) or any(part in snippet_lower for part in name_parts):
                relevant.append(snippet)
            else:
                other.append(snippet)

        # Prioritize relevant snippets, then fill with others up to cap
        combined = "\n\n---\n\n".join(relevant)
        if len(combined) < MAX_SEARCH_TEXT_CHARS and other:
            remaining = MAX_SEARCH_TEXT_CHARS - len(combined)
            extra = "\n\n---\n\n".join(other)
            combined = combined + "\n\n---\n\n" + extra[:remaining]

        result = combined[:MAX_SEARCH_TEXT_CHARS]

        if len(text) > len(result):
            logger.debug(
                "Filtered search text for %r: %d -> %d chars (%.0f%% reduction)",
                founder_name,
                len(text),
                len(result),
                (1 - len(result) / len(text)) * 100,
            )

        return result

    # -- News / recent updates (Exa-powered) ---------------------------------

    async def fetch_company_news(
        self,
        company_name: str,
        days_back: int = 90,
    ) -> list[dict]:
        """Fetch recent news about a company using Exa semantic search.

        Returns structured news items: title, date, summary, url.
        Cost: ~$0.005 per company (1 Exa query).

        Useful for:
          - Funding round announcements
          - Acquisitions / exits
          - Product launches
          - Team changes
          - Shutdowns
        """
        if not self._exa:
            logger.info("Exa not configured; skipping news for %r", company_name)
            return []

        try:
            snippets = await self._exa.search_news(
                query=f"{company_name} startup funding news",
                days_back=days_back,
            )
            self._search_count += 1

            # Return raw snippets as structured news items
            news_items = []
            for snippet in snippets:
                lines = snippet.strip().split("\n")
                item = {"title": lines[0] if lines else "", "raw": snippet}
                # Try to extract date
                for line in lines:
                    if line.startswith("Published:"):
                        item["date"] = line.replace("Published:", "").strip()
                    if line.startswith("URL:"):
                        item["url"] = line.replace("URL:", "").strip()
                news_items.append(item)

            logger.info(
                "Fetched %d news items for %r (last %d days)",
                len(news_items), company_name, days_back,
            )
            return news_items

        except Exception as exc:
            logger.warning("Exa news search failed for %r: %s", company_name, exc)
            return []

    async def fetch_vc_news(
        self,
        vc_name: str,
        days_back: int = 30,
    ) -> list[dict]:
        """Fetch recent news about a VC firm (new funds, investments, exits).

        Cost: ~$0.005 per VC (1 Exa query).
        """
        if not self._exa:
            return []

        try:
            snippets = await self._exa.search_news(
                query=f"{vc_name} venture capital fund investment portfolio",
                days_back=days_back,
            )
            self._search_count += 1

            news_items = []
            for snippet in snippets:
                lines = snippet.strip().split("\n")
                item = {"title": lines[0] if lines else "", "raw": snippet}
                for line in lines:
                    if line.startswith("Published:"):
                        item["date"] = line.replace("Published:", "").strip()
                    if line.startswith("URL:"):
                        item["url"] = line.replace("URL:", "").strip()
                news_items.append(item)

            return news_items
        except Exception as exc:
            logger.warning("Exa VC news search failed for %r: %s", vc_name, exc)
            return []

    # -- Batch enrichment ----------------------------------------------------

    async def enrich_batch(self, companies: list[dict]) -> list[dict]:
        """Enrich a batch of companies.

        Each company's founders are enriched concurrently (up to 4 at a time),
        but companies are still processed sequentially to avoid overwhelming
        the search backends with too many concurrent requests.
        """
        enriched: list[dict] = []

        for i, company in enumerate(companies):
            logger.info(
                "Enriching %d/%d: %s",
                i + 1, len(companies), company.get("name", "Unknown"),
            )

            # Inject company website into each founder dict so _enrich_single_founder
            # can try the website before doing an expensive search
            website = company.get("website", "")
            if website:
                for f in company.get("founders", []):
                    if isinstance(f, dict) and not f.get("company_website"):
                        f["company_website"] = website

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
