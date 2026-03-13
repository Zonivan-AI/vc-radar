"""
Claude API-based structured data extraction from HTML.

Uses Anthropic's Claude to parse raw HTML from VC portfolio pages and extract
structured company/founder data matching the Meridian database schema.
"""

from __future__ import annotations

import json
import logging
import os
import re
from pathlib import Path
from typing import Any

import anthropic
import yaml
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEFAULT_MODEL = "claude-sonnet-4-20250514"
MAX_HTML_CHARS = 180_000  # Claude context window safety margin
MAX_OUTPUT_TOKENS = 8192
PROMPTS_PATH = Path(__file__).resolve().parent.parent / "config" / "prompts.yaml"

# Cost per token (approximate for Claude 3.5 Sonnet)
COST_PER_INPUT_TOKEN = 3.0 / 1_000_000
COST_PER_OUTPUT_TOKEN = 15.0 / 1_000_000


# ---------------------------------------------------------------------------
# Token usage tracking
# ---------------------------------------------------------------------------


class TokenUsage:
    """Accumulates token usage across multiple API calls."""

    def __init__(self) -> None:
        self.input_tokens: int = 0
        self.output_tokens: int = 0
        self.api_calls: int = 0

    def record(self, usage: anthropic.types.Usage) -> None:
        """Record usage from a single API response."""
        self.input_tokens += usage.input_tokens
        self.output_tokens += usage.output_tokens
        self.api_calls += 1

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens

    @property
    def estimated_cost_usd(self) -> float:
        return (
            self.input_tokens * COST_PER_INPUT_TOKEN
            + self.output_tokens * COST_PER_OUTPUT_TOKEN
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "total_tokens": self.total_tokens,
            "api_calls": self.api_calls,
            "estimated_cost_usd": round(self.estimated_cost_usd, 4),
        }


# ---------------------------------------------------------------------------
# Prompt loader
# ---------------------------------------------------------------------------


def _load_prompts() -> dict[str, str]:
    """Load prompt templates from config/prompts.yaml.

    Returns a dict with keys like 'portfolio_extraction' and 'founder_extraction'.
    Falls back to built-in defaults if the file is missing.
    """
    if PROMPTS_PATH.exists():
        try:
            with open(PROMPTS_PATH, "r") as f:
                prompts = yaml.safe_load(f)
            logger.info("Loaded prompts from %s", PROMPTS_PATH)
            return prompts
        except Exception as exc:
            logger.warning("Failed to load prompts from %s: %s", PROMPTS_PATH, exc)

    logger.info("Using built-in default prompts")
    return {
        "portfolio_extraction": _DEFAULT_PORTFOLIO_PROMPT,
        "founder_extraction": _DEFAULT_FOUNDER_PROMPT,
    }


# ---------------------------------------------------------------------------
# Default prompts (fallback when prompts.yaml is missing)
# ---------------------------------------------------------------------------

_DEFAULT_PORTFOLIO_PROMPT = """You are a data extraction specialist. Given raw HTML from a VC firm's portfolio page, extract structured data about every portfolio company listed.

For each company, extract:
- name: Company name (required)
- slug: URL-friendly lowercase name with hyphens (e.g., "my-company")
- sector: Primary sector (e.g., AI, Fintech, Healthcare, SaaS, DeepTech, Climate, Consumer, Crypto, Enterprise, Biotech)
- subsector: More specific category if available
- description: One-line description of what the company does
- website: Company website URL if listed
- founded_year: Year founded (integer) if available
- city: Headquarters city if available
- country: Headquarters country if available
- stage: Investment stage if shown (Pre-Seed, Seed, Early, Series A, Series B, Series C, Series D, Series E, Growth)
- status: One of Active, Acquired, IPO, Shutdown, Unknown
- status_detail: Details like "Acquired by Google 2024" if available
- founders: Array of founder objects with:
  - full_name: Founder's full name
  - role: "primary" for the main/CEO founder, "co-founder" for others
- source_url: The URL this data was extracted from

Important guidelines:
- Only extract companies that are ACTUAL portfolio investments, not team members, events, or blog posts
- If a company name is ambiguous, include it with status "Unknown"
- Use null for any fields where the data is not available in the HTML
- Generate the slug from the company name: lowercase, replace spaces/special chars with hyphens

VC Firm name: {vc_name}
Source URL: {source_url}

Respond with ONLY a JSON array of company objects. No markdown formatting, no explanation."""

_DEFAULT_FOUNDER_PROMPT = """You are a data extraction specialist. Given search results about a founder, extract structured biographical and professional data.

Extract the following for the founder:
- full_name: Full name
- role: "primary" or "co-founder"
- est_birth_year: Estimated birth year (integer). Infer from:
  - Graduation year (typically age 22 for Bachelor's, 24 for Master's, 28 for PhD)
  - LinkedIn "X years of experience" (add ~22 to get birth year)
  - Direct mentions of age or birth year
  - Forbes 30 under 30 lists (if on 2023 list, born ~1993-2003)
- domain_exp_years: Years of experience in their domain
- prior_founder: true if they founded a previous company
- education_tier: "Top-10", "Top-50", or "Other" based on university ranking
- university: University name
- degree: Degree obtained
- grad_year: Graduation year (integer)
- age_at_founding: Age when they founded the company (if both birth year and founding year are known)
- age_inference_method: Brief explanation of how you estimated the birth year
- linkedin_url: LinkedIn profile URL if found
- twitter_url: Twitter/X profile URL if found
- nationality: Nationality or country of origin if available
- source_notes: Brief note about data sources used

Company name: {company_name}
Company founded year: {founded_year}

Important:
- Be conservative with age estimates. If uncertain, leave est_birth_year as null.
- For education_tier: Top-10 includes MIT, Stanford, Harvard, Caltech, Princeton, Chicago, Columbia, Penn, Yale, Berkeley. Top-50 includes other well-ranked institutions.
- Only set prior_founder to true if there is clear evidence of a previous startup.

Respond with ONLY a JSON object for this founder. No markdown formatting, no explanation."""


# ---------------------------------------------------------------------------
# Extractor
# ---------------------------------------------------------------------------


class DataExtractor:
    """Extracts structured VC portfolio data from HTML using Claude."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str = DEFAULT_MODEL,
    ) -> None:
        resolved_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not resolved_key:
            raise ValueError(
                "Anthropic API key required. Pass api_key or set ANTHROPIC_API_KEY."
            )
        self._client = anthropic.Anthropic(api_key=resolved_key)
        self._model = model
        self._prompts = _load_prompts()
        self.token_usage = TokenUsage()
        logger.info("DataExtractor initialized with model=%s", model)

    # -- Portfolio extraction ------------------------------------------------

    @retry(
        retry=retry_if_exception_type((anthropic.RateLimitError, anthropic.APIConnectionError)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=2, min=5, max=60),
        reraise=True,
    )
    async def extract_portfolio(
        self,
        html: str,
        vc_name: str,
        source_url: str = "",
    ) -> list[dict]:
        """Extract portfolio companies from raw HTML using Claude.

        Args:
            html: Raw HTML content from a VC portfolio page.
            vc_name: Name of the VC firm (for context in the prompt).
            source_url: URL the HTML was scraped from.

        Returns:
            List of dicts, each representing a portfolio company.
        """
        # Truncate HTML to fit within context window
        truncated_html = self._truncate_html(html)

        prompt_template = self._prompts.get(
            "portfolio_extraction", _DEFAULT_PORTFOLIO_PROMPT
        )
        system_prompt = prompt_template.format(
            vc_name=vc_name,
            source_url=source_url,
        )

        logger.info(
            "Extracting portfolio for %r from %d chars of HTML",
            vc_name,
            len(truncated_html),
        )

        response = self._client.messages.create(
            model=self._model,
            max_tokens=MAX_OUTPUT_TOKENS,
            system=system_prompt,
            messages=[
                {
                    "role": "user",
                    "content": f"Extract all portfolio companies from this HTML:\n\n{truncated_html}",
                }
            ],
        )

        self.token_usage.record(response.usage)

        raw_text = response.content[0].text.strip()
        companies = self._parse_json_response(raw_text, expected_type=list)

        logger.info(
            "Extracted %d companies for %r (tokens: in=%d, out=%d)",
            len(companies),
            vc_name,
            response.usage.input_tokens,
            response.usage.output_tokens,
        )
        return companies

    # -- Founder extraction --------------------------------------------------

    @retry(
        retry=retry_if_exception_type((anthropic.RateLimitError, anthropic.APIConnectionError)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=2, min=5, max=60),
        reraise=True,
    )
    async def extract_founder_info(
        self,
        search_results: str,
        company_name: str,
        founded_year: int | None = None,
    ) -> dict:
        """Extract structured founder data from search result text.

        Args:
            search_results: Concatenated text from search results about the founder.
            company_name: Name of the founder's company (for context).
            founded_year: Year the company was founded (for age-at-founding calculation).

        Returns:
            Dict of founder fields matching the Founder schema.
        """
        prompt_template = self._prompts.get(
            "founder_extraction", _DEFAULT_FOUNDER_PROMPT
        )
        system_prompt = prompt_template.format(
            company_name=company_name,
            founded_year=founded_year or "Unknown",
        )

        # Truncate search results if too long
        truncated_results = search_results[:60_000]

        logger.info(
            "Extracting founder info for company %r from %d chars of search results",
            company_name,
            len(truncated_results),
        )

        response = self._client.messages.create(
            model=self._model,
            max_tokens=MAX_OUTPUT_TOKENS,
            system=system_prompt,
            messages=[
                {
                    "role": "user",
                    "content": f"Extract founder information from these search results:\n\n{truncated_results}",
                }
            ],
        )

        self.token_usage.record(response.usage)

        raw_text = response.content[0].text.strip()
        founder_data = self._parse_json_response(raw_text, expected_type=dict)

        logger.info(
            "Extracted founder data for %r (tokens: in=%d, out=%d)",
            company_name,
            response.usage.input_tokens,
            response.usage.output_tokens,
        )
        return founder_data

    # -- Helpers -------------------------------------------------------------

    def _truncate_html(self, html: str) -> str:
        """Truncate HTML to fit within token limits.

        Strips script/style tags first, then truncates to MAX_HTML_CHARS.
        """
        # Remove script and style blocks to reduce noise
        cleaned = re.sub(
            r"<(script|style|noscript)[^>]*>.*?</\1>",
            "",
            html,
            flags=re.DOTALL | re.IGNORECASE,
        )
        # Remove HTML comments
        cleaned = re.sub(r"<!--.*?-->", "", cleaned, flags=re.DOTALL)
        # Collapse whitespace
        cleaned = re.sub(r"\s+", " ", cleaned)

        if len(cleaned) > MAX_HTML_CHARS:
            logger.debug(
                "Truncating HTML from %d to %d chars", len(cleaned), MAX_HTML_CHARS
            )
            cleaned = cleaned[:MAX_HTML_CHARS]

        return cleaned

    def _parse_json_response(
        self, text: str, expected_type: type = list
    ) -> list | dict:
        """Parse JSON from Claude's response, handling common formatting issues.

        Args:
            text: Raw text response from Claude.
            expected_type: Expected top-level type (list or dict).

        Returns:
            Parsed JSON as a list or dict.
        """
        # Strip markdown code fences if present
        text = re.sub(r"^```(?:json)?\s*\n?", "", text)
        text = re.sub(r"\n?```\s*$", "", text)
        text = text.strip()

        try:
            parsed = json.loads(text)
        except json.JSONDecodeError as exc:
            logger.error("JSON parse error: %s\nRaw text (first 500 chars): %s", exc, text[:500])
            return [] if expected_type is list else {}

        if not isinstance(parsed, expected_type):
            logger.warning(
                "Expected %s but got %s; wrapping/unwrapping",
                expected_type.__name__,
                type(parsed).__name__,
            )
            if expected_type is list and isinstance(parsed, dict):
                # Maybe a single object instead of array
                return [parsed]
            if expected_type is dict and isinstance(parsed, list) and len(parsed) == 1:
                return parsed[0]
            return [] if expected_type is list else {}

        return parsed
