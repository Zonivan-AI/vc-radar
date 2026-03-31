"""
Pipeline orchestrator that runs the full VC Radar data pipeline end-to-end.

Coordinates scraping, extraction, enrichment, validation, and database
persistence for VC portfolio data. Supports full runs, partial runs for
specific VCs, and resume-from-failure.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

# Load .env BEFORE importing pipeline modules so they pick up env vars
# (e.g., USE_CLOUD_ENRICHMENT, LMSTUDIO_API_URL)
_env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(_env_path)

from supabase import Client as SupabaseClient
from supabase import create_client

from pipeline.enricher import FounderEnricher
from pipeline.extractor import DataExtractor
from pipeline.scraper import VCScraper
from pipeline.validator import Company, DataValidator

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent
VC_LIST_PATH = PROJECT_ROOT / "config" / "vc_list.yaml"
ENV_PATH = PROJECT_ROOT / ".env"

# Pipeline run statuses
STATUS_RUNNING = "running"
STATUS_COMPLETED = "completed"
STATUS_FAILED = "failed"
STATUS_PARTIAL = "partial"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _generate_slug(name: str) -> str:
    """Generate a URL-friendly slug from a name."""
    slug = name.lower().strip()
    slug = re.sub(r"[^a-z0-9\s-]", "", slug)
    slug = re.sub(r"[\s]+", "-", slug)
    slug = re.sub(r"-+", "-", slug)
    return slug.strip("-")


def _setup_logging(verbose: bool = False) -> None:
    """Configure logging for the pipeline."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    # Quiet noisy libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("playwright").setLevel(logging.WARNING)


def _load_vc_configs(path: Path = VC_LIST_PATH) -> list[dict]:
    """Load VC firm configurations from vc_list.yaml.

    Expected YAML format::

        vcs:
          - slug: a16z
            name: Andreessen Horowitz
            website: https://a16z.com
            portfolio_urls:
              - https://a16z.com/portfolio
            focus_sectors: [ai, fintech, crypto]
            fund_stage: [seed, series_a, series_b]

    Returns:
        List of VC config dicts.
    """
    if not path.exists():
        logger.error("VC list config not found at %s", path)
        return []

    with open(path, "r") as f:
        data = yaml.safe_load(f)

    vcs = data.get("vcs", [])
    logger.info("Loaded %d VC configurations from %s", len(vcs), path)
    return vcs


# ---------------------------------------------------------------------------
# Pipeline run stats
# ---------------------------------------------------------------------------


class PipelineStats:
    """Tracks statistics for a single pipeline run."""

    def __init__(self, vc_id: str | None = None) -> None:
        self.vc_id = vc_id
        self.companies_found: int = 0
        self.companies_added: int = 0
        self.companies_updated: int = 0
        self.founders_added: int = 0
        self.errors_count: int = 0
        self.error_details: list[dict] = []
        self.tokens_used: int = 0
        self.cost_usd: float = 0.0
        self.started_at: datetime = datetime.now(timezone.utc)
        self.completed_at: datetime | None = None

    def record_error(self, stage: str, message: str, context: str = "") -> None:
        """Record an error that occurred during the pipeline."""
        self.errors_count += 1
        self.error_details.append(
            {"stage": stage, "message": message, "context": context}
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialize stats for database storage."""
        return {
            "companies_found": self.companies_found,
            "companies_added": self.companies_added,
            "companies_updated": self.companies_updated,
            "founders_added": self.founders_added,
            "errors_count": self.errors_count,
            "error_details": self.error_details,
            "tokens_used": self.tokens_used,
            "cost_usd": round(self.cost_usd, 4),
        }


# ---------------------------------------------------------------------------
# Scheduler
# ---------------------------------------------------------------------------


class PipelineScheduler:
    """Orchestrates the full VC Radar data pipeline.

    Pipeline stages:
        1. Scrape  - Playwright fetches JS-rendered portfolio pages
        2. Extract - Claude parses HTML into structured company data
        3. Enrich  - Serper + Claude add founder biographical details
        4. Validate - Pydantic models enforce schema + quality scoring
        5. Save    - Upsert validated data into Supabase

    Usage::

        scheduler = PipelineScheduler()
        await scheduler.run_full_pipeline()  # all VCs
        await scheduler.run_full_pipeline(vc_slugs=["a16z", "sequoia"])  # specific VCs
    """

    def __init__(self, skip_founders: bool = False) -> None:
        load_dotenv(ENV_PATH)

        self._skip_founders = skip_founders

        # Load VC configurations
        self._vc_configs = _load_vc_configs()

        # Initialize components (extractor no longer requires api_key positional arg)
        self._scraper = VCScraper()
        self._extractor = DataExtractor()
        self._enricher = FounderEnricher(extractor=self._extractor) if not skip_founders else None
        self._validator = DataValidator()

        # Initialize Supabase client
        supabase_url = os.environ.get("SUPABASE_URL", "")
        supabase_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
        if not supabase_url or not supabase_key:
            logger.warning(
                "Supabase credentials not configured. "
                "Database operations will fail."
            )
        self._supabase: SupabaseClient | None = None
        if supabase_url and supabase_key:
            self._supabase = create_client(supabase_url, supabase_key)

        logger.info(
            "PipelineScheduler initialized with %d VC configs",
            len(self._vc_configs),
        )

    # -- Full pipeline -------------------------------------------------------

    async def run_full_pipeline(
        self, vc_slugs: list[str] | None = None
    ) -> list[dict]:
        """Run the complete pipeline for all or specified VCs.

        Args:
            vc_slugs: Optional list of VC slugs to process. If None, all
                configured VCs are processed.

        Returns:
            List of result dicts, one per VC, with stats and outcomes.
        """
        # Filter VC configs
        if vc_slugs:
            slug_set = set(vc_slugs)
            configs = [c for c in self._vc_configs if c.get("slug") in slug_set]
            missing = slug_set - {c.get("slug") for c in configs}
            if missing:
                logger.warning("VC slugs not found in config: %s", missing)
        else:
            configs = self._vc_configs

        if not configs:
            logger.error("No VC configurations to process")
            return []

        logger.info(
            "Starting pipeline for %d VCs: %s",
            len(configs),
            [c.get("slug") for c in configs],
        )

        results: list[dict] = []

        try:
            for vc_config in configs:
                slug = vc_config.get("slug", "unknown")
                try:
                    # Init scraper fresh for each VC (closed after scraping to free
                    # network resources for LLM calls)
                    await self._scraper.init()
                    result = await self.run_single_vc(vc_config)
                    results.append(result)
                except Exception as exc:
                    logger.error("Pipeline failed for VC %r: %s", slug, exc)
                    results.append(
                        {
                            "vc_slug": slug,
                            "status": STATUS_FAILED,
                            "error": str(exc),
                        }
                    )
                finally:
                    await self._scraper.close()
        finally:
            if self._enricher:
                await self._enricher.close()
            await self._extractor.close()

        # Summary
        success = sum(1 for r in results if r.get("status") == STATUS_COMPLETED)
        logger.info(
            "Pipeline complete: %d/%d VCs succeeded. Total tokens: %d, est cost: $%.4f",
            success,
            len(results),
            self._extractor.token_usage.total_tokens,
            self._extractor.token_usage.estimated_cost_usd,
        )

        return results

    # -- Single VC -----------------------------------------------------------

    async def run_single_vc(self, vc_config: dict) -> dict:
        """Run the full pipeline for a single VC firm.

        Stages: scrape -> extract -> enrich -> validate -> save

        Args:
            vc_config: VC configuration dict from vc_list.yaml.

        Returns:
            Dict with pipeline results and statistics.
        """
        slug = vc_config.get("slug", "unknown")
        name = vc_config.get("name", slug)
        stats = PipelineStats(vc_id=slug)

        # Create pipeline run record
        run_id = await self._create_run_record(slug, stats)

        logger.info("=" * 60)
        logger.info("Processing VC: %s (%s)", name, slug)
        logger.info("=" * 60)

        try:
            # Stage 1: Scrape
            logger.info("[1/5] Scraping portfolio pages for %s", name)
            scrape_results = await self._scraper.scrape_batch([vc_config])
            if not scrape_results or not scrape_results[0].all_html:
                raise RuntimeError(f"No HTML content scraped for {slug}")
            html_content = scrape_results[0].all_html

            # Close browser before LLM calls to avoid connection conflicts
            await self._scraper.close()

            # Stage 2: Extract
            logger.info("[2/5] Extracting companies from HTML for %s", name)
            portfolio_urls = vc_config.get("portfolio_urls", [""])
            companies_raw = await self._extractor.extract_portfolio(
                html=html_content,
                vc_name=name,
                source_url=portfolio_urls[0] if portfolio_urls else "",
            )
            stats.companies_found = len(companies_raw)
            logger.info("Extracted %d companies for %s", len(companies_raw), name)

            if not companies_raw:
                logger.warning("No companies extracted for %s, ending early", name)
                stats.completed_at = datetime.now(timezone.utc)
                await self._update_run_record(run_id, STATUS_PARTIAL, stats)
                return {
                    "vc_slug": slug,
                    "status": STATUS_PARTIAL,
                    "stats": stats.to_dict(),
                }

            # Filter out non-dict entries (some models return strings instead of objects)
            companies_raw = [
                c if isinstance(c, dict) else {"name": str(c)}
                for c in companies_raw
                if c  # skip None/empty
            ]

            # Normalize field names (local LLMs sometimes use different keys)
            field_aliases = {
                "company_name": "name",
                "company": "name",
                "title": "name",
                "industry": "sector",
                "category": "sector",
                "url": "website",
                "homepage": "website",
                "site": "website",
                "desc": "description",
                "summary": "description",
                "about": "description",
            }
            for comp in companies_raw:
                if isinstance(comp, dict):
                    for alias, canonical in field_aliases.items():
                        if alias in comp and canonical not in comp:
                            comp[canonical] = comp.pop(alias)
                    # Normalize founders: convert string entries to dicts
                    if "founders" in comp and isinstance(comp["founders"], list):
                        normalized = []
                        for f in comp["founders"]:
                            if isinstance(f, str):
                                normalized.append({"full_name": f})
                            elif isinstance(f, dict):
                                # Normalize founder field names to match Founder model
                                for alias in ("name", "founder_name", "founder"):
                                    if alias in f and "full_name" not in f:
                                        f["full_name"] = f.pop(alias)
                                normalized.append(f)
                        comp["founders"] = normalized

            # Stage 3-5: Process each company granularly (validate → save → discover founders → save founders)
            logger.info("[3-5] Processing %d companies granularly (save as we go)", len(companies_raw))

            vc_db_id = await self._upsert_vc_firm(vc_config)
            total_added = 0
            total_updated = 0
            total_founders = 0

            for i, comp in enumerate(companies_raw):
                comp_name = comp.get("name", "Unknown")

                # 3a: Clean name + generate slug
                if comp.get("name"):
                    comp["name"] = re.sub(r"[*#@!&^%$]+$", "", comp["name"]).strip()
                if not comp.get("slug") and comp.get("name"):
                    comp["slug"] = _generate_slug(comp["name"])

                # 3b: Validate
                validated_company, warnings = self._validator.validate_company(comp)
                if validated_company is None:
                    stats.record_error("validation", str(warnings), context=comp_name)
                    continue

                # 3c: Save company immediately
                if vc_db_id and self._supabase:
                    company_id = await self._upsert_company(validated_company)
                    if company_id:
                        total_added += 1
                        await self._upsert_investment(
                            vc_id=vc_db_id,
                            company_id=company_id,
                            stage=validated_company.stage,
                        )
                        logger.info(
                            "[%d/%d] Saved company: %s",
                            i + 1, len(companies_raw), comp_name,
                        )

                        # 3d: Discover & save founders for this company
                        if not self._skip_founders and self._enricher:
                            try:
                                enriched = await self._enricher.enrich_company(comp)
                                founders_list = enriched.get("founders", [])
                                for f_raw in founders_list:
                                    if isinstance(f_raw, dict) and f_raw.get("full_name"):
                                        # Normalize role to string (Founder model expects string)
                                        if isinstance(f_raw.get("role"), dict):
                                            f_raw["role"] = f_raw["role"].get("title", "primary")
                                        elif not f_raw.get("role"):
                                            f_raw["role"] = "primary"
                                        try:
                                            from pipeline.validator import Founder
                                            founder_obj = Founder(**f_raw)
                                            founder_id = await self._upsert_founder(
                                                founder_obj, company_id
                                            )
                                            if founder_id:
                                                total_founders += 1
                                                logger.info(
                                                    "  Saved founder: %s",
                                                    founder_obj.full_name,
                                                )
                                        except Exception as fexc:
                                            logger.warning(
                                                "  Founder validation failed for %r: %s",
                                                f_raw.get("full_name"), fexc,
                                            )
                            except Exception as exc:
                                logger.warning(
                                    "  Enrichment failed for %s: %s", comp_name, exc,
                            )

            stats.companies_added = total_added
            stats.companies_updated = total_updated
            stats.founders_added = total_founders

            # Record token usage
            stats.tokens_used = self._extractor.token_usage.total_tokens
            stats.cost_usd = self._extractor.token_usage.estimated_cost_usd
            stats.completed_at = datetime.now(timezone.utc)

            status = STATUS_COMPLETED if not stats.errors_count else STATUS_PARTIAL
            await self._update_run_record(run_id, status, stats)

            logger.info(
                "VC %s complete: %d found, %d added, %d updated, %d founders, %d errors",
                slug,
                stats.companies_found,
                stats.companies_added,
                stats.companies_updated,
                stats.founders_added,
                stats.errors_count,
            )

            return {
                "vc_slug": slug,
                "status": status,
                "stats": stats.to_dict(),
            }

        except Exception as exc:
            stats.record_error("pipeline", str(exc), context=slug)
            stats.completed_at = datetime.now(timezone.utc)
            await self._update_run_record(run_id, STATUS_FAILED, stats)
            logger.error("Pipeline failed for VC %s: %s", slug, exc)
            raise

    # -- Database persistence ------------------------------------------------

    async def save_results(
        self,
        validated_companies: list[Company],
        vc_config: dict,
    ) -> dict[str, int]:
        """Save validated companies, founders, and investments to Supabase.

        Uses upsert semantics (ON CONFLICT UPDATE) to handle re-runs gracefully.

        Args:
            validated_companies: List of validated Company objects.
            vc_config: The VC configuration dict.

        Returns:
            Dict with counts of added/updated records.
        """
        if not self._supabase:
            logger.warning("Supabase not configured; skipping database save")
            return {"companies_added": 0, "companies_updated": 0, "founders_added": 0}

        counts = {"companies_added": 0, "companies_updated": 0, "founders_added": 0}
        vc_slug = vc_config.get("slug", "")

        # Ensure the VC firm exists
        vc_db_id = await self._upsert_vc_firm(vc_config)
        if not vc_db_id:
            logger.error("Failed to upsert VC firm %r, aborting save", vc_slug)
            return counts

        for company in validated_companies:
            try:
                company_id = await self._upsert_company(company)
                if not company_id:
                    continue

                # Create investment junction record
                await self._upsert_investment(
                    vc_id=vc_db_id,
                    company_id=company_id,
                    stage=company.stage,
                    source_url=company.source_url,
                )
                counts["companies_added"] += 1

                # Save founders
                for founder in company.founders:
                    founder_id = await self._upsert_founder(
                        founder=founder, company_id=company_id
                    )
                    if founder_id:
                        counts["founders_added"] += 1

                # Save funding rounds
                for fround in company.funding_rounds:
                    await self._upsert_funding_round(
                        funding_round=fround, company_id=company_id
                    )

            except Exception as exc:
                logger.error(
                    "Error saving company %r: %s", company.name, exc
                )

        logger.info(
            "Database save complete for VC %r: %s", vc_slug, counts
        )
        return counts

    async def _upsert_vc_firm(self, vc_config: dict) -> str | None:
        """Upsert a VC firm and return its database ID."""
        if not self._supabase:
            return None

        slug = vc_config.get("slug", "")
        name = vc_config.get("name", "")

        data = {
            "name": name,
            "slug": slug,
            "website": vc_config.get("website"),
            "fund_stage": vc_config.get("stage_focus", vc_config.get("fund_stage", [])),
            "focus_sectors": vc_config.get("focus_sectors", []),
            "hq_city": vc_config.get("hq_city"),
            "hq_country": vc_config.get("hq_country"),
            "hq_region": vc_config.get("hq_region"),
        }

        try:
            # Check if VC already exists by slug or name
            existing = (
                self._supabase.table("vc_firms")
                .select("id, slug")
                .or_(f"slug.eq.{slug},name.eq.{name}")
                .limit(1)
                .execute()
            )
            if existing.data:
                # Update existing record
                vc_id = existing.data[0]["id"]
                existing_slug = existing.data[0]["slug"]
                update_data = {k: v for k, v in data.items() if v is not None and k != "slug"}
                self._supabase.table("vc_firms").update(update_data).eq("id", vc_id).execute()
                logger.debug("Updated VC firm %r (%s) -> %s", slug, existing_slug, vc_id)
                return vc_id
            else:
                # Insert new
                result = (
                    self._supabase.table("vc_firms")
                    .insert(data)
                    .execute()
                )
                if result.data:
                    vc_id = result.data[0]["id"]
                    logger.debug("Inserted VC firm %r -> %s", slug, vc_id)
                    return vc_id
        except Exception as exc:
            logger.error("Failed to upsert VC firm %r: %s", data["slug"], exc)

        return None

    async def _upsert_company(self, company: Company) -> str | None:
        """Upsert a portfolio company and return its database ID."""
        if not self._supabase:
            return None

        data = {
            "name": company.name,
            "slug": company.slug,
            "sector": company.sector,
            "subsector": company.subsector,
            "founded_year": company.founded_year,
            "city": company.city,
            "country": company.country,
            "region": company.region,
            "stage": company.stage,
            "status": company.status,
            "status_detail": company.status_detail,
            "website": company.website,
            "description": company.description,
            "total_raised_usd": company.total_raised_usd,
            "valuation_usd": company.valuation_usd,
            "source_url": company.source_url,
            "data_quality": company.data_quality,
        }

        try:
            result = (
                self._supabase.table("portfolio_companies")
                .upsert(data, on_conflict="slug")
                .execute()
            )
            if result.data:
                company_id = result.data[0]["id"]
                logger.debug("Upserted company %r -> %s", company.slug, company_id)
                return company_id
        except Exception as exc:
            logger.error("Failed to upsert company %r: %s", company.slug, exc)

        return None

    async def _upsert_investment(
        self,
        vc_id: str,
        company_id: str,
        stage: str | None = None,
        source_url: str | None = None,
    ) -> None:
        """Upsert an investment junction record."""
        if not self._supabase:
            return

        data = {
            "vc_id": vc_id,
            "company_id": company_id,
            "stage": stage,
            "source_url": source_url,
        }

        try:
            self._supabase.table("investments").upsert(
                data, on_conflict="vc_id,company_id"
            ).execute()
            logger.debug("Upserted investment %s -> %s", vc_id, company_id)
        except Exception as exc:
            logger.error(
                "Failed to upsert investment vc=%s company=%s: %s",
                vc_id,
                company_id,
                exc,
            )

    async def _upsert_founder(
        self, founder: Any, company_id: str
    ) -> str | None:
        """Insert a founder record (no natural unique key, so insert-or-skip)."""
        if not self._supabase:
            return None

        data = {
            "company_id": company_id,
            "full_name": founder.full_name,
            "role": founder.role,
            "est_birth_year": founder.est_birth_year,
            "domain_exp_years": founder.domain_exp_years,
            "prior_founder": founder.prior_founder,
            "education_tier": founder.education_tier,
            "university": founder.university,
            "degree": founder.degree,
            "grad_year": founder.grad_year,
            "age_at_founding": founder.age_at_founding,
            "current_age_2026": founder.current_age_2026,
            "age_confidence": founder.age_confidence,
            "age_inference_method": founder.age_inference_method,
            "linkedin_url": founder.linkedin_url,
            "twitter_url": founder.twitter_url,
            "nationality": founder.nationality,
            "source_notes": founder.source_notes,
        }

        try:
            # Check if founder already exists for this company
            existing = (
                self._supabase.table("founders")
                .select("id")
                .eq("company_id", company_id)
                .eq("full_name", founder.full_name)
                .execute()
            )

            if existing.data:
                # Update existing founder
                founder_id = existing.data[0]["id"]
                self._supabase.table("founders").update(data).eq(
                    "id", founder_id
                ).execute()
                logger.debug("Updated founder %r -> %s", founder.full_name, founder_id)
                return founder_id
            else:
                # Insert new founder
                result = (
                    self._supabase.table("founders").insert(data).execute()
                )
                if result.data:
                    founder_id = result.data[0]["id"]
                    logger.debug(
                        "Inserted founder %r -> %s", founder.full_name, founder_id
                    )
                    return founder_id
        except Exception as exc:
            logger.error(
                "Failed to upsert founder %r: %s", founder.full_name, exc
            )

        return None

    async def _upsert_funding_round(
        self, funding_round: Any, company_id: str
    ) -> None:
        """Insert a funding round record."""
        if not self._supabase:
            return

        data = {
            "company_id": company_id,
            "round_name": funding_round.round_name,
            "amount_usd": funding_round.amount_usd,
            "announced_date": (
                funding_round.announced_date.isoformat()
                if funding_round.announced_date
                else None
            ),
            "lead_investor": funding_round.lead_investor,
            "co_investors": funding_round.co_investors,
            "valuation_pre_usd": funding_round.valuation_pre_usd,
            "valuation_post_usd": funding_round.valuation_post_usd,
            "source_url": funding_round.source_url,
        }

        try:
            self._supabase.table("funding_rounds").insert(data).execute()
            logger.debug(
                "Inserted funding round %r for company %s",
                funding_round.round_name,
                company_id,
            )
        except Exception as exc:
            logger.error(
                "Failed to insert funding round %r: %s",
                funding_round.round_name,
                exc,
            )

    # -- Pipeline run tracking -----------------------------------------------

    async def _create_run_record(
        self, vc_slug: str, stats: PipelineStats
    ) -> str | None:
        """Create a pipeline_runs record and return its ID."""
        if not self._supabase:
            return None

        # Look up VC ID from slug
        vc_id = None
        try:
            result = (
                self._supabase.table("vc_firms")
                .select("id")
                .eq("slug", vc_slug)
                .execute()
            )
            if result.data:
                vc_id = result.data[0]["id"]
        except Exception:
            pass

        data = {
            "vc_id": vc_id,
            "status": STATUS_RUNNING,
            "model_used": self._extractor._model,
            "started_at": stats.started_at.isoformat(),
        }

        try:
            result = self._supabase.table("pipeline_runs").insert(data).execute()
            if result.data:
                run_id = result.data[0]["id"]
                logger.debug("Created pipeline run %s for VC %s", run_id, vc_slug)
                return run_id
        except Exception as exc:
            logger.error("Failed to create pipeline run record: %s", exc)

        return None

    async def _update_run_record(
        self, run_id: str | None, status: str, stats: PipelineStats
    ) -> None:
        """Update a pipeline_runs record with final stats."""
        if not self._supabase or not run_id:
            return

        data = {
            "status": status,
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "companies_found": stats.companies_found,
            "companies_added": stats.companies_added,
            "companies_updated": stats.companies_updated,
            "founders_added": stats.founders_added,
            "errors_count": stats.errors_count,
            "error_details": stats.error_details,
            "tokens_used": stats.tokens_used,
            "cost_usd": round(stats.cost_usd, 4),
        }

        try:
            self._supabase.table("pipeline_runs").update(data).eq(
                "id", run_id
            ).execute()
            logger.debug("Updated pipeline run %s -> %s", run_id, status)
        except Exception as exc:
            logger.error("Failed to update pipeline run %s: %s", run_id, exc)

    def log_run(self, vc_id: str, stats: dict) -> None:
        """Log a pipeline run summary (convenience method for sync callers).

        Args:
            vc_id: VC slug identifier.
            stats: Stats dict from PipelineStats.to_dict().
        """
        logger.info(
            "Pipeline run for %s: found=%d, added=%d, updated=%d, "
            "founders=%d, errors=%d, tokens=%d, cost=$%.4f",
            vc_id,
            stats.get("companies_found", 0),
            stats.get("companies_added", 0),
            stats.get("companies_updated", 0),
            stats.get("founders_added", 0),
            stats.get("errors_count", 0),
            stats.get("tokens_used", 0),
            stats.get("cost_usd", 0),
        )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments for the pipeline."""
    parser = argparse.ArgumentParser(
        description="VC Radar Intelligence Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
Examples:
  # Run for all configured VCs
  python -m pipeline.scheduler

  # Run for specific VCs
  python -m pipeline.scheduler --vcs a16z sequoia

  # Verbose logging
  python -m pipeline.scheduler --vcs a16z --verbose

  # Dry run (validate config only)
  python -m pipeline.scheduler --dry-run
""",
    )
    parser.add_argument(
        "--vcs",
        nargs="*",
        default=None,
        help="VC slugs to process (default: all configured VCs)",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose/debug logging",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate configuration and exit without running the pipeline",
    )
    parser.add_argument(
        "--skip-founders",
        action="store_true",
        help="Skip founder enrichment (useful when Serper is out of credits)",
    )
    parser.add_argument(
        "--skip-existing",
        action="store_true",
        help="Skip VCs that already exist in the database",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=0,
        help="Process only this many VCs (0 = all)",
    )
    return parser.parse_args(argv)


async def async_main(args: argparse.Namespace) -> None:
    """Async entry point for the pipeline CLI."""
    _setup_logging(verbose=args.verbose)

    if args.dry_run:
        configs = _load_vc_configs()
        if not configs:
            logger.error("No VC configurations found. Create config/vc_list.yaml.")
            sys.exit(1)
        logger.info("Dry run: %d VC configs loaded successfully", len(configs))
        for cfg in configs:
            logger.info("  - %s (%s): %d URLs", cfg.get("name"), cfg.get("slug"), len(cfg.get("portfolio_urls", [])))
        return

    scheduler = PipelineScheduler(skip_founders=args.skip_founders)

    vc_slugs = args.vcs

    # --skip-existing: filter out VCs already in the database
    if args.skip_existing and scheduler._supabase:
        existing = scheduler._supabase.table("vc_firms").select("slug").execute()
        existing_slugs = {r["slug"] for r in existing.data}
        configs = _load_vc_configs()
        # Only keep VCs with portfolio_urls that aren't already in DB
        candidates = [
            c.get("slug") for c in configs
            if c.get("portfolio_urls") and c.get("slug") not in existing_slugs
        ]
        if vc_slugs:
            candidates = [s for s in candidates if s in set(vc_slugs)]
        vc_slugs = candidates
        logger.info("After --skip-existing filter: %d VCs to process", len(vc_slugs))

    # --batch-size: limit number of VCs processed
    if args.batch_size > 0 and vc_slugs:
        vc_slugs = vc_slugs[:args.batch_size]
        logger.info("Batch limited to %d VCs", len(vc_slugs))

    if vc_slugs is not None and len(vc_slugs) == 0:
        logger.info("No VCs to process (all existing or none match filters)")
        return

    results = await scheduler.run_full_pipeline(vc_slugs=vc_slugs)

    # Print summary
    for result in results:
        status = result.get("status", "unknown")
        slug = result.get("vc_slug", "?")
        stats = result.get("stats", {})
        if status == STATUS_COMPLETED:
            logger.info(
                "[OK] %s: %d companies, %d founders",
                slug,
                stats.get("companies_added", 0),
                stats.get("founders_added", 0),
            )
        elif status == STATUS_PARTIAL:
            logger.warning(
                "[PARTIAL] %s: %d companies, %d errors",
                slug,
                stats.get("companies_found", 0),
                stats.get("errors_count", 0),
            )
        else:
            logger.error("[FAILED] %s: %s", slug, result.get("error", "unknown"))


def main() -> None:
    """Synchronous entry point."""
    args = parse_args()
    asyncio.run(async_main(args))


if __name__ == "__main__":
    main()
