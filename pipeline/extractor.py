"""
Multi-provider LLM client for data extraction.

Supports OpenRouter (cheap OSS models), Anthropic (Claude), and direct
DeepSeek/Gemini APIs via OpenAI-compatible interface. Automatically selects
the cheapest viable model for each task.

Cost hierarchy (per 1M tokens, input/output):
  - Free tier (openrouter/free):       $0 / $0          (rate-limited)
  - DeepSeek V3:                       $0.25 / $0.38
  - Gemini Flash Lite:                 $0.25 / $1.50
  - Llama 3.3 70B (OpenRouter):        $0.10 / $0.10
  - Claude Sonnet:                     $3.00 / $15.00   (50-100x more expensive)
"""

from __future__ import annotations

import json
import logging
import os
import re
from enum import Enum
from pathlib import Path
from typing import Any

import httpx
import yaml
from bs4 import BeautifulSoup
from markdownify import markdownify as md
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

PROMPTS_PATH = Path(__file__).resolve().parent.parent / "config" / "prompts.yaml"
MAX_HTML_CHARS = 180_000
MAX_OUTPUT_TOKENS = 8192

# OpenRouter API
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"

# Local LM Studio API
LMSTUDIO_API_URL = os.environ.get("LMSTUDIO_API_URL", "http://192.168.1.4:1234/v1/chat/completions")


class ModelTier(Enum):
    """Model tiers ordered by cost (cheapest first)."""
    FREE = "free"
    CHEAP = "cheap"
    MID = "mid"
    PREMIUM = "premium"


# Model registry: (provider, model_id, input_cost_per_M, output_cost_per_M)
MODEL_REGISTRY = {
    # --- Local (free, runs on LM Studio) ---
    "local/gemma-3-12b": {
        "provider": "local",
        "model_id": "google/gemma-3-12b",
        "tier": ModelTier.FREE,
        "input_cost": 0.0,
        "output_cost": 0.0,
        "max_context": 131_072,
        "notes": "Gemma 3 12B — local via LM Studio, free, no reasoning overhead, 131K context",
    },
    "local/qwen2.5-coder-14b": {
        "provider": "local",
        "model_id": "qwen/qwen2.5-coder-14b",
        "tier": ModelTier.FREE,
        "input_cost": 0.0,
        "output_cost": 0.0,
        "max_context": 32_768,
        "notes": "Qwen 2.5 Coder 14B — local via LM Studio, free, no reasoning overhead",
    },
    # --- Free ---
    "openrouter/free": {
        "provider": "openrouter",
        "model_id": "openrouter/auto",  # auto-routes to free models
        "tier": ModelTier.FREE,
        "input_cost": 0.0,
        "output_cost": 0.0,
        "max_context": 128_000,
        "notes": "Rate-limited: 20 req/min, 200 req/day",
    },
    # --- Cheap ---
    "deepseek/deepseek-chat": {
        "provider": "openrouter",
        "model_id": "deepseek/deepseek-chat",
        "tier": ModelTier.CHEAP,
        "input_cost": 0.25,
        "output_cost": 0.38,
        "max_context": 128_000,
        "notes": "DeepSeek V3 — best cost/quality ratio",
    },
    "google/gemini-flash-1.5": {
        "provider": "openrouter",
        "model_id": "google/gemini-flash-1.5",
        "tier": ModelTier.CHEAP,
        "input_cost": 0.075,
        "output_cost": 0.30,
        "max_context": 1_000_000,
        "notes": "Gemini Flash — huge context, very cheap",
    },
    "meta-llama/llama-3.3-70b-instruct": {
        "provider": "openrouter",
        "model_id": "meta-llama/llama-3.3-70b-instruct",
        "tier": ModelTier.CHEAP,
        "input_cost": 0.10,
        "output_cost": 0.10,
        "max_context": 128_000,
        "notes": "Llama 3.3 70B — excellent for structured extraction",
    },
    "qwen/qwen-2.5-72b-instruct": {
        "provider": "openrouter",
        "model_id": "qwen/qwen-2.5-72b-instruct",
        "tier": ModelTier.CHEAP,
        "input_cost": 0.15,
        "output_cost": 0.15,
        "max_context": 128_000,
        "notes": "Qwen 2.5 72B — strong JSON/code extraction",
    },
    # --- Mid ---
    "anthropic/claude-haiku": {
        "provider": "openrouter",
        "model_id": "anthropic/claude-3.5-haiku",
        "tier": ModelTier.MID,
        "input_cost": 0.80,
        "output_cost": 4.00,
        "max_context": 200_000,
        "notes": "Claude Haiku — fast, good quality",
    },
    # --- Premium (fallback only) ---
    "anthropic/claude-sonnet": {
        "provider": "anthropic",
        "model_id": "claude-sonnet-4-20250514",
        "tier": ModelTier.PREMIUM,
        "input_cost": 3.00,
        "output_cost": 15.00,
        "max_context": 200_000,
        "notes": "Claude Sonnet — highest quality, highest cost",
    },
}

# Default model selections by task
# Strategy: all local — free, runs on LM Studio, no API costs
DEFAULT_MODELS = {
    "portfolio_extraction": "local/gemma-3-12b",           # HTML → companies JSON (free, local, ~2min)
    "founder_extraction": "local/gemma-3-12b",             # search text → founder JSON (free, local, ~90s)
    "fallback": "deepseek/deepseek-chat",                  # if local model fails, use cheap cloud
}


# ---------------------------------------------------------------------------
# Token usage tracking
# ---------------------------------------------------------------------------


class TokenUsage:
    """Accumulates token usage and estimated cost across API calls."""

    def __init__(self) -> None:
        self.input_tokens: int = 0
        self.output_tokens: int = 0
        self.api_calls: int = 0
        self._cost_usd: float = 0.0

    def record(self, input_tokens: int, output_tokens: int, model_key: str) -> None:
        """Record usage from a single API response."""
        self.input_tokens += input_tokens
        self.output_tokens += output_tokens
        self.api_calls += 1

        model = MODEL_REGISTRY.get(model_key, {})
        input_cost = model.get("input_cost", 3.0)
        output_cost = model.get("output_cost", 15.0)
        self._cost_usd += (
            input_tokens * input_cost / 1_000_000
            + output_tokens * output_cost / 1_000_000
        )

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens

    @property
    def estimated_cost_usd(self) -> float:
        return self._cost_usd

    def to_dict(self) -> dict[str, Any]:
        return {
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "total_tokens": self.total_tokens,
            "api_calls": self.api_calls,
            "estimated_cost_usd": round(self.estimated_cost_usd, 6),
        }


# ---------------------------------------------------------------------------
# Prompt loader
# ---------------------------------------------------------------------------


def _load_prompts() -> dict[str, Any]:
    """Load prompt templates from config/prompts.yaml."""
    if PROMPTS_PATH.exists():
        try:
            with open(PROMPTS_PATH, "r") as f:
                return yaml.safe_load(f) or {}
        except Exception as exc:
            logger.warning("Failed to load prompts: %s", exc)
    return {}


# ---------------------------------------------------------------------------
# Default prompts
# ---------------------------------------------------------------------------

_DEFAULT_PORTFOLIO_PROMPT = """You are a data extraction specialist. Given raw HTML from a VC firm's portfolio page, extract structured data about every portfolio company listed.

For each company, extract:
- name: Company name (required)
- slug: URL-friendly lowercase name with hyphens
- sector: Primary sector (AI, Fintech, Healthcare, SaaS, DeepTech, Climate, Consumer, Crypto, Enterprise, Biotech)
- description: One-line description
- website: Company website URL if listed
- founded_year: Year founded (integer) if available
- city: HQ city
- country: HQ country
- stage: Investment stage (Pre-Seed, Seed, Series A, Series B, Series C, Series D, Growth)
- status: Active, Acquired, IPO, Shutdown, or Unknown
- founders: Array of {full_name, role} objects (role: "primary" or "co-founder")

Only extract ACTUAL portfolio investments, not team members or blog posts.
Use null for unavailable fields. Generate slug from company name.

VC Firm: {vc_name}
Source: {source_url}

Respond with ONLY a JSON array. No markdown, no explanation."""

_DEFAULT_FOUNDER_PROMPT = """Extract structured biographical data for this founder from search results.

Extract:
- full_name, role ("primary"/"co-founder")
- est_birth_year (integer, infer from graduation +22, experience +22, Forbes lists, etc.)
- domain_exp_years, prior_founder (boolean)
- education_tier ("Top-10"/"Top-50"/"Other"), university, degree, grad_year
- age_at_founding, age_inference_method
- linkedin_url, twitter_url, nationality

Company: {company_name} (founded {founded_year})

Be conservative with age estimates. Use null if uncertain.
Respond with ONLY a JSON object. No markdown."""


# ---------------------------------------------------------------------------
# Multi-provider LLM Client
# ---------------------------------------------------------------------------


class LLMClient:
    """Unified client that routes to OpenRouter or Anthropic based on model."""

    def __init__(self) -> None:
        self._openrouter_key = os.environ.get("OPENROUTER_API_KEY", "")
        self._anthropic_key = os.environ.get("ANTHROPIC_API_KEY", "")
        self._http_client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._http_client is None or self._http_client.is_closed:
            self._http_client = httpx.AsyncClient(timeout=httpx.Timeout(120.0))
        return self._http_client

    async def close(self) -> None:
        if self._http_client and not self._http_client.is_closed:
            await self._http_client.aclose()

    @retry(
        retry=retry_if_exception_type((httpx.HTTPStatusError, httpx.ConnectError)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=2, min=3, max=30),
        reraise=True,
    )
    async def complete(
        self,
        model_key: str,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = MAX_OUTPUT_TOKENS,
    ) -> tuple[str, int, int]:
        """Send a completion request to the appropriate provider.

        Returns:
            Tuple of (response_text, input_tokens, output_tokens).
        """
        model_info = MODEL_REGISTRY.get(model_key)
        if not model_info:
            raise ValueError(f"Unknown model: {model_key}")

        provider = model_info["provider"]
        model_id = model_info["model_id"]

        if provider == "local":
            return await self._call_local(model_id, system_prompt, user_prompt, max_tokens)
        elif provider == "openrouter":
            return await self._call_openrouter(model_id, system_prompt, user_prompt, max_tokens)
        elif provider == "anthropic":
            return await self._call_anthropic(model_id, system_prompt, user_prompt, max_tokens)
        else:
            raise ValueError(f"Unknown provider: {provider}")

    async def _call_local(
        self, model_id: str, system: str, user: str, max_tokens: int
    ) -> tuple[str, int, int]:
        """Call local LM Studio's OpenAI-compatible API (free).

        Uses sync httpx in a thread executor to avoid asyncio event loop
        conflicts with Playwright's browser keepalive connections.
        """
        import asyncio
        import concurrent.futures

        def _sync_call() -> dict:
            response = httpx.post(
                LMSTUDIO_API_URL,
                headers={"Content-Type": "application/json"},
                json={
                    "model": model_id,
                    "max_tokens": max_tokens,
                    "temperature": 0.0,
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user", "content": user},
                    ],
                },
                timeout=600.0,  # 10 min — local models are slow but free
            )
            response.raise_for_status()
            return response.json()

        loop = asyncio.get_event_loop()
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            data = await loop.run_in_executor(pool, _sync_call)

        text = data["choices"][0]["message"].get("content", "")
        # GLM reasoning models wrap output in <|begin_of_box|>...<|end_of_box|> tags
        if "<|begin_of_box|>" in text:
            text = text.split("<|begin_of_box|>", 1)[1]
            text = text.split("<|end_of_box|>", 1)[0]
        # Strip markdown code fences (common with Qwen coder models)
        text = re.sub(r"^```(?:json)?\s*\n?", "", text.strip())
        text = re.sub(r"\n?```\s*$", "", text)
        text = text.strip()
        usage = data.get("usage", {})
        return text, usage.get("prompt_tokens", 0), usage.get("completion_tokens", 0)

    async def _call_openrouter(
        self, model_id: str, system: str, user: str, max_tokens: int
    ) -> tuple[str, int, int]:
        """Call OpenRouter's OpenAI-compatible API."""
        if not self._openrouter_key:
            raise ValueError("OPENROUTER_API_KEY not set")

        client = await self._get_client()
        response = await client.post(
            OPENROUTER_API_URL,
            headers={
                "Authorization": f"Bearer {self._openrouter_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://vc-radar.app",
                "X-Title": "VC Radar Pipeline",
            },
            json={
                "model": model_id,
                "max_tokens": max_tokens,
                "temperature": 0.0,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                "response_format": {"type": "json_object"},
            },
        )
        response.raise_for_status()
        data = response.json()

        text = data["choices"][0]["message"]["content"]
        usage = data.get("usage", {})
        return (
            text,
            usage.get("prompt_tokens", 0),
            usage.get("completion_tokens", 0),
        )

    async def _call_anthropic(
        self, model_id: str, system: str, user: str, max_tokens: int
    ) -> tuple[str, int, int]:
        """Call Anthropic's Claude API directly."""
        if not self._anthropic_key:
            raise ValueError("ANTHROPIC_API_KEY not set")

        # Import lazily so anthropic is optional when using OpenRouter only
        import anthropic

        client = anthropic.Anthropic(api_key=self._anthropic_key)
        response = client.messages.create(
            model=model_id,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        return (
            response.content[0].text.strip(),
            response.usage.input_tokens,
            response.usage.output_tokens,
        )


# ---------------------------------------------------------------------------
# DataExtractor (refactored for multi-provider)
# ---------------------------------------------------------------------------


class DataExtractor:
    """Extracts structured VC portfolio data using the cheapest viable model.

    Cost comparison for processing 1 VC (~50k tokens input, ~4k output):
      - Claude Sonnet:  ~$0.21 per VC  → $210 for 1000 VCs
      - DeepSeek V3:    ~$0.014 per VC → $14 for 1000 VCs  (15x cheaper)
      - Llama 3.3 70B:  ~$0.005 per VC → $5 for 1000 VCs   (42x cheaper)
      - Free tier:      ~$0.00 per VC  → $0 (rate-limited)
    """

    def __init__(
        self,
        portfolio_model: str | None = None,
        founder_model: str | None = None,
        fallback_model: str | None = None,
    ) -> None:
        self._llm = LLMClient()
        self._prompts = _load_prompts()
        self.token_usage = TokenUsage()

        # Model selection (env vars override defaults)
        self._portfolio_model = (
            portfolio_model
            or os.environ.get("PIPELINE_PORTFOLIO_MODEL")
            or DEFAULT_MODELS["portfolio_extraction"]
        )
        self._founder_model = (
            founder_model
            or os.environ.get("PIPELINE_FOUNDER_MODEL")
            or DEFAULT_MODELS["founder_extraction"]
        )
        self._fallback_model = (
            fallback_model
            or os.environ.get("PIPELINE_FALLBACK_MODEL")
            or DEFAULT_MODELS["fallback"]
        )

        # Expose model name for scheduler's pipeline_runs record
        self._model = self._portfolio_model

        logger.info(
            "DataExtractor initialized: portfolio=%s, founder=%s, fallback=%s",
            self._portfolio_model,
            self._founder_model,
            self._fallback_model,
        )

    async def close(self) -> None:
        await self._llm.close()

    # -- Portfolio extraction ------------------------------------------------

    async def extract_portfolio(
        self,
        html: str,
        vc_name: str,
        source_url: str = "",
    ) -> list[dict]:
        """Extract portfolio companies from raw HTML."""
        # Limit markdown to fit in model's context window
        # After markdown conversion, ~1.2 chars/token; reserve 4K tokens for prompt + output
        model_info = MODEL_REGISTRY.get(self._portfolio_model, {})
        max_ctx = model_info.get("max_context", 128_000)
        # Conservative: assume ~1.2 chars per token for markdown text
        html_char_limit = min(MAX_HTML_CHARS, int((max_ctx - 4000) * 1.2))
        truncated_html = self._truncate_html(html, max_chars=html_char_limit)

        prompt_template = self._prompts.get(
            "portfolio_extraction", {}
        )
        if isinstance(prompt_template, dict):
            system_prompt = prompt_template.get("system", _DEFAULT_PORTFOLIO_PROMPT)
        else:
            system_prompt = str(prompt_template) if prompt_template else _DEFAULT_PORTFOLIO_PROMPT

        system_prompt = system_prompt.format(
            vc_name=vc_name,
            source_url=source_url,
        )

        logger.info(
            "Extracting portfolio for %r (%d chars HTML) using %s",
            vc_name,
            len(truncated_html),
            self._portfolio_model,
        )

        # Try cheap model first, fallback on failure
        try:
            text, in_tok, out_tok = await self._llm.complete(
                model_key=self._portfolio_model,
                system_prompt=system_prompt,
                user_prompt=f"Extract all portfolio companies from this HTML:\n\n{truncated_html}",
            )
            self.token_usage.record(in_tok, out_tok, self._portfolio_model)
        except Exception as exc:
            logger.warning(
                "Primary model %s failed for %r: %s. Trying fallback %s",
                self._portfolio_model,
                vc_name,
                exc,
                self._fallback_model,
            )
            text, in_tok, out_tok = await self._llm.complete(
                model_key=self._fallback_model,
                system_prompt=system_prompt,
                user_prompt=f"Extract all portfolio companies from this HTML:\n\n{truncated_html}",
            )
            self.token_usage.record(in_tok, out_tok, self._fallback_model)

        companies = self._parse_json_response(text, expected_type=list)
        logger.info(
            "Extracted %d companies for %r (tokens: in=%d, out=%d)",
            len(companies), vc_name, in_tok, out_tok,
        )
        return companies

    # -- Founder extraction --------------------------------------------------

    async def extract_founder_info(
        self,
        search_results: str,
        company_name: str,
        founded_year: int | None = None,
    ) -> dict:
        """Extract structured founder data from search result text."""
        prompt_template = self._prompts.get(
            "founder_extraction", {}
        )
        if isinstance(prompt_template, dict):
            system_prompt = prompt_template.get("system", _DEFAULT_FOUNDER_PROMPT)
        else:
            system_prompt = str(prompt_template) if prompt_template else _DEFAULT_FOUNDER_PROMPT

        system_prompt = system_prompt.format(
            company_name=company_name,
            founded_year=founded_year or "Unknown",
        )

        truncated = search_results[:60_000]

        try:
            text, in_tok, out_tok = await self._llm.complete(
                model_key=self._founder_model,
                system_prompt=system_prompt,
                user_prompt=f"Extract founder information:\n\n{truncated}",
            )
            self.token_usage.record(in_tok, out_tok, self._founder_model)
        except Exception as exc:
            logger.warning(
                "Founder model %s failed: %s. Trying fallback.", self._founder_model, exc
            )
            text, in_tok, out_tok = await self._llm.complete(
                model_key=self._fallback_model,
                system_prompt=system_prompt,
                user_prompt=f"Extract founder information:\n\n{truncated}",
            )
            self.token_usage.record(in_tok, out_tok, self._fallback_model)

        return self._parse_json_response(text, expected_type=dict)

    # -- HTML preprocessing (aggressive cost reduction) ----------------------

    def _truncate_html(self, html: str, max_chars: int = MAX_HTML_CHARS) -> str:
        """Convert HTML to clean Markdown for minimal token usage.

        This is the #1 cost lever — converting 500KB HTML to ~2-10KB Markdown
        preserves ALL company data while cutting tokens by 50-350x.
        Falls back to regex stripping if markdownify/bs4 fail.
        """
        try:
            return self._html_to_markdown(html, max_chars)
        except Exception as exc:
            logger.warning("Markdown conversion failed (%s), falling back to regex", exc)
            return self._regex_strip_html(html, max_chars)

    def _html_to_markdown(self, html: str, max_chars: int) -> str:
        """Convert HTML to clean Markdown using BeautifulSoup + markdownify."""
        soup = BeautifulSoup(html, "html.parser")

        # Remove non-content tags
        for tag in soup.find_all(
            ["script", "style", "noscript", "svg", "head", "footer",
             "nav", "iframe", "form", "button", "input", "select"]
        ):
            tag.decompose()

        # Remove images, video, audio (we only want text data)
        for tag in soup.find_all(["img", "figure", "picture", "video", "audio", "canvas"]):
            tag.decompose()

        # Convert to markdown
        markdown = md(
            str(soup),
            strip=["img", "figure", "picture", "video", "audio", "canvas"],
        )

        # Clean up excessive whitespace
        markdown = re.sub(r"\n{3,}", "\n\n", markdown)
        markdown = re.sub(r" {2,}", " ", markdown)
        markdown = markdown.strip()

        # Safety truncation (should rarely trigger with markdown)
        if len(markdown) > max_chars:
            logger.warning(
                "Markdown still large (%d chars), truncating to %d",
                len(markdown), max_chars,
            )
            markdown = markdown[:max_chars]

        return markdown

    def _regex_strip_html(self, html: str, max_chars: int) -> str:
        """Fallback: regex-based HTML stripping if markdown conversion fails."""
        cleaned = re.sub(
            r"<(script|style|noscript|svg|path|meta|link|head)[^>]*>.*?</\1>",
            "", html, flags=re.DOTALL | re.IGNORECASE,
        )
        cleaned = re.sub(r"<!--.*?-->", "", cleaned, flags=re.DOTALL)
        cleaned = re.sub(r'\s+data-[a-z-]+="[^"]*"', "", cleaned)
        cleaned = re.sub(r'\s+class="[^"]*"', "", cleaned)
        cleaned = re.sub(r'\s+style="[^"]*"', "", cleaned)
        cleaned = re.sub(r"<\w+[^>]*>\s*</\w+>", "", cleaned)
        cleaned = re.sub(r"\s+", " ", cleaned)
        cleaned = re.sub(r"\n\s*\n", "\n", cleaned)

        if len(cleaned) > max_chars:
            cleaned = cleaned[:max_chars]

        return cleaned.strip()

    # -- JSON parsing --------------------------------------------------------

    def _parse_json_response(
        self, text: str, expected_type: type = list
    ) -> list | dict:
        """Parse JSON from LLM response, handling common formatting issues."""
        # Strip markdown code fences
        text = re.sub(r"^```(?:json)?\s*\n?", "", text)
        text = re.sub(r"\n?```\s*$", "", text)
        text = text.strip()

        # Some models wrap in {"result": [...]} or {"companies": [...]}
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError as exc:
            logger.error("JSON parse error: %s\nFirst 500 chars: %s", exc, text[:500])
            return [] if expected_type is list else {}

        # Unwrap common wrapper patterns
        if isinstance(parsed, dict) and expected_type is list:
            # Check for {"companies": [...]} or {"results": [...]} patterns
            for key in ("companies", "results", "data", "portfolio", "items"):
                if key in parsed and isinstance(parsed[key], list):
                    return parsed[key]
            # Single object → wrap in list
            return [parsed]

        if isinstance(parsed, list) and expected_type is dict and len(parsed) == 1:
            return parsed[0]

        if not isinstance(parsed, expected_type):
            return [] if expected_type is list else {}

        return parsed
