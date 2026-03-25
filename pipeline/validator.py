"""
Pydantic schema validation and data quality scoring for the Meridian pipeline.

Defines structured models that mirror the Supabase database schema and provides
validation logic with confidence scoring for extracted VC/founder data.
"""

from __future__ import annotations

import logging
import re
from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator, model_validator

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

CURRENT_YEAR = 2026

VALID_STAGES = {
    "Pre-Seed", "Seed", "Early", "Series A", "Series B",
    "Series C", "Series D", "Series E", "Growth",
}

VALID_STATUSES = {"Active", "Acquired", "IPO", "Shutdown", "Unknown", "Exited", "Merged"}

VALID_ROLES = {"primary", "co-founder"}

VALID_EDUCATION_TIERS = {"Top-10", "Top-50", "Other"}

VALID_CONFIDENCE_LEVELS = {"High", "Medium", "Low"}

# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------


class VCFirm(BaseModel):
    """Represents a venture capital firm."""

    name: str = Field(..., min_length=1, max_length=200)
    slug: str = Field(..., min_length=1, max_length=200)
    website: Optional[str] = None
    description: Optional[str] = None
    hq_city: Optional[str] = None
    hq_country: Optional[str] = None
    hq_region: Optional[str] = None
    founded_year: Optional[int] = None
    aum_usd: Optional[int] = None
    fund_stage: list[str] = Field(default_factory=list)
    focus_sectors: list[str] = Field(default_factory=list)
    logo_url: Optional[str] = None
    linkedin_url: Optional[str] = None
    data_quality: str = "medium"

    @field_validator("slug")
    @classmethod
    def validate_slug(cls, v: str) -> str:
        if not re.match(r"^[a-z0-9]+(?:-[a-z0-9]+)*$", v):
            raise ValueError(f"Invalid slug format: {v!r}")
        return v

    @field_validator("founded_year")
    @classmethod
    def validate_founded_year(cls, v: int | None) -> int | None:
        if v is not None and (v < 1900 or v > CURRENT_YEAR):
            raise ValueError(f"Founded year {v} out of range [1900, {CURRENT_YEAR}]")
        return v

    @field_validator("data_quality")
    @classmethod
    def validate_data_quality(cls, v: str) -> str:
        if v not in {"high", "medium", "low"}:
            raise ValueError(f"data_quality must be high/medium/low, got {v!r}")
        return v

    @field_validator("website", "logo_url", "linkedin_url")
    @classmethod
    def validate_url(cls, v: str | None) -> str | None:
        if v is not None and not v.startswith(("http://", "https://")):
            raise ValueError(f"URL must start with http(s)://, got {v!r}")
        return v


class FundingRound(BaseModel):
    """Represents a single funding round for a portfolio company."""

    round_name: Optional[str] = None
    amount_usd: Optional[int] = None
    announced_date: Optional[date] = None
    lead_investor: Optional[str] = None
    co_investors: list[str] = Field(default_factory=list)
    valuation_pre_usd: Optional[int] = None
    valuation_post_usd: Optional[int] = None
    source_url: Optional[str] = None

    @field_validator("amount_usd", "valuation_pre_usd", "valuation_post_usd")
    @classmethod
    def validate_positive_amount(cls, v: int | None) -> int | None:
        if v is not None and v < 0:
            raise ValueError(f"Monetary value must be non-negative, got {v}")
        return v


class Founder(BaseModel):
    """Represents a founder of a portfolio company."""

    full_name: str = Field(..., min_length=1, max_length=300)
    role: str = "primary"
    est_birth_year: Optional[int] = None
    domain_exp_years: Optional[int] = None
    prior_founder: bool = False
    education_tier: Optional[str] = None
    university: Optional[str] = None
    degree: Optional[str] = None
    grad_year: Optional[int] = None
    age_at_founding: Optional[int] = None
    current_age_2026: Optional[int] = None
    age_confidence: str = "Low"
    age_inference_method: Optional[str] = None
    linkedin_url: Optional[str] = None
    twitter_url: Optional[str] = None
    nationality: Optional[str] = None
    source_notes: Optional[str] = None

    @field_validator("nationality", mode="before")
    @classmethod
    def normalize_nationality(cls, v):
        """Convert list to string (LLMs sometimes return ['Irish-American'])."""
        if isinstance(v, list):
            return ", ".join(str(x) for x in v) if v else None
        return v

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: str) -> str:
        # Normalize: lowercase, strip extra titles like "& CEO", "& CTO"
        normalized = v.lower().strip()
        normalized = re.sub(r"\s*&\s*(ceo|cto|coo|cfo|president|chairman|director).*", "", normalized)
        normalized = normalized.strip()
        if normalized in VALID_ROLES:
            return normalized
        # Map common variants
        role_map = {"founder": "primary", "cofounder": "co-founder", "co founder": "co-founder",
                    "ceo": "primary", "cto": "co-founder", "coo": "co-founder",
                    "cfo": "co-founder", "president": "primary", "managing partner": "primary"}
        if normalized in role_map:
            return role_map[normalized]
        # Default to primary instead of rejecting
        logger.warning("Unknown role %r, defaulting to 'primary'", v)
        return "primary"

    @field_validator("education_tier")
    @classmethod
    def validate_education_tier(cls, v: str | None) -> str | None:
        if v is not None and v not in VALID_EDUCATION_TIERS:
            raise ValueError(
                f"education_tier must be one of {VALID_EDUCATION_TIERS}, got {v!r}"
            )
        return v

    @field_validator("age_confidence")
    @classmethod
    def validate_age_confidence(cls, v: str) -> str:
        if v not in VALID_CONFIDENCE_LEVELS:
            raise ValueError(
                f"age_confidence must be one of {VALID_CONFIDENCE_LEVELS}, got {v!r}"
            )
        return v

    @field_validator("est_birth_year")
    @classmethod
    def validate_birth_year(cls, v: int | None) -> int | None:
        if v is not None and (v < 1940 or v > CURRENT_YEAR - 16):
            raise ValueError(
                f"est_birth_year {v} out of plausible range [1940, {CURRENT_YEAR - 16}]"
            )
        return v

    @field_validator("grad_year")
    @classmethod
    def validate_grad_year(cls, v: int | None) -> int | None:
        if v is not None and (v < 1960 or v > CURRENT_YEAR):
            raise ValueError(f"grad_year {v} out of range [1960, {CURRENT_YEAR}]")
        return v

    @field_validator("domain_exp_years")
    @classmethod
    def validate_exp_years(cls, v: int | None) -> int | None:
        if v is not None and (v < 0 or v > 60):
            raise ValueError(f"domain_exp_years {v} out of range [0, 60]")
        return v

    @model_validator(mode="after")
    def compute_derived_ages(self) -> "Founder":
        """Compute current_age_2026 and cross-validate age fields."""
        if self.est_birth_year is not None:
            self.current_age_2026 = CURRENT_YEAR - self.est_birth_year
        return self


class Investment(BaseModel):
    """Represents the many-to-many relationship between VCs and companies."""

    vc_slug: str = Field(..., min_length=1)
    company_slug: str = Field(..., min_length=1)
    stage: Optional[str] = None
    lead_investor: bool = False
    announced_date: Optional[date] = None
    source_url: Optional[str] = None

    @field_validator("stage")
    @classmethod
    def validate_stage(cls, v: str | None) -> str | None:
        if v is None or v in VALID_STAGES:
            return v
        # Default unknown stages to None instead of rejecting
        logger.warning("Unknown funding stage %r, defaulting to None", v)
        return None


class Company(BaseModel):
    """Represents a portfolio company with optional nested founders/rounds."""

    name: str = Field(..., min_length=1, max_length=300)
    slug: str = Field(..., min_length=1, max_length=300)
    sector: Optional[str] = None
    subsector: Optional[str] = None
    founded_year: Optional[int] = None
    city: Optional[str] = None
    country: Optional[str] = None
    region: Optional[str] = None
    stage: Optional[str] = None
    status: str = "Active"
    status_detail: Optional[str] = None
    website: Optional[str] = None
    description: Optional[str] = None
    total_raised_usd: Optional[int] = None
    valuation_usd: Optional[int] = None
    source_url: Optional[str] = None
    data_quality: str = "medium"

    # Nested data (not directly in portfolio_companies table, but carried through pipeline)
    founders: list[Founder] = Field(default_factory=list)
    funding_rounds: list[FundingRound] = Field(default_factory=list)

    @field_validator("slug")
    @classmethod
    def validate_slug(cls, v: str) -> str:
        if not re.match(r"^[a-z0-9]+(?:-[a-z0-9]+)*$", v):
            raise ValueError(f"Invalid slug format: {v!r}")
        return v

    @field_validator("stage")
    @classmethod
    def validate_stage(cls, v: str | None) -> str | None:
        if v is None or v in VALID_STAGES:
            return v
        # Normalize common LLM variants
        stage_map = {
            "pre-seed": "Pre-Seed", "preseed": "Pre-Seed", "angel": "Pre-Seed",
            "seed": "Seed", "seed stage": "Seed",
            "early": "Early", "early stage": "Early",
            "series a": "Series A", "a": "Series A",
            "series b": "Series B", "b": "Series B",
            "series c": "Series C", "c": "Series C",
            "series d": "Series D", "d": "Series D",
            "series e": "Series E", "e": "Series E",
            "growth": "Growth", "late stage": "Growth", "late": "Growth",
        }
        normalized = stage_map.get(v.lower().strip())
        if normalized:
            return normalized
        # Default to None for unknown stages instead of rejecting
        logger.warning("Unknown stage %r, defaulting to None", v)
        return None

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        if v in VALID_STATUSES:
            return v
        # Normalize common LLM variants
        status_map = {
            "acquired by": "Acquired",
            "acquired": "Acquired",
            "merged": "Acquired",
            "ipo": "IPO",
            "dpo": "IPO",
            "spac": "IPO",
            "public": "IPO",
            "listed": "IPO",
            "active": "Active",
            "operating": "Active",
            "private": "Active",
            "shutdown": "Shutdown",
            "closed": "Shutdown",
            "defunct": "Shutdown",
            "dead": "Shutdown",
            "unknown": "Unknown",
            "exited": "Exited",
            "exit": "Exited",
            "merged": "Merged",
        }
        normalized = status_map.get(v.lower().strip())
        if normalized:
            return normalized
        # If status contains "acquired", treat as Acquired
        if "acqui" in v.lower():
            return "Acquired"
        if "exit" in v.lower():
            return "Exited"
        # Default to Unknown instead of rejecting
        logger.warning("Unknown status %r, defaulting to 'Unknown'", v)
        return "Unknown"

    @field_validator("data_quality")
    @classmethod
    def validate_data_quality(cls, v: str) -> str:
        if v not in {"high", "medium", "low"}:
            raise ValueError(f"data_quality must be high/medium/low, got {v!r}")
        return v

    @field_validator("founded_year")
    @classmethod
    def validate_founded_year(cls, v: int | None) -> int | None:
        if v is not None and (v < 1980 or v > CURRENT_YEAR):
            raise ValueError(f"founded_year {v} out of range [1980, {CURRENT_YEAR}]")
        return v

    @field_validator("website", "source_url")
    @classmethod
    def validate_url(cls, v: str | None) -> str | None:
        if v is not None and not v.startswith(("http://", "https://")):
            raise ValueError(f"URL must start with http(s)://, got {v!r}")
        return v


# ---------------------------------------------------------------------------
# Validator class
# ---------------------------------------------------------------------------


class DataValidator:
    """Validates raw dicts against Pydantic models and scores data quality."""

    def validate_company(self, data: dict) -> tuple[Company | None, list[str]]:
        """Validate a raw company dict.

        Args:
            data: Raw dict with company fields.

        Returns:
            Tuple of (validated Company or None, list of warning messages).
        """
        warnings: list[str] = []
        try:
            company = Company(**data)
        except Exception as exc:
            logger.warning("Company validation failed for %r: %s", data.get("name"), exc)
            return None, [str(exc)]

        # Non-fatal warnings
        if company.founded_year is None:
            warnings.append("Missing founded_year")
        if company.sector is None:
            warnings.append("Missing sector")
        if company.website is None:
            warnings.append("Missing website")
        if company.description is None:
            warnings.append("Missing description")
        if not company.founders:
            warnings.append("No founders attached")

        # Set data_quality based on completeness
        filled = sum(
            1
            for field_name in ["sector", "founded_year", "city", "country", "website", "description", "stage"]
            if getattr(company, field_name) is not None
        )
        if filled >= 6:
            company.data_quality = "high"
        elif filled >= 3:
            company.data_quality = "medium"
        else:
            company.data_quality = "low"

        return company, warnings

    def validate_founder(self, data: dict) -> tuple[Founder | None, list[str]]:
        """Validate a raw founder dict.

        Args:
            data: Raw dict with founder fields.

        Returns:
            Tuple of (validated Founder or None, list of warning messages).
        """
        warnings: list[str] = []
        try:
            founder = Founder(**data)
        except Exception as exc:
            logger.warning("Founder validation failed for %r: %s", data.get("full_name"), exc)
            return None, [str(exc)]

        if founder.est_birth_year is None:
            warnings.append("Missing est_birth_year; age fields will be empty")
        if founder.linkedin_url is None:
            warnings.append("Missing LinkedIn URL")
        if founder.university is None:
            warnings.append("Missing university")

        # Auto-score age confidence
        founder.age_confidence = self.score_confidence(founder)

        return founder, warnings

    def score_confidence(self, founder: Founder) -> str:
        """Score the confidence level for a founder's age data.

        Scoring criteria:
            High  - birth year + at least one corroborating field (grad_year or LinkedIn)
            Medium - birth year present OR grad_year that allows inference
            Low   - neither birth year nor grad_year available

        Args:
            founder: Validated Founder instance.

        Returns:
            One of 'High', 'Medium', 'Low'.
        """
        has_birth_year = founder.est_birth_year is not None
        has_grad_year = founder.grad_year is not None
        has_linkedin = founder.linkedin_url is not None
        has_university = founder.university is not None

        if has_birth_year and (has_grad_year or has_linkedin):
            return "High"
        if has_birth_year or (has_grad_year and has_university):
            return "Medium"
        return "Low"

    def validate_batch(
        self, companies: list[dict]
    ) -> tuple[list[Company], list[dict]]:
        """Validate a batch of company dicts.

        Args:
            companies: List of raw company dicts.

        Returns:
            Tuple of (list of valid Company objects, list of rejected dicts with reasons).
        """
        validated: list[Company] = []
        rejected: list[dict] = []

        for raw in companies:
            company, warnings = self.validate_company(raw)
            if company is not None:
                # Also validate nested founders
                valid_founders: list[Founder] = []
                for f_data in raw.get("founders", []):
                    founder, f_warnings = self.validate_founder(f_data)
                    if founder is not None:
                        valid_founders.append(founder)
                    else:
                        logger.warning(
                            "Rejected founder %r for company %r: %s",
                            f_data.get("full_name"),
                            raw.get("name"),
                            f_warnings,
                        )
                company.founders = valid_founders
                validated.append(company)
                if warnings:
                    logger.info(
                        "Company %r validated with warnings: %s",
                        company.name,
                        warnings,
                    )
            else:
                rejected.append({"data": raw, "errors": warnings})
                logger.warning("Rejected company %r: %s", raw.get("name"), warnings)

        logger.info(
            "Validation complete: %d validated, %d rejected out of %d total",
            len(validated),
            len(rejected),
            len(companies),
        )
        return validated, rejected
