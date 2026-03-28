"""
Claude Sonnet-based founder age triangulation.

Uses multi-step reasoning to estimate a founder's birth year from heterogeneous
search results: explicit mentions → education graduation → career timeline →
cross-reference signals.
"""

from __future__ import annotations

import json
import logging
import os
import re
from typing import Any

from anthropic import AsyncAnthropic, APIConnectionError, RateLimitError
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from pipeline.models import AgeConfidence, FounderAgeResult

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

TRIANGULATOR_MODEL = "claude-sonnet-4-6"
MAX_SEARCH_CHARS = 60_000          # Max chars of search results to pass to Claude
MAX_OUTPUT_TOKENS = 2048
CURRENT_YEAR = 2026                # Hard-coded reference year matching schema


# ---------------------------------------------------------------------------
# Prompt
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """\
You are a biographical research specialist helping to estimate a founder's age for a VC intelligence database.

Your task is to estimate the founder's birth year by reasoning through the following evidence hierarchy — work through each step in order:

1. EXPLICIT age mention
   Look for a direct statement of age ("is 32 years old", "born in 1991", "turns 30 in 2024").
   If found with high certainty, stop here.

2. Education graduation year
   - Bachelor's degree: typically awarded at age 21–23 (use 22 as default).
   - Master's degree: typically at age 23–25 (use 24).
   - PhD: typically at age 27–30 (use 28).
   Use graduation year minus the appropriate age to get birth year.

3. Career first job / internship
   - First professional role typically starts at age 22–23.
   - If the earliest LinkedIn/résumé entry has a year, subtract 22.

4. Cross-reference signals
   - Forbes 30 Under 30 in year Y → birth year ≥ Y − 30.
   - "X years of experience" stated at a known year → approximate birth year.
   - Company founding year combined with typical career stage.

After reasoning, output ONLY a JSON object (no markdown) with exactly these keys:
{
  "est_birth_year": <integer or null>,
  "age_at_founding": <integer or null>,
  "current_age_2026": <integer or null>,
  "age_confidence": "High" | "Medium" | "Low",
  "age_inference_method": "<brief description of the primary method used>",
  "reasoning": "<step-by-step explanation of your reasoning>",
  "sources_used": ["<evidence type 1>", "<evidence type 2>", ...]
}

Rules:
- Be conservative. If you are uncertain, lower the confidence and widen your estimate.
- Do not guess purely from the founder's name or ethnicity.
- If you truly cannot estimate, set est_birth_year to null with confidence "Low".
- age_at_founding = founded_year - est_birth_year (compute only when both are known).
- current_age_2026 = 2026 - est_birth_year (compute only when est_birth_year is known).
- Output ONLY the JSON object — no prose, no markdown fences.\
"""


def _build_user_message(
    founder_name: str,
    search_results: str,
    founded_year: int | None,
    company_name: str,
) -> str:
    truncated = search_results[:MAX_SEARCH_CHARS]
    founded_str = str(founded_year) if founded_year else "Unknown"
    return (
        f"Founder name: {founder_name}\n"
        f"Company: {company_name}\n"
        f"Company founded year: {founded_str}\n\n"
        f"Search results:\n{truncated}"
    )


# ---------------------------------------------------------------------------
# Triangulator
# ---------------------------------------------------------------------------


def _get_client() -> AsyncAnthropic:
    """Return an AsyncAnthropic client using ANTHROPIC_API_KEY from env."""
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError(
            "ANTHROPIC_API_KEY environment variable is not set. "
            "Set it before calling triangulate_founder_age()."
        )
    return AsyncAnthropic(api_key=api_key)


def _parse_triangulation_response(
    raw_text: str,
    founder_name: str,
    company_name: str,
) -> FounderAgeResult:
    """Parse Claude's JSON response into a FounderAgeResult.

    Strips markdown code fences if present; returns a low-confidence
    FounderAgeResult on any parse failure so the pipeline can continue.
    """
    text = raw_text.strip()
    # Strip optional markdown fences
    text = re.sub(r"^```(?:json)?\s*\n?", "", text)
    text = re.sub(r"\n?```\s*$", "", text)
    text = text.strip()

    try:
        payload: dict[str, Any] = json.loads(text)
    except json.JSONDecodeError as exc:
        logger.error(
            "JSON parse error for founder %r: %s\nRaw (first 500): %s",
            founder_name,
            exc,
            raw_text[:500],
        )
        return FounderAgeResult(
            founder_name=founder_name,
            company_name=company_name,
            age_confidence="Low",
            age_inference_method="parse-error",
            reasoning=f"Could not parse Claude response: {exc}",
            raw_response=raw_text,
        )

    # Coerce types defensively
    est_birth_year = payload.get("est_birth_year")
    if est_birth_year is not None:
        try:
            est_birth_year = int(est_birth_year)
        except (TypeError, ValueError):
            est_birth_year = None

    age_at_founding = payload.get("age_at_founding")
    if age_at_founding is not None:
        try:
            age_at_founding = int(age_at_founding)
        except (TypeError, ValueError):
            age_at_founding = None

    current_age_2026 = payload.get("current_age_2026")
    if current_age_2026 is not None:
        try:
            current_age_2026 = int(current_age_2026)
        except (TypeError, ValueError):
            current_age_2026 = None

    raw_confidence = payload.get("age_confidence", "Low")
    confidence: AgeConfidence
    if raw_confidence in ("High", "Medium", "Low"):
        confidence = raw_confidence  # type: ignore[assignment]
    else:
        confidence = "Low"

    sources_used = payload.get("sources_used", [])
    if not isinstance(sources_used, list):
        sources_used = []

    return FounderAgeResult(
        founder_name=founder_name,
        company_name=company_name,
        est_birth_year=est_birth_year,
        age_at_founding=age_at_founding,
        current_age_2026=current_age_2026,
        age_confidence=confidence,
        age_inference_method=payload.get("age_inference_method"),
        reasoning=payload.get("reasoning"),
        sources_used=sources_used,
        raw_response=raw_text,
    )


@retry(
    retry=retry_if_exception_type((RateLimitError, APIConnectionError)),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=2, min=5, max=60),
    reraise=True,
)
async def triangulate_founder_age(
    founder_name: str,
    search_results: str,
    founded_year: int | None,
    company_name: str,
) -> FounderAgeResult:
    """Estimate a founder's birth year using Claude Sonnet.

    Uses a structured reasoning chain:
      explicit age mention → education graduation year →
      career first job → cross-reference signals.

    Retries up to 3 times on rate limit or connection errors with
    exponential backoff (5 s → 10 s → 60 s max).

    Args:
        founder_name: Full name of the founder.
        search_results: Concatenated text from web search results about
            the founder (will be truncated to 60k chars).
        founded_year: Year the company was founded; used to compute
            age_at_founding. Pass None if unknown.
        company_name: Name of the company (for context in the prompt).

    Returns:
        FounderAgeResult with best-effort age estimate and confidence level.

    Raises:
        anthropic.RateLimitError: After 3 retries on rate limit.
        anthropic.APIConnectionError: After 3 retries on connection error.
        ValueError: If ANTHROPIC_API_KEY is not set.
    """
    client = _get_client()
    user_message = _build_user_message(
        founder_name, search_results, founded_year, company_name
    )

    logger.info(
        "Triangulating age for founder %r (company=%r, founded=%s)",
        founder_name,
        company_name,
        founded_year,
    )

    response = await client.messages.create(
        model=TRIANGULATOR_MODEL,
        max_tokens=MAX_OUTPUT_TOKENS,
        system=SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": user_message,
            }
        ],
    )

    raw_text = response.content[0].text.strip()

    logger.info(
        "Triangulation complete for %r (tokens: in=%d, out=%d)",
        founder_name,
        response.usage.input_tokens,
        response.usage.output_tokens,
    )

    result = _parse_triangulation_response(raw_text, founder_name, company_name)

    # Log outcome summary
    logger.debug(
        "Result for %r: birth_year=%s, confidence=%s, method=%s",
        founder_name,
        result.est_birth_year,
        result.age_confidence,
        result.age_inference_method,
    )

    return result
