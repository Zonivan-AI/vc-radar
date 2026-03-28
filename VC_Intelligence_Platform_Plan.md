# vc-radar — Platform Execution Plan
### Claude Code Implementation Sprint — Build Everything Today

> **Repository**: [github.com/Zonivan-AI/vc-radar](https://github.com/Zonivan-AI/vc-radar)
> **License**: MIT
> **Vision**: The go-to open-source dashboard for tracking AI VC investments in North America. Who's investing, in what, at what stage, and who they back (founder profile analytics). Eventually: match your startup to the right VCs.
> **Implementation**: Everything below is built in a single Claude Code session today — all tracks running in parallel.

---

## Version Pinning — Latest & Secure (as of March 2026)

All tooling must use the versions below. No exceptions — these are the latest stable, security-patched releases.

```
Runtime / Language:
  Python              3.13.x          (latest stable, significant perf + security improvements)
  Node.js             22.x LTS        (Active LTS — security patches guaranteed through 2027)

Frontend:
  Next.js             15.x            (App Router stable, Turbopack default, React 19 support)
  React               19.x            (concurrent features, improved hydration, RSC stable)
  TypeScript          5.8.x           (latest — satisfies / infer improvements)
  Tailwind CSS        4.x             (oxide engine — 10× faster builds, no config file)
  Framer Motion       12.x            (layout animations, gesture improvements)
  Recharts            2.x             (latest stable)
  D3.js               7.x             (latest stable)
  Mapbox GL JS        3.x             (WebGL2 default, improved performance)
  Supabase JS         2.x             (latest stable)

Python Pipeline:
  exa-py              1.x             (latest SDK)
  openai              1.x             (latest — used pointed at OpenRouter)
  anthropic           0.40.x+         (latest Claude SDK)
  supabase            2.x             (latest Python client)
  pydantic            2.x             (V2 — Rust-backed validation, 5-50× faster than V1)
  playwright          1.x             (latest stable, Chromium/Firefox/Webkit)
  openpyxl            3.x             (latest stable)
  httpx               0.27.x          (async HTTP — replaces requests)
  tenacity            9.x             (retry logic with exponential backoff)
  structlog           24.x            (structured JSON logging)
  python-dotenv       1.x             (env management)

Infrastructure:
  Supabase            Latest (hosted) (free tier: 500MB)
  Vercel              Latest (hosted) (free tier, auto-deploys)
  GitHub Actions      ubuntu-24.04    (latest runner)
  PostHog             Latest (hosted) (free open-source analytics)
```

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                        vc-radar Architecture                         │
│                                                                     │
│  DATA LAYER                  APP LAYER              INFRA LAYER     │
│  ──────────                  ─────────              ──────────      │
│                                                                     │
│  [vc_list.yaml]              [Next.js 15]           [Vercel]        │
│       │                           │                     │           │
│       ▼                     [Supabase JS]          [GitHub Actions] │
│  [scraper.py]  ◄── Exa            │                     │           │
│       │                     [Recharts/D3]          [Weekly Cron]    │
│       ▼                           │                                 │
│  [extractor.py] ◄── OpenRouter    ▼                                 │
│       │           (Deepseek V3)  [Supabase PostgreSQL]              │
│       ▼                           ▲                                 │
│  [enricher.py]  ◄── Exa Search    │                                 │
│       │                      [validator.py]                         │
│       ▼                           ▲                                 │
│  [triangulator.py] ◄── Claude     │                                 │
│       │                      [pydantic v2]                          │
│       ▼                                                             │
│  [validator.py]                                                     │
│       │                                                             │
│       ▼                                                             │
│  [Supabase DB] ──► [json_exporter.py] ──► [dashboard/public/data/] │
│                ──► [excel_exporter.py] ──► [exports/*.xlsx]         │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Agentic Data Pipeline (Phase 1)

### Why the Pipeline Exists

Right now, every new company requires: manual website fetch → manual founder research → manual Python edit → rebuild. That's 20–40 minutes per VC firm with 10+ companies each. For 20 VCs × 15 companies = 300 companies, that's days of manual work. The pipeline eliminates this entirely.

### Full Pipeline Flow

```
┌─────────────────────────────────────────────────────────────┐
│                   AGENTIC PIPELINE FLOW                      │
│                                                             │
│  [vc_list.yaml]                                             │
│      │                                                      │
│      ▼                                                      │
│  [Exa get_contents(url)] ──► Clean text from VC site        │
│      │                       (handles JS-rendered sites)    │
│      │  If Exa fails ──► [Playwright fallback]              │
│      ▼                                                      │
│  [OpenRouter — Deepseek V3] ──► Extract: company name,      │
│      │                          sector, stage, city, year   │
│      ▼                                                      │
│  [Exa search(company_name)] ──► Find founder info from      │
│      │                          press coverage, Wikipedia,  │
│      │                          public profiles             │
│      ▼                                                      │
│  [OpenRouter — Tiered Model] ──► Structure founder data     │
│      │   Simple extraction → Deepseek V3 (cheap)           │
│      │   Age triangulation → Claude Sonnet (accurate)       │
│      ▼                                                      │
│  [Pydantic V2 Validator] ──► Schema check, reject bad data  │
│      │                                                      │
│      ▼                                                      │
│  [Supabase — PostgreSQL] ──► Persist all data               │
│      │                                                      │
│      ▼                                                      │
│  [Exporter] ──► Excel (.xlsx) + JSON + CSV                  │
└─────────────────────────────────────────────────────────────┘
```

### Tech Stack

**Core:**
- Python 3.13+ (type hints throughout, async/await everywhere)
- `exa-py` — URL crawling + semantic search (replaces both Firecrawl and Serper)
- `playwright` — fallback only for sites Exa can't handle
- `openai` SDK v1.x pointed at OpenRouter base URL — all cheap LLM calls
- `anthropic` SDK latest — used directly only for complex founder age triangulation
- `supabase-py` v2 — database
- `pydantic` v2 — strict data validation before any DB insert (Rust-backed, fast)
- `openpyxl` — Excel export
- `httpx` — async HTTP client (replaces `requests`)
- `tenacity` — retry with exponential backoff on all API calls
- `structlog` — structured JSON logging for every pipeline run

**Why Exa over Serper/Firecrawl:**
- Exa does both jobs: `get_contents(url)` fetches and cleans any webpage (what Firecrawl did), and `search(query)` finds semantically relevant founder info (what Serper did)
- Single API, single key, simpler pipeline
- Semantic search finds founder age from press coverage far more accurately than keyword-based Google search
- Free tier: 1,000 requests/month. After that ~$4/1K requests

**Why OpenRouter over direct Claude API (for cheap tasks):**
- Access to 100+ models through one API key and one SDK
- Deepseek V3 at $0.27/1M tokens handles all straightforward JSON extraction
- Built-in model fallbacks — if Deepseek fails, automatically retries with next model
- Claude Sonnet reserved only for complex founder age triangulation (multi-step reasoning)
- 10–15× cheaper than routing everything through Claude

### Tiered Model Strategy

```
Task                              Model                    Why
──────────────────────────────────────────────────────────────────────
Portfolio page → JSON             Deepseek V3 (OpenRouter)  Clear, deterministic
Founder name/company extraction   Deepseek V3 (OpenRouter)  Pattern matching
Founder age triangulation         Claude Sonnet             Multi-step reasoning
Edge cases / ambiguous data       Claude Sonnet             Nuanced judgment
SEC filing parsing                Deepseek V3 (OpenRouter)  Structured extraction
Match explanation generation      Deepseek V3 (OpenRouter)  Simple text generation
Embedding generation              text-embedding-3-small    Via OpenRouter
```

### Cost Estimate per Full Run (20 VCs, ~300 companies)

```
Exa get_contents (20 VC sites):      20 × $0.004  = $0.08
Exa search (300 founder searches):   300 × $0.004 = $1.20
Deepseek V3 extraction (80% tasks):  ~9M tokens × $0.00027 = $2.43
Claude Sonnet (20% hard cases):       ~1M tokens × $0.003  = $0.30
Playwright fallback:                  Free
                                      ──────────────────────
Total per full run:                   ~$4.00
Monthly (weekly updates):             ~$16/month
```

Compared to Crunchbase Enterprise ($30–50K/yr) or PitchBook — essentially free.

---

## Full File/Folder Structure

```
vc-radar/                           ← github.com/Zonivan-AI/vc-radar
├── README.md
├── LICENSE                         # MIT
├── .env.example
├── .python-version                 # 3.13.x — pinned via pyenv
├── .nvmrc                          # 22.x LTS — pinned for dashboard
├── .github/
│   ├── workflows/
│   │   ├── data-pipeline.yml       # Weekly automated data update
│   │   ├── ci.yml                  # Lint + type-check on every PR
│   │   └── deploy.yml              # Vercel deploy on push to main
│   └── CONTRIBUTING.md
│
├── pipeline/
│   ├── pyproject.toml              # Python deps (uv / pip-tools)
│   ├── requirements.txt            # Pinned versions
│   ├── scraper.py                  # Exa get_contents + Playwright fallback
│   ├── extractor.py                # OpenRouter (Deepseek V3) portfolio extraction
│   ├── enricher.py                 # Exa search for founder info
│   ├── triangulator.py             # Claude Sonnet for age reasoning
│   ├── validator.py                # Pydantic V2 schema validation
│   ├── scheduler.py                # Async orchestrator — runs full pipeline
│   └── models.py                   # Shared Pydantic models (single source of truth)
│
├── config/
│   ├── vc_list.yaml                # Community-editable VC list
│   └── prompts.yaml                # All LLM prompts, versioned
│
├── database/
│   ├── schema.sql                  # Full Supabase schema (8 tables)
│   ├── seed.py                     # Import existing 142 rows from Excel
│   └── migrations/                 # Future schema changes
│       └── 001_initial.sql
│
├── exporters/
│   ├── excel_exporter.py           # Generates .xlsx (backward compat)
│   └── json_exporter.py            # Generates data.json for dashboard
│
├── sec/
│   ├── sec_parser.py               # SEC EDGAR Form D fetcher + parser
│   └── fund_tracker.py             # VC fundraise feed builder
│
├── matching/
│   ├── embedder.py                 # Generate + store portfolio embeddings
│   ├── matcher.py                  # Cosine similarity scoring
│   └── explainer.py                # Deepseek V3 match explanations
│
├── dashboard/                      # Next.js 15 frontend
│   ├── package.json
│   ├── tsconfig.json
│   ├── next.config.ts
│   ├── tailwind.config.ts          # Tailwind v4 (oxide engine)
│   ├── app/
│   │   ├── layout.tsx              # Root layout, PostHog provider
│   │   ├── page.tsx                # Overview — stats, age histogram, sector donut
│   │   ├── explore/
│   │   │   ├── vcs/
│   │   │   │   ├── page.tsx        # VC directory with filters
│   │   │   │   └── [slug]/
│   │   │   │       └── page.tsx    # VC deep dive
│   │   │   ├── companies/
│   │   │   │   └── page.tsx        # Company database
│   │   │   └── founders/
│   │   │       └── page.tsx        # Founder age analytics
│   │   ├── trends/
│   │   │   └── page.tsx            # Sector stream chart, timeline
│   │   ├── fundraises/
│   │   │   └── page.tsx            # VC fund raises (Phase 3)
│   │   └── match/
│   │       └── page.tsx            # Startup–VC matching (Phase 3)
│   ├── components/
│   │   ├── charts/
│   │   │   ├── AgeHistogram.tsx
│   │   │   ├── SectorDonut.tsx
│   │   │   ├── InvestmentTimeline.tsx
│   │   │   ├── NetworkGraph.tsx    # D3-force
│   │   │   ├── BubbleUniverse.tsx  # D3 bubble chart
│   │   │   ├── VCDnaRadar.tsx      # Radar chart per VC
│   │   │   ├── SankeyFlow.tsx      # D3 Sankey — VC → Sector → Company
│   │   │   ├── GeoHeatmap.tsx      # Mapbox GL JS
│   │   │   └── SectorStream.tsx    # D3 streamgraph
│   │   ├── tables/
│   │   │   ├── CompanyTable.tsx
│   │   │   ├── VCTable.tsx
│   │   │   └── FounderTable.tsx
│   │   └── ui/
│   │       ├── FilterBar.tsx
│   │       ├── SearchInput.tsx
│   │       ├── StatCard.tsx
│   │       └── VCCard.tsx
│   └── lib/
│       ├── supabase.ts             # Supabase JS v2 client
│       ├── queries.ts              # All DB query functions
│       └── utils.ts
│
└── exports/
    └── VC_Founder_Age_Analysis.xlsx  ← Seed data, kept in sync by pipeline
```

---

## Extraction Code Pattern

```python
# pipeline/extractor.py — OpenRouter with Deepseek V3 for all simple tasks
# Python 3.13+, async throughout, Pydantic V2, tenacity retries

from __future__ import annotations
import asyncio
import json
import os
from typing import Any

import httpx
from openai import AsyncOpenAI          # openai v1.x SDK
from pydantic import BaseModel, Field
from tenacity import retry, stop_after_attempt, wait_exponential
import structlog

log = structlog.get_logger()

router_client = AsyncOpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.environ["OPENROUTER_API_KEY"],
    http_client=httpx.AsyncClient(timeout=60.0),
)


class PortfolioCompany(BaseModel):
    name: str
    sector: str | None = None
    stage: str | None = None
    founded_year: int | None = None
    city: str | None = None
    country: str | None = None
    status: str = "active"


class PortfolioExtractionResult(BaseModel):
    companies: list[PortfolioCompany] = Field(default_factory=list)
    confidence: str = "medium"


PORTFOLIO_EXTRACTION_PROMPT = """
You are extracting structured VC portfolio data from webpage text.

Webpage content:
{page_content}

Extract ALL portfolio companies. For each return:
- name: company name
- sector: specific sector (e.g. "AI Coding Assistant" not just "AI")
- stage: investment stage if visible
- founded_year: if visible
- city: headquarters city
- country: country code (e.g. "USA", "CAN", "GBR")
- status: active/acquired/ipo/unknown

Return as JSON: {{"companies": [...], "confidence": "high|medium|low"}}
Never invent data. Use null for missing fields.
"""


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
async def extract_portfolio(page_content: str) -> PortfolioExtractionResult:
    log.info("extracting_portfolio", content_length=len(page_content))
    response = await router_client.chat.completions.create(
        model="deepseek/deepseek-chat",   # Deepseek V3 via OpenRouter
        messages=[{"role": "user", "content": PORTFOLIO_EXTRACTION_PROMPT.format(
            page_content=page_content[:12000]   # token budget
        )}],
        response_format={"type": "json_object"},
        temperature=0.1,
    )
    raw = json.loads(response.choices[0].message.content)
    return PortfolioExtractionResult(**raw)
```

```python
# pipeline/triangulator.py — Claude direct for complex multi-step age reasoning
# Only called when Deepseek V3 confidence is low or founder is ambiguous

from __future__ import annotations
import json
import os

from anthropic import AsyncAnthropic
from pydantic import BaseModel
from tenacity import retry, stop_after_attempt, wait_exponential
import structlog

log = structlog.get_logger()

claude = AsyncAnthropic()   # reads ANTHROPIC_API_KEY from env


class FounderAgeResult(BaseModel):
    est_birth_year: int | None = None
    age_at_founding: int | None = None
    confidence: str = "low"
    method: str = ""
    reasoning: str = ""


FOUNDER_AGE_PROMPT = """
Based on these search results about {founder_name}, estimate their birth year.

Search results:
{search_results}

Use this reasoning chain:
1. Look for explicit age or birth year mentions
2. Check education: grad year → subtract 22 for undergrad, 27 for PhD
3. Check career: first job year → typical age for that role/seniority
4. Cross-reference multiple independent signals
5. Note contradictions and resolve them

Return JSON:
- est_birth_year: integer or null if genuinely unknown
- age_at_founding: est_birth_year subtracted from {founded_year}
- confidence: high / medium / low
- method: how you determined this (1-2 sentences)
- reasoning: full step-by-step logic

Be conservative. If genuinely uncertain, say low confidence.
"""


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
async def triangulate_founder_age(
    founder_name: str,
    search_results: str,
    founded_year: int,
) -> FounderAgeResult:
    log.info("triangulating_age", founder=founder_name, founded_year=founded_year)
    response = await claude.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=600,
        messages=[{"role": "user", "content": FOUNDER_AGE_PROMPT.format(
            founder_name=founder_name,
            search_results=search_results[:8000],
            founded_year=founded_year,
        )}]
    )
    raw = json.loads(response.content[0].text)
    return FounderAgeResult(**raw)
```

```python
# pipeline/scraper.py — Exa handles both URL fetching AND founder search
# Playwright is fallback only — spun up lazily

from __future__ import annotations
import os

from exa_py import Exa
from tenacity import retry, stop_after_attempt, wait_exponential
import structlog

log = structlog.get_logger()

exa = Exa(api_key=os.environ["EXA_API_KEY"])


@retry(stop=stop_after_attempt(2), wait=wait_exponential(min=2, max=8))
def fetch_vc_portfolio_page(url: str) -> str:
    """Fetch and clean a VC portfolio page (replaces Firecrawl)."""
    log.info("fetching_portfolio_page", url=url)
    result = exa.get_contents([url], text=True)
    text = result.results[0].text if result.results else ""
    if len(text) < 200:
        log.warning("exa_returned_sparse_content", url=url, length=len(text))
        return playwright_fallback(url)
    return text


@retry(stop=stop_after_attempt(2), wait=wait_exponential(min=2, max=8))
def search_founder_info(founder_name: str, company_name: str) -> str:
    """Semantic search for founder background (replaces Serper)."""
    log.info("searching_founder", founder=founder_name, company=company_name)
    results = exa.search(
        f"{founder_name} founder {company_name} age education background biography",
        num_results=5,
        use_autoprompt=True,
        text=True,
    )
    return "\n\n---\n\n".join([r.text for r in results.results if r.text])


def playwright_fallback(url: str) -> str:
    """Last resort for JS-heavy sites Exa can't handle."""
    log.warning("using_playwright_fallback", url=url)
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(user_agent="Mozilla/5.0 (compatible; vc-radar-bot/1.0)")
        page = ctx.new_page()
        page.goto(url, wait_until="networkidle", timeout=30000)
        page.wait_for_timeout(2000)
        content = page.inner_text("body")
        browser.close()
    return content
```

```python
# pipeline/models.py — Pydantic V2 shared models (single source of truth)

from __future__ import annotations
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class VCFirm(BaseModel):
    id: int | None = None
    name: str
    slug: str
    portfolio_url: str
    focus: list[str] = Field(default_factory=list)
    stage_focus: list[str] = Field(default_factory=list)
    hq_city: str | None = None
    hq_country: str = "USA"
    region: str | None = None


class Company(BaseModel):
    id: int | None = None
    vc_firm_id: int
    name: str
    sector: str
    city: str | None = None
    country: str | None = None
    region: str | None = None
    founded_year: int | None = None
    investment_stage: str | None = None
    status: Literal["active", "acquired", "ipo", "dead", "unknown"] = "active"
    primary_founder: str | None = None
    co_founders: str | None = None
    est_birth_year: int | None = None
    domain_exp_years: int | None = None
    prior_founder: bool | None = None
    education_tier: str | None = None
    age_confidence: Literal["high", "medium", "low"] | None = None
    age_inference_method: str | None = None
    source_notes: str | None = None
    last_updated: datetime = Field(default_factory=datetime.utcnow)

    @field_validator("founded_year")
    @classmethod
    def validate_year(cls, v: int | None) -> int | None:
        if v is not None and not (1990 <= v <= 2026):
            raise ValueError(f"founded_year {v} is out of plausible range")
        return v

    @field_validator("est_birth_year")
    @classmethod
    def validate_birth_year(cls, v: int | None) -> int | None:
        if v is not None and not (1950 <= v <= 2000):
            raise ValueError(f"est_birth_year {v} is out of plausible range")
        return v
```

```python
# pipeline/scheduler.py — async orchestrator, runs full pipeline end-to-end

from __future__ import annotations
import asyncio
import time
import yaml
from pathlib import Path

import structlog
from supabase import create_client, Client

from scraper import fetch_vc_portfolio_page, search_founder_info
from extractor import extract_portfolio
from enricher import enrich_with_founder_data
from triangulator import triangulate_founder_age
from validator import validate_and_deduplicate
from models import VCFirm, Company

log = structlog.get_logger()


async def process_vc(vc: dict, db: Client) -> int:
    """Full pipeline for a single VC firm. Returns count of companies upserted."""
    log.info("processing_vc", vc=vc["name"])
    start = time.monotonic()

    # 1. Fetch portfolio page
    page_text = fetch_vc_portfolio_page(vc["portfolio_url"])

    # 2. Extract companies with Deepseek V3
    extraction = await extract_portfolio(page_text)
    log.info("extracted_companies", vc=vc["name"], count=len(extraction.companies))

    # 3. For each company, enrich + triangulate founder age
    enriched: list[Company] = []
    tasks = [enrich_company(company, vc, db) for company in extraction.companies]
    enriched = await asyncio.gather(*tasks, return_exceptions=False)

    # 4. Validate and upsert to Supabase
    valid = validate_and_deduplicate(enriched, db)
    for company in valid:
        db.table("companies").upsert(company.model_dump(exclude_none=True)).execute()

    elapsed = time.monotonic() - start
    log.info("vc_complete", vc=vc["name"], upserted=len(valid), elapsed_s=round(elapsed, 1))
    return len(valid)


async def enrich_company(company, vc: dict, db: Client) -> Company:
    """Enrich a single company with founder info and age triangulation."""
    if not company.name:
        return None

    # Search for founder info via Exa
    founder_info = search_founder_info(company.name, vc["name"])

    # Use Deepseek V3 first for simple extraction
    founder_data = await extract_founder_basic(founder_info, company.name)

    # Escalate to Claude Sonnet only if confidence is low
    if founder_data.get("confidence") == "low" and company.founded_year:
        age_result = await triangulate_founder_age(
            founder_name=founder_data.get("primary_founder", ""),
            search_results=founder_info,
            founded_year=company.founded_year,
        )
        founder_data.update(age_result.model_dump())

    return Company(
        vc_firm_id=vc["id"],
        name=company.name,
        sector=company.sector or "Unknown",
        city=company.city,
        country=company.country or "USA",
        founded_year=company.founded_year,
        investment_stage=company.stage,
        status=company.status,
        primary_founder=founder_data.get("primary_founder"),
        est_birth_year=founder_data.get("est_birth_year"),
        age_confidence=founder_data.get("confidence"),
        age_inference_method=founder_data.get("method"),
        source_notes=founder_data.get("reasoning"),
    )


async def run_pipeline() -> None:
    """Main entry point — processes all VCs in parallel (configurable concurrency)."""
    vc_list = yaml.safe_load(Path("../config/vc_list.yaml").read_text())["vcs"]
    db = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_KEY"])

    log.info("pipeline_start", vc_count=len(vc_list))

    # Run all VCs with controlled concurrency (max 5 at a time to respect rate limits)
    semaphore = asyncio.Semaphore(5)
    async def bounded(vc):
        async with semaphore:
            return await process_vc(vc, db)

    results = await asyncio.gather(*[bounded(vc) for vc in vc_list])
    total = sum(r for r in results if isinstance(r, int))
    log.info("pipeline_complete", total_upserted=total)


if __name__ == "__main__":
    import os
    from dotenv import load_dotenv
    load_dotenv()
    asyncio.run(run_pipeline())
```

---

## Supabase Schema

```sql
-- database/schema.sql
-- Full 8-table schema for vc-radar
-- Run this in the Supabase SQL editor to set up all tables

-- Enable UUID extension
create extension if not exists "uuid-ossp";

-- VC Firms
create table vc_firms (
    id              serial primary key,
    name            text not null unique,
    slug            text not null unique,
    portfolio_url   text,
    hq_city         text,
    hq_country      text default 'USA',
    region          text,
    focus           text[],       -- e.g. ['ai', 'enterprise', 'consumer']
    stage_focus     text[],       -- e.g. ['seed', 'series_a']
    aum_usd         bigint,
    founded_year    int,
    website         text,
    created_at      timestamptz default now(),
    updated_at      timestamptz default now()
);

-- Portfolio Companies
create table companies (
    id                  serial primary key,
    vc_firm_id          int references vc_firms(id) on delete cascade,
    name                text not null,
    slug                text,
    sector              text,
    city                text,
    country             text default 'USA',
    region              text,
    founded_year        int,
    investment_stage    text,
    status              text default 'active',
    website             text,
    description         text,
    created_at          timestamptz default now(),
    updated_at          timestamptz default now(),
    unique(vc_firm_id, name)
);

-- Founders
create table founders (
    id                  serial primary key,
    company_id          int references companies(id) on delete cascade,
    name                text not null,
    is_primary          boolean default false,
    est_birth_year      int,
    domain_exp_years    int,
    prior_founder       boolean,
    education_tier      text,   -- 'elite' / 'strong' / 'standard' / 'self-taught'
    age_at_founding     int generated always as (
                            case when est_birth_year is not null and
                                 (select founded_year from companies where id = company_id) is not null
                            then (select founded_year from companies where id = company_id) - est_birth_year
                            else null end
                        ) stored,
    current_age_2026    int generated always as (
                            case when est_birth_year is not null
                            then 2026 - est_birth_year
                            else null end
                        ) stored,
    confidence          text,   -- 'high' / 'medium' / 'low'
    inference_method    text,
    source_notes        text,
    linkedin_url        text,
    created_at          timestamptz default now(),
    updated_at          timestamptz default now()
);

-- VC Fund Raises (Phase 3 — SEC EDGAR)
create table fund_raises (
    id              serial primary key,
    vc_firm_id      int references vc_firms(id) on delete set null,
    fund_name       text not null,
    amount_usd      bigint,
    filing_date     date,
    sec_form_d_url  text,
    status          text default 'active',
    created_at      timestamptz default now()
);

-- Sectors (lookup)
create table sectors (
    id          serial primary key,
    name        text not null unique,
    parent      text,
    color_hex   text
);

-- Pipeline Run Audit Log
create table pipeline_runs (
    id                  serial primary key,
    run_at              timestamptz default now(),
    vc_firms_processed  int,
    companies_upserted  int,
    companies_skipped   int,
    exa_calls           int,
    openrouter_tokens   bigint,
    claude_tokens       bigint,
    total_cost_usd      numeric(8,4),
    duration_seconds    int,
    status              text default 'success',
    error_log           text
);

-- Startup-VC Match Embeddings (Phase 3)
create table vc_embeddings (
    id          serial primary key,
    vc_firm_id  int references vc_firms(id) on delete cascade,
    embedding   vector(1536),  -- requires pgvector extension
    model       text,
    created_at  timestamptz default now()
);

-- Company-VC relationship (handles co-investment)
create table company_investors (
    id          serial primary key,
    company_id  int references companies(id) on delete cascade,
    vc_firm_id  int references vc_firms(id) on delete cascade,
    unique(company_id, vc_firm_id)
);

-- Indexes for dashboard performance
create index idx_companies_vc on companies(vc_firm_id);
create index idx_companies_sector on companies(sector);
create index idx_companies_founded on companies(founded_year);
create index idx_companies_country on companies(country);
create index idx_founders_company on founders(company_id);
create index idx_fund_raises_vc on fund_raises(vc_firm_id);
create index idx_fund_raises_date on fund_raises(filing_date);

-- Row Level Security (public read, service role write)
alter table vc_firms enable row level security;
alter table companies enable row level security;
alter table founders enable row level security;
alter table fund_raises enable row level security;

create policy "Public read access" on vc_firms for select using (true);
create policy "Public read access" on companies for select using (true);
create policy "Public read access" on founders for select using (true);
create policy "Public read access" on fund_raises for select using (true);
```

---

## Dashboard (Next.js 15)

### Tech Stack
- **Next.js 15.x** — App Router, Turbopack (default in v15), React Server Components
- **React 19.x** — concurrent features, improved hydration
- **TypeScript 5.8.x** — strict mode throughout
- **Tailwind CSS v4** — oxide engine (no config file needed, CSS-first config)
- **Recharts 2.x** — standard charts (histogram, donut, bar, scatter)
- **D3.js 7.x** — complex interactive viz (network graph, Sankey, streamgraph, bubble)
- **Mapbox GL JS 3.x** — geographic investment heatmap (WebGL2)
- **Framer Motion 12.x** — page transitions, chart animations
- **Supabase JS v2** — direct DB reads from browser (no separate API layer needed)
- **PostHog** — open-source analytics
- **Vercel** — deploy on push to main (free tier)

### Dashboard Views

Refer to `Meridian_Design_Bible.md` for full wireframes, color palette, and visualization specs.

**Core pages — all built today:**
1. `/` — Overview: live stats, founder age histogram, sector donut, investment heatmap, recent additions
2. `/explore/vcs` — VC directory with filter by stage/sector/region
3. `/explore/vcs/[slug]` — VC deep dive: portfolio list, founder age radar, timeline, fund raises
4. `/explore/companies` — Searchable/filterable company database with sorting
5. `/explore/founders` — Age scatter (age vs. company valuation), education breakdown, experience histogram
6. `/trends` — Sector stream chart, emerging sectors YoY, investment timeline animation
7. `/fundraises` — SEC Form D feed — VC funds raised (Phase 3, scaffolded today)
8. `/match` — Startup input form → ranked VC match list (Phase 3, scaffolded today)

### Supabase Client Pattern

```typescript
// dashboard/lib/supabase.ts — Supabase JS v2, typed with generated types

import { createBrowserClient } from '@supabase/ssr'
import type { Database } from './database.types'   // generated by supabase gen types

export function createClient() {
  return createBrowserClient<Database>(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
  )
}

// dashboard/lib/queries.ts — all DB queries in one place

export async function getVCFirms(filters?: {
  stage?: string
  sector?: string
  region?: string
}) {
  const supabase = createClient()
  let query = supabase
    .from('vc_firms')
    .select(`*, companies(count)`)
    .order('name')

  if (filters?.region) query = query.eq('region', filters.region)
  return query
}

export async function getFounderAgeStats() {
  const supabase = createClient()
  return supabase
    .from('founders')
    .select('age_at_founding, current_age_2026, confidence, education_tier')
    .not('age_at_founding', 'is', null)
}
```

---

## Phase 3: SEC Fundraise Tracker

```python
# sec/sec_parser.py — SEC EDGAR Form D, completely free, no API key
# Uses Deepseek V3 via OpenRouter for structured parsing

from __future__ import annotations
import asyncio
import httpx
from openai import AsyncOpenAI
from tenacity import retry, stop_after_attempt, wait_exponential
import structlog

log = structlog.get_logger()

SEC_FULL_TEXT_URL = "https://efts.sec.gov/LATEST/search-index"

async def fetch_vc_form_d_filings(since_date: str) -> list[dict]:
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.get(SEC_FULL_TEXT_URL, params={
            "q": '"venture capital" OR "venture fund" OR "early stage"',
            "forms": "D",
            "dateRange": "custom",
            "startdt": since_date,
        })
        r.raise_for_status()
        return r.json().get("hits", {}).get("hits", [])

@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=10))
async def parse_filing_with_llm(filing_xml: str) -> dict:
    response = await router_client.chat.completions.create(
        model="deepseek/deepseek-chat",
        messages=[{"role": "user", "content": (
            f"Extract these fields from this SEC Form D XML filing. "
            f"Return JSON: fund_name, vc_firm, amount_raised_usd, filing_date, "
            f"fund_type, total_offering_amount.\n\n{filing_xml[:6000]}"
        )}],
        response_format={"type": "json_object"},
        temperature=0.0,
    )
    return json.loads(response.choices[0].message.content)
```

---

## Phase 3: Startup–VC Matching Engine

```python
# matching/matcher.py — embedding-based cosine similarity scoring

from __future__ import annotations
import numpy as np
from openai import AsyncOpenAI
import structlog

log = structlog.get_logger()

router_client = AsyncOpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.environ["OPENROUTER_API_KEY"],
)


async def get_embedding(text: str) -> list[float]:
    response = await router_client.embeddings.create(
        model="openai/text-embedding-3-small",   # via OpenRouter, no extra key
        input=text,
    )
    return response.data[0].embedding


def cosine_similarity(a: list[float], b: list[float]) -> float:
    a, b = np.array(a), np.array(b)
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))


async def compute_vc_match_score(
    startup_profile: dict,
    vc: dict,
    portfolio_embeddings: list[list[float]],
) -> float:
    startup_emb = await get_embedding(startup_profile["description"])
    sector_score = max(cosine_similarity(startup_emb, e) for e in portfolio_embeddings)
    stage_score = 1.0 if startup_profile.get("stage") in (vc.get("stage_focus") or []) else 0.3
    geo_score = 1.0 if startup_profile.get("country") == vc.get("hq_country") else 0.7
    return round(0.4 * sector_score + 0.3 * stage_score + 0.3 * geo_score, 4)


async def generate_match_explanation(startup: dict, vc: dict) -> str:
    response = await router_client.chat.completions.create(
        model="deepseek/deepseek-chat",
        messages=[{"role": "user", "content": (
            f"In exactly 2 sentences, explain why {vc['name']} is a strong fit for this startup: "
            f"{startup['description']}. "
            f"Reference these recent {vc['name']} investments: {vc.get('recent_investments', [])}."
        )}],
        temperature=0.4,
    )
    return response.choices[0].message.content
```

---

## GitHub Actions — CI/CD & Automation

```yaml
# .github/workflows/data-pipeline.yml
name: Weekly Data Pipeline
on:
  schedule:
    - cron: '0 9 * * 1'       # Every Monday 9am UTC
  workflow_dispatch:             # Manual trigger from GitHub Actions UI

jobs:
  run-pipeline:
    runs-on: ubuntu-24.04
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python 3.13
        uses: actions/setup-python@v5
        with:
          python-version: '3.13'
          cache: 'pip'

      - name: Install Playwright browsers
        run: |
          pip install -r pipeline/requirements.txt
          playwright install chromium --with-deps

      - name: Run pipeline
        env:
          EXA_API_KEY: ${{ secrets.EXA_API_KEY }}
          OPENROUTER_API_KEY: ${{ secrets.OPENROUTER_API_KEY }}
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
          SUPABASE_URL: ${{ secrets.SUPABASE_URL }}
          SUPABASE_KEY: ${{ secrets.SUPABASE_KEY }}
        run: python pipeline/scheduler.py

      - name: Export to Excel + JSON
        run: |
          python exporters/excel_exporter.py
          python exporters/json_exporter.py

      - name: Commit updated exports
        run: |
          git config user.name "vc-radar-bot"
          git config user.email "bot@vc-radar.dev"
          git add exports/
          git commit -m "data: weekly update $(date +%Y-%m-%d)" || echo "No changes"
          git push
```

```yaml
# .github/workflows/ci.yml
name: CI — Lint, Type Check, Test
on:
  pull_request:
    branches: [main]
  push:
    branches: [main]

jobs:
  python-checks:
    runs-on: ubuntu-24.04
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.13'
          cache: 'pip'
      - run: pip install -r pipeline/requirements.txt ruff mypy
      - run: ruff check pipeline/
      - run: mypy pipeline/ --strict

  dashboard-checks:
    runs-on: ubuntu-24.04
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '22'
          cache: 'npm'
          cache-dependency-path: dashboard/package-lock.json
      - run: cd dashboard && npm ci
      - run: cd dashboard && npm run build
      - run: cd dashboard && npx tsc --noEmit
```

---

## Community VC List (config/vc_list.yaml)

```yaml
# config/vc_list.yaml
# Add VCs via PR — pipeline automatically picks them up on next Monday run
# Required fields: name, portfolio_url
# Optional: focus, stage, region, hq_country

vcs:
  - name: "NEA"
    portfolio_url: "https://www.nea.com/portfolio"
    focus: ["ai", "enterprise", "consumer", "health"]
    stage: ["seed", "series_a", "series_b", "series_c", "growth"]
    region: "US-Multiple"
    hq_country: "USA"

  - name: "NFX"
    portfolio_url: "https://www.nfx.com/companies"
    focus: ["ai", "marketplace", "network-effects", "fintech"]
    stage: ["pre-seed", "seed", "series_a"]
    region: "US-SF Bay"
    hq_country: "USA"

  - name: "Race Capital"
    portfolio_url: "https://race.capital/portfolio"
    focus: ["ai", "developer-tools", "infrastructure"]
    stage: ["pre-seed", "seed", "series_a"]
    region: "US-SF Bay"
    hq_country: "USA"

  # ... remaining 17 VCs from current dataset + new ones to be added
```

---

## APIs & Cost Breakdown

| Service | Use Case | Cost | Priority |
|---------|----------|------|----------|
| **Exa API** | URL crawling + founder search (replaces Firecrawl + Serper) | ~$10/month | ✅ Essential |
| **OpenRouter** (Deepseek V3) | Portfolio extraction, structured data, embeddings | ~$3/month | ✅ Essential |
| **Claude API** (Anthropic) | Complex founder age triangulation only | ~$5/month | ✅ Essential |
| **Supabase** | PostgreSQL database + auth + storage | Free tier | ✅ Essential |
| **Vercel** | Dashboard hosting + preview deploys | Free tier | ✅ Essential |
| **Playwright** | Fallback scraping for difficult sites | Free | ✅ Essential |
| **SEC EDGAR** | VC fund raise data | Free (public) | Phase 3 |
| **PostHog** | Dashboard usage analytics | Free tier | ✅ Essential |
| **Mapbox GL** | Geographic investment heatmap | Free (50K loads/month) | Phase 2 |

**Total monthly cost: ~$18–22/month**

---

## Open-Source Strategy

**Why MIT:**
- Maximum community adoption — no restrictions on use
- Community contributes data corrections and new VCs via PRs to `vc_list.yaml`
- Credibility — people trust open data
- Network effects — contributors become users become advocates

---

## Today's Build Sprint — Parallel Tracks in Claude Code

Everything ships today. Claude Code runs all tracks simultaneously. Dependencies are noted — blocked tracks wait only for their specific unblock, not for all other tracks to finish.

```
TRACK A — Repo Scaffolding (no dependencies)
  ├── Create full folder structure
  ├── .env.example with all required keys
  ├── .python-version (3.13.x)
  ├── .nvmrc (22 LTS)
  ├── LICENSE (MIT)
  ├── README.md (full docs)
  ├── pipeline/pyproject.toml + requirements.txt (pinned)
  ├── dashboard/package.json (Next.js 15, React 19, all deps)
  └── .github/workflows/ (ci.yml, data-pipeline.yml, deploy.yml)

TRACK B — Database (no dependencies)
  ├── database/schema.sql (all 8 tables, indexes, RLS)
  ├── database/migrations/001_initial.sql
  └── database/seed.py (import all 142 rows from Excel → Supabase)

TRACK C — Pipeline Modules (no dependencies between modules, run in parallel)
  ├── pipeline/models.py          ← Pydantic V2 shared models
  ├── pipeline/scraper.py         ← Exa + Playwright fallback
  ├── pipeline/extractor.py       ← OpenRouter Deepseek V3
  ├── pipeline/enricher.py        ← Exa semantic founder search
  ├── pipeline/triangulator.py    ← Claude Sonnet age triangulation
  ├── pipeline/validator.py       ← Pydantic V2 schema validation + dedup
  └── pipeline/scheduler.py       ← Async orchestrator (depends on all above)

TRACK D — Config & Prompts (no dependencies)
  ├── config/vc_list.yaml (all 20 current VCs pre-populated)
  └── config/prompts.yaml (all LLM prompts versioned, extracted from code)

TRACK E — Exporters (no dependencies)
  ├── exporters/excel_exporter.py
  └── exporters/json_exporter.py

TRACK F — Dashboard (parallel to all pipeline tracks)
  ├── Next.js 15 project initialisation
  ├── Tailwind v4 + Framer Motion + Recharts + D3 setup
  ├── dashboard/lib/supabase.ts + queries.ts
  ├── All 8 page routes (scaffolded and functional same day)
  ├── All chart components (AgeHistogram, SectorDonut, NetworkGraph, SankeyFlow,
  │   BubbleUniverse, VCDnaRadar, GeoHeatmap, SectorStream)
  ├── All table components (CompanyTable, VCTable, FounderTable)
  ├── All UI components (FilterBar, SearchInput, StatCard, VCCard)
  └── Vercel deploy (push to main triggers auto-deploy)

TRACK G — Phase 3 Modules (scaffold today, activate after core is stable)
  ├── sec/sec_parser.py + fund_tracker.py
  └── matching/embedder.py + matcher.py + explainer.py

TRACK H — Community & Documentation (parallel to everything)
  ├── README.md (full: setup, usage, contributing, architecture diagram)
  ├── .github/CONTRIBUTING.md (how to add a VC, PR checklist)
  └── .env.example (all keys documented with where to get them)
```

**Dependency map — what waits for what:**

```
seed.py              → needs schema.sql applied to Supabase first
scheduler.py         → needs models.py, scraper.py, extractor.py, enricher.py,
                        triangulator.py, validator.py all complete
dashboard pages      → need supabase.ts + queries.ts (lib layer first)
chart components     → need queries.ts to know data shape
Vercel deploy        → needs dashboard to build (npm run build) clean
Phase 3 activation   → needs pipeline + DB working end-to-end first
```

**Execution order within Claude Code (parallel where possible):**

```
STEP 1 (parallel):   Track A + Track B + Track D + Track H
STEP 2 (parallel):   Track C (all pipeline modules at once) + Track E + Track F lib layer
STEP 3:              scheduler.py (after all pipeline modules done)
STEP 4 (parallel):   Dashboard pages + chart components + Track G scaffolding
STEP 5:              End-to-end test: run scheduler.py against 3 VCs
STEP 6:              seed.py + Vercel deploy + GitHub Actions verify
STEP 7:              Phase 3 activation (SEC + matching scaffolds wired up)
```

---

## Pre-Flight Checklist (Before Opening Claude Code)

Get these done first — pipeline can't run without them:

- [ ] **Exa API key** → [exa.ai](https://exa.ai) (1K free requests/month)
- [ ] **OpenRouter API key** → [openrouter.ai](https://openrouter.ai) (add $10 credit to start)
- [ ] **Anthropic API key** → [console.anthropic.com](https://console.anthropic.com) (add $10 credit)
- [ ] **Supabase project created** → [supabase.com](https://supabase.com) — get URL + anon key + service key
- [ ] **Vercel project created** → [vercel.com](https://vercel.com) — link to `github.com/Zonivan-AI/vc-radar`
- [ ] **Mapbox token** → [mapbox.com](https://mapbox.com) (free, 50K loads/month)
- [ ] **Add GitHub repo secrets**: `EXA_API_KEY`, `OPENROUTER_API_KEY`, `ANTHROPIC_API_KEY`, `SUPABASE_URL`, `SUPABASE_KEY`, `VERCEL_TOKEN`
- [ ] **pgvector extension** → Enable in Supabase dashboard (Dashboard → Extensions → pgvector) — needed for Phase 3 matching

---

## What Claude Code Delivers by End of Today

```
✅ Full repo at github.com/Zonivan-AI/vc-radar (MIT, public)
✅ Agentic pipeline live and tested against all 20 current VCs
✅ 142 seed rows imported into Supabase
✅ Weekly GitHub Actions cron wired up
✅ Next.js 15 dashboard deployed on Vercel
✅ All 8 pages live and querying real Supabase data
✅ All interactive visualizations working (D3 + Recharts)
✅ SEC parser scaffolded and ready for activation
✅ Startup–VC matching engine scaffolded and ready for activation
✅ Lint, type-check, and CI pipeline passing on every push
✅ README + CONTRIBUTING docs complete for open-source launch
```

---

*vc-radar — MIT License — March 2026*
*github.com/Zonivan-AI/vc-radar*