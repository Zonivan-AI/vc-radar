# Meridian — Design Bible & Platform Specification
### "Navigate the AI investment landscape"

> Open-source intelligence platform tracking VC investments, founder profiles, and fund activity across North America's AI ecosystem.

---

## Table of Contents

1. [Brand Identity](#1-brand-identity)
2. [Product Vision & Personas](#2-product-vision--personas)
3. [Information Architecture](#3-information-architecture)
4. [User Flows](#4-user-flows)
5. [Wireframes](#5-wireframes)
6. [Visualization Strategy](#6-visualization-strategy)
7. [Data Model & ERD](#7-data-model--erd)
8. [Feature Prioritization](#8-feature-prioritization)
9. [Technical Architecture](#9-technical-architecture)
10. [Things You Haven't Covered Yet](#10-things-you-havent-covered-yet)

---

## 1. Brand Identity

### Name: **Meridian**

A meridian is a reference line used for navigation — exactly what this platform is for founders and investors trying to navigate the VC landscape. It evokes precision, clarity, and direction.

- **Tagline**: *Navigate the AI investment landscape*
- **Sub-tagline**: *Open-source VC intelligence for founders, researchers, and operators*
- **Domain suggestions**: `meridian.fyi` · `getmeridian.io` · `meridianvc.io`
- **GitHub**: [github.com/Zonivan-AI/vc-radar](https://github.com/Zonivan-AI/vc-radar)

---

### Color Palette

```
PRIMARY PALETTE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  Background      #0A0F1E   ████  Deep space navy
  Surface         #111827   ████  Card background
  Surface Raised  #1A2235   ████  Elevated cards, modals
  Border          #1F2937   ████  Subtle dividers

ACCENT COLORS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  Indigo          #6366F1   ████  Primary CTA, links, focus
  Indigo Light    #818CF8   ████  Hover states
  Emerald         #10B981   ████  Growth, active, positive
  Amber           #F59E0B   ████  Warnings, highlights, badges
  Rose            #F43F5E   ████  Shutdown, negative, danger

TEXT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  Primary         #F9FAFB   ████  Headings, key data
  Secondary       #9CA3AF   ████  Labels, metadata
  Muted           #4B5563   ████  Placeholder, disabled

CHART PALETTE (8 distinct colors for sector coding)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  AI Infra        #6366F1   ████  Indigo
  AI Apps         #10B981   ████  Emerald
  Security        #F59E0B   ████  Amber
  Healthcare      #EC4899   ████  Pink
  Fintech         #3B82F6   ████  Blue
  Robotics        #8B5CF6   ████  Violet
  Dev Tools       #14B8A6   ████  Teal
  Consumer        #F97316   ████  Orange
```

### Typography
- **Headings**: `Inter` (variable, 600–800 weight) — clean, modern, used by Vercel/Linear
- **Body**: `Inter` (400–500) — consistent system
- **Data/Numbers**: `JetBrains Mono` — monospace for all numbers, amounts, dates in tables
- **Code**: `JetBrains Mono`

### Design Language

Inspired by: **Linear** (product) + **Vercel** (developer feel) + **Bloomberg Terminal** (data density)

Core principles:
- **Dark by default** — data pops on dark backgrounds; chart colors sing
- **Dense but breathable** — pack information without clutter
- **Every pixel earns its place** — no decorative elements, all UI serves data
- **Micro-interactions** — hover states on every chart element, smooth transitions
- **Glassmorphism cards** — subtle frosted glass effect on stat cards

### Logo Concept

```
  ◈ MERIDIAN

  Mark: A compass rose simplified to a diamond/crosshair shape
  ◈ = A rotated square with a center dot
      Represents: navigation, precision, intersection of data

  Usage:
  ◈ Meridian         (full lockup)
  ◈                  (icon only, favicon)
  MERIDIAN           (wordmark only, some contexts)
```

---

## 2. Product Vision & Personas

### What Meridian Is

An open-source intelligence layer on top of the AI VC ecosystem. Raw data (who invested in what, when, at what stage, and who founded it) transformed into actionable insight through interactive visualizations and analytics.

**Not** a replacement for Crunchbase or PitchBook. Those are expensive, opaque, and built for enterprise deal teams. Meridian is free, open, founder-first, and focused specifically on the AI investment landscape with a unique angle: **founder profile analytics** (age, experience, education patterns) layered on top of investment data.

### User Personas

**Persona 1 — The Founder (Primary)**
> *"I'm raising a $2M seed round for my AI infrastructure startup. Which VCs should I approach first?"*
- Wants: Find best-fit VCs fast, understand what they actually invest in recently, see founder profile matches
- Frustration: Crunchbase paywalls, PitchBook is $30K/yr, cold outreach into the void

**Persona 2 — The Researcher / Analyst**
> *"I'm writing a report on founder age trends in AI. Where is the data?"*
- Wants: Clean exportable data, trend analysis, charts ready to screenshot/embed
- Frustration: No single source of truth, data scattered across press releases

**Persona 3 — The LP / Fund Evaluator**
> *"I'm evaluating three VC firms to commit capital to. What's their recent activity?"*
- Wants: Portfolio breakdown, investment velocity, sector focus drift over time
- Frustration: VC firms curate their own narratives; no neutral third-party view

**Persona 4 — The Operator / BD Person**
> *"I want to know which VC-backed AI companies are in the health space and recently raised."*
- Wants: Filtered company lists, contact context, investment stage
- Frustration: Google searches return stale info

**Persona 5 — The Open-Source Contributor**
> *"I know Sequoia backed a company that's not on here."*
- Wants: Easy way to submit data, see contributions recognized
- Frustration: No open, community-maintained VC database exists

---

## 3. Information Architecture

### Sitemap

```
◈ MERIDIAN
│
├── / (Overview / Home Dashboard)
│   └── Live stats, featured charts, recent activity feed
│
├── /explore
│   ├── /explore/vcs              (VC Directory)
│   │   └── /explore/vcs/[slug]   (VC Deep Dive)
│   ├── /explore/companies         (Company Database)
│   │   └── /explore/companies/[slug]  (Company Profile)
│   └── /explore/founders          (Founder Analytics)
│
├── /trends                        (Investment Trends)
│   ├── /trends/sectors
│   ├── /trends/stages
│   ├── /trends/geography
│   └── /trends/founders
│
├── /fundraises                    (VC Fund Raises — Phase 2)
│   └── Live feed of new VC fund announcements + SEC filings
│
├── /match                         (Startup–VC Matching — Phase 3)
│
├── /data                          (Data & API)
│   ├── /data/download             (CSV/Excel download)
│   ├── /data/api                  (API docs)
│   └── /data/contribute           (How to contribute)
│
└── /about
```

### Navigation Structure

```
TOP NAV (sticky)
┌────────────────────────────────────────────────────────────────┐
│ ◈ Meridian    Explore ▾    Trends    Fundraises    Match       │
│                                              [Download] [GitHub]│
└────────────────────────────────────────────────────────────────┘

EXPLORE DROPDOWN
┌───────────────────────────────┐
│ 🏛  VC Firms                  │
│ 🏢  Portfolio Companies       │
│ 👤  Founder Analytics         │
└───────────────────────────────┘
```

---

## 4. User Flows

### Flow 1: Founder Finding Best-Fit VCs

```
Landing Page
    │
    ├── [See "Match" CTA prominently]
    │
    ▼
/match — Startup Profile Form
    │
    ├── Input: Sector (dropdown + freetext)
    ├── Input: Stage (pre-seed/seed/A)
    ├── Input: Location (city/country)
    ├── Input: What you're building (2 sentences)
    └── [Find My VCs →]
    │
    ▼
Match Results Page
    │
    ├── Top 10 VCs ranked by match score
    ├── Each card shows: recent similar investments, founder profile fit
    ├── [View VC Profile] → /explore/vcs/[slug]
    └── [Export List as CSV]
```

### Flow 2: Researcher Analyzing Founder Age Trends

```
Landing Page → [Explore Trends]
    │
    ▼
/trends/founders
    │
    ├── Age at founding distribution histogram
    ├── Filter by: VC firm / Sector / Stage / Year / Region
    ├── Hover any bar → tooltip with company names
    ├── [Click bar] → filter company table below
    └── [Export filtered data]
```

### Flow 3: Exploring a Specific VC

```
/explore/vcs (VC Directory)
    │
    ├── Search bar + filters (stage, sector, region, AUM)
    ├── Grid of VC cards
    └── [Click VC card]
    │
    ▼
/explore/vcs/nea-capital
    │
    ├── Header: name, AUM, stage focus, HQ, link to website
    ├── Stats row: # portfolio companies, avg founder age, # unicorns
    ├── Tabs:
    │   ├── [Portfolio] — filterable company grid
    │   ├── [Founder Analytics] — age/exp charts for this VC
    │   ├── [Investment Timeline] — companies added over time
    │   └── [Fund Raises] — their own fund raise history
    └── Each company card → /explore/companies/[slug]
```

### Flow 4: Data Contributor

```
GitHub → README → CONTRIBUTING.md
    │
    ├── Edit vc_list.yaml to add new VC
    ├── Submit PR
    ├── GitHub Action validates schema
    ├── Maintainer reviews + merges
    └── Pipeline auto-runs, dashboard updates within 24h
```

---

## 5. Wireframes

### 5.1 Home / Overview Page

```
┌──────────────────────────────────────────────────────────────────────┐
│ ◈ Meridian        Explore ▾    Trends    Fundraises    Match         │
│                                                    [Download] [GitHub]│
├──────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  ┌─── HERO ──────────────────────────────────────────────────────┐   │
│  │                                                               │   │
│  │  Navigate the AI                                             │   │
│  │  Investment Landscape                                        │   │
│  │                                                               │   │
│  │  Open-source intelligence on 438+ VC-backed AI companies,   │   │
│  │  20 top VC firms, and the founders they back.                │   │
│  │                                                               │   │
│  │  [Explore VCs →]    [Find Your VC Match →]                   │   │
│  │                                                               │   │
│  └───────────────────────────────────────────────────────────────┘   │
│                                                                       │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐            │
│  │   20     │  │  438+    │  │   $47B   │  │  312     │            │
│  │ VC Firms │  │Companies │  │  Raised  │  │ Founders │            │
│  │          │  │ Tracked  │  │  Total   │  │ Profiled │            │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘            │
│                                                                       │
│  ┌─── FEATURED CHART: Founder Age at Founding ───────────────────┐  │
│  │                                                               │  │
│  │   # companies                                                 │  │
│  │   60│    ██                                                  │  │
│  │   50│    ██ ██                                               │  │
│  │   40│ ██ ██ ██ ██                                            │  │
│  │   30│ ██ ██ ██ ██ ██                                         │  │
│  │   20│ ██ ██ ██ ██ ██ ██                                      │  │
│  │   10│ ██ ██ ██ ██ ██ ██ ██ ██                               │  │
│  │    0└──────────────────────────────────                      │  │
│  │      18  22  26  30  34  38  42  46+                         │  │
│  │                        Age at Founding                       │  │
│  │                                                               │  │
│  │  Median: 29  │  Mean: 31.4  │  Range: 19–52                 │  │
│  └───────────────────────────────────────────────────────────────┘  │
│                                                                       │
│  ┌─── SECTOR BREAKDOWN ──────────┐  ┌─── RECENT ACTIVITY ────────┐  │
│  │                               │  │                            │  │
│  │   [Donut Chart]               │  │  ● Poolside raised $500M   │  │
│  │                               │  │    Bain Capital · 3d ago   │  │
│  │   AI Infra   ████ 34%         │  │                            │  │
│  │   AI Apps    ███  24%         │  │  ● TwinMind seed round     │  │
│  │   Security   ██   15%         │  │    Streamlined · 1w ago    │  │
│  │   Dev Tools  ██   12%         │  │                            │  │
│  │   Robotics   █     9%         │  │  ● Qdrant Series B close   │  │
│  │   Other      █     6%         │  │    Unusual · 2w ago        │  │
│  │                               │  │                            │  │
│  └───────────────────────────────┘  └────────────────────────────┘  │
│                                                                       │
│  ┌─── VC INVESTMENT HEATMAP ─────────────────────────────────────┐  │
│  │                                                               │  │
│  │  Each cell = # investments. Darker = more.                   │  │
│  │                                                               │  │
│  │            AI   Sec  Fin  Rob  Dev  Hlth Health              │  │
│  │  NEA       ███  ██   █    ██   ███  ██                       │  │
│  │  Khosla    ████ ███  ██   ███  ██   █                        │  │
│  │  Quiet     ███  █    ██   █    ██   ██                       │  │
│  │  Matrix    ████ ██   █    █    ███  █                        │  │
│  │  Bain      ██   ███  ██   █    ██   ████                     │  │
│  │  ...                                                          │  │
│  │                                                               │  │
│  └───────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────────┘
```

---

### 5.2 VC Directory Page

```
┌──────────────────────────────────────────────────────────────────────┐
│ ◈ Meridian        Explore ▾    Trends    Fundraises    Match         │
├──────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  VC Firms                                          [+ Submit a VC]  │
│  ─────────────────────────────────────────────────────────────────   │
│                                                                       │
│  ┌─ FILTERS ─────────────────────────────────────────────────────┐   │
│  │ Search: [_______________]  Stage: [All ▾]  Sector: [All ▾]    │   │
│  │ Region: [All ▾]           AUM: [All ▾]    Sort: [Most Active] │   │
│  └────────────────────────────────────────────────────────────────┘  │
│                                                                       │
│  20 firms · 438 companies tracked                                     │
│                                                                       │
│  ┌─────────────────────┐  ┌─────────────────────┐                   │
│  │ NEA Capital         │  │ Khosla Ventures      │                   │
│  │ ─────────────────── │  │ ──────────────────── │                   │
│  │ Seed → Series C     │  │ Seed → Series B      │                   │
│  │ SF Bay · $4B AUM    │  │ Palo Alto · $15B AUM │                   │
│  │                     │  │                      │                   │
│  │ 32 companies tracked│  │ 10 companies tracked │                   │
│  │ Avg founder age: 31 │  │ Avg founder age: 34  │                   │
│  │                     │  │                      │                   │
│  │ Top sectors:        │  │ Top sectors:         │                   │
│  │ ██ AI Infra  ██ SaaS│  │ ██ AI    ██ Robotics │                   │
│  │                     │  │                      │                   │
│  │ [View Portfolio →]  │  │ [View Portfolio →]   │                   │
│  └─────────────────────┘  └─────────────────────┘                   │
│                                                                       │
│  ┌─────────────────────┐  ┌─────────────────────┐                   │
│  │ Quiet Capital       │  │ NFX                  │                   │
│  │ ...                 │  │ ...                  │                   │
│  └─────────────────────┘  └─────────────────────┘                   │
│                                                                       │
└──────────────────────────────────────────────────────────────────────┘
```

---

### 5.3 VC Deep Dive Page

```
┌──────────────────────────────────────────────────────────────────────┐
│ ◈ Meridian   > Explore > VCs > NEA Capital                          │
├──────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  ┌─── VC HEADER ─────────────────────────────────────────────────┐   │
│  │                                                               │   │
│  │  ◻ NEA Capital                          [↗ nea.com]          │   │
│  │    New Enterprise Associates                                  │   │
│  │                                                               │   │
│  │  Founded 1978 · Menlo Park, CA · $25B+ AUM                   │   │
│  │  Stage focus: Seed · Series A · Series B · Series C           │   │
│  │  Sectors: AI · Enterprise · Consumer · Healthcare            │   │
│  │                                                               │   │
│  │  ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐    │   │
│  │  │   32   │ │  28.5  │ │   4    │ │  $8.2B │ │   68%  │    │   │
│  │  │tracked │ │avg age │ │unicorns│ │ raised │ │AI-focus│    │   │
│  │  └────────┘ └────────┘ └────────┘ └────────┘ └────────┘    │   │
│  │                                                               │   │
│  └───────────────────────────────────────────────────────────────┘   │
│                                                                       │
│  [Portfolio]  [Founder Analytics]  [Timeline]  [Fund Raises]         │
│  ──────────                                                           │
│                                                                       │
│  ┌─── PORTFOLIO TAB ─────────────────────────────────────────────┐   │
│  │                                                               │   │
│  │  Filter: [Sector ▾] [Stage ▾] [Status ▾] [Founded Year ▾]    │   │
│  │  Sort: [Funding ↓]            [▦ Grid]  [☰ Table]            │   │
│  │                                                               │   │
│  │  ┌───────────────────┐  ┌───────────────────┐               │   │
│  │  │ Samaya AI         │  │ Runway             │               │   │
│  │  │ AI Finance        │  │ AI Video           │               │   │
│  │  │ Series A · 2022   │  │ Series D · 2018    │               │   │
│  │  │ New York · Active │  │ SF · Active        │               │   │
│  │  │ $43.5M raised     │  │ $237M raised       │               │   │
│  │  │                   │  │                    │               │   │
│  │  │ Founder: Maithra  │  │ Founder: Siqi Chen │               │   │
│  │  │ Age at founding:28│  │ Age at founding:31 │               │   │
│  │  └───────────────────┘  └────────────────────┘               │   │
│  │                                                               │   │
│  └───────────────────────────────────────────────────────────────┘   │
│                                                                       │
└──────────────────────────────────────────────────────────────────────┘
```

---

### 5.4 Founder Analytics Page

```
┌──────────────────────────────────────────────────────────────────────┐
│ ◈ Meridian   > Explore > Founder Analytics                           │
├──────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  Founder Analytics                                                    │
│  How old, how experienced, how educated are the founders VCs back?   │
│                                                                       │
│  ┌─ GLOBAL FILTERS ───────────────────────────────────────────────┐  │
│  │ VC: [All ▾]  Sector: [All ▾]  Stage: [All ▾]  Year: [All ▾]  │  │
│  └────────────────────────────────────────────────────────────────┘  │
│                                                                       │
│  ┌─── AGE AT FOUNDING HISTOGRAM ─────────────────────────────────┐  │
│  │                                                               │  │
│  │  INTERACTIVE: hover = tooltip with companies, click = filter  │  │
│  │                                                               │  │
│  │  80│                  ████                                    │  │
│  │  60│             ████ ████ ████                               │  │
│  │  40│        ████ ████ ████ ████ ████                          │  │
│  │  20│   ████ ████ ████ ████ ████ ████ ████ ████               │  │
│  │   0└────────────────────────────────────────                  │  │
│  │     <22  24   26   28   30   32   34   36  38+                │  │
│  │                                                               │  │
│  │  ◆ Median: 29  ◆ Mean: 31.4  ◆ Youngest: 19  ◆ Oldest: 52  │  │
│  └───────────────────────────────────────────────────────────────┘  │
│                                                                       │
│  ┌─── EXPERIENCE vs FUNDING RAISED ──────────────────────────────┐  │
│  │                                                               │  │
│  │  SCATTER PLOT: x=domain exp (years), y=total raised ($M)      │  │
│  │  Bubble size = current valuation                              │  │
│  │  Color = sector                                               │  │
│  │  Hover = company name + founder details                       │  │
│  │                                                               │  │
│  │  $1B│                         ○ OpenAI                        │  │
│  │$500M│               ○ Runway                                  │  │
│  │$100M│  ○○ ○  ○○ ○ ○ ○○○ ○○ ○ ○                              │  │
│  │ $50M│ ○ ○ ○○○○○○○○○○ ○ ○ ○ ○○ ○                             │  │
│  │ $10M│○○ ○○ ○○○ ○○ ○○ ○ ○○ ○ ○ ○○                           │  │
│  │     └──────────────────────────────────                       │  │
│  │      0   2   5   10  15  20  25  30+                          │  │
│  │                    Domain Experience (years)                   │  │
│  └───────────────────────────────────────────────────────────────┘  │
│                                                                       │
│  ┌── EDUCATION TIER ────────┐  ┌── PRIOR FOUNDER RATE ───────────┐  │
│  │                          │  │                                 │  │
│  │ Top-10 Univ  ████ 47%    │  │  First-time  ████████████  71% │  │
│  │ Top-50 Univ  ███  28%    │  │  Prior found ████         29%  │  │
│  │ Other        ██   18%    │  │                                 │  │
│  │ No degree    █     7%    │  │  By VC: [Breakdown chart]       │  │
│  │                          │  │                                 │  │
│  └──────────────────────────┘  └─────────────────────────────────┘  │
│                                                                       │
└──────────────────────────────────────────────────────────────────────┘
```

---

### 5.5 Investment Trends Page

```
┌──────────────────────────────────────────────────────────────────────┐
│ ◈ Meridian   > Trends                                                │
├──────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  Investment Trends                                                    │
│                                                                       │
│  [Sectors]  [Stages]  [Geography]  [Founder Age Over Time]           │
│  ─────────                                                           │
│                                                                       │
│  ┌─── SECTOR INVESTMENT OVER TIME (Stream / Area Chart) ─────────┐  │
│  │                                                               │  │
│  │  INTERACTIVE: hover to see $ amount per sector per year       │  │
│  │  Toggle sectors on/off via legend                             │  │
│  │                                                               │  │
│  │  ████░░░░░░░░░░░░░░░░░░░░░░░░░░░   AI Infra                  │  │
│  │  ░░░░████░░░░░░░░░░░░░░░░░░░░░░░   AI Apps                   │  │
│  │  ░░░░░░░░████░░░░░░░░░░░░░░░░░░░   Security                  │  │
│  │  ░░░░░░░░░░░░████░░░░░░░░░░░░░░░   Dev Tools                 │  │
│  │  ░░░░░░░░░░░░░░░░████░░░░░░░░░░░   Robotics                  │  │
│  │  ░░░░░░░░░░░░░░░░░░░░████░░░░░░░   Healthcare                │  │
│  │      2019  2020  2021  2022  2023  2024  2025                 │  │
│  │                                                               │  │
│  └───────────────────────────────────────────────────────────────┘  │
│                                                                       │
│  ┌─── EMERGING vs DECLINING SECTORS ─────────────────────────────┐  │
│  │                                                               │  │
│  │  Ranked by YoY investment growth rate                        │  │
│  │                                                               │  │
│  │  ↑ AI Agents         +340% YoY  ████████████████████         │  │
│  │  ↑ AI Security       +180% YoY  ████████████                 │  │
│  │  ↑ AI Infrastructure +120% YoY  ████████                     │  │
│  │  → AI Apps            +45% YoY  ████                         │  │
│  │  ↓ Crypto/Web3        -23% YoY  ██                           │  │
│  │                                                               │  │
│  └───────────────────────────────────────────────────────────────┘  │
│                                                                       │
└──────────────────────────────────────────────────────────────────────┘
```

---

### 5.6 Company Profile Page

```
┌──────────────────────────────────────────────────────────────────────┐
│ ◈ Meridian   > Explore > Companies > Poolside                        │
├──────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  ┌─── COMPANY HEADER ────────────────────────────────────────────┐   │
│  │                                                               │   │
│  │  Poolside                              [↗ poolside.ai]       │   │
│  │  AI Coding / Foundation Model for Software Engineering       │   │
│  │                                                               │   │
│  │  San Francisco · USA · Founded 2023 · Series B               │   │
│  │  Status: ● Active    Total Raised: $500M                     │   │
│  │  Investor: Bain Capital Ventures                             │   │
│  │                                                               │   │
│  └───────────────────────────────────────────────────────────────┘   │
│                                                                       │
│  ┌─── FOUNDER PROFILE ───────────────────────────────────────────┐   │
│  │                                                               │   │
│  │  Primary: Jason Warner                                        │   │
│  │  Co-Founder: Eiso Kant                                        │   │
│  │                                                               │   │
│  │  Est. Birth Year: ~1980      Age at Founding: ~43            │   │
│  │  Domain Experience: 20+ yrs  Prior Founder: No               │   │
│  │  Education: Penn State                                        │   │
│  │                                                               │   │
│  │  Background: ex-GitHub CTO (oversaw GitHub Copilot launch);  │   │
│  │  ex-Redpoint Ventures Managing Director; 20+ years in        │   │
│  │  software industry.                                           │   │
│  │                                                               │   │
│  │  Age Confidence: Low  [?]  Method: Pattern inference         │   │
│  │                                                               │   │
│  └───────────────────────────────────────────────────────────────┘   │
│                                                                       │
│  ┌─── SIMILAR COMPANIES ─────────────────────────────────────────┐   │
│  │  (Same sector, similar stage, similar founder profile)        │   │
│  │                                                               │   │
│  │  Magic (Matrix) · Cognition (Quiet) · 11x (Quiet) ···        │   │
│  └───────────────────────────────────────────────────────────────┘   │
│                                                                       │
└──────────────────────────────────────────────────────────────────────┘
```

---

### 5.7 Startup–VC Match Page

```
┌──────────────────────────────────────────────────────────────────────┐
│ ◈ Meridian   > Match                                                 │
├──────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  Find Your Best-Fit VCs                                              │
│  Based on recent investments, stage, sector, and founder profile     │
│                                                                       │
│  ┌─── INPUT FORM ────────────────────────────────────────────────┐   │
│  │                                                               │   │
│  │  What are you building?                                       │   │
│  │  [________________________________________________]          │   │
│  │  e.g. "AI infrastructure for real-time data pipelines"        │   │
│  │                                                               │   │
│  │  Stage:  ○ Pre-Seed  ○ Seed  ○ Series A  ○ Series B          │   │
│  │                                                               │   │
│  │  Location: [City or Country ________________]                 │   │
│  │                                                               │   │
│  │  Your background (optional, improves match):                  │   │
│  │  [________________________________________________]          │   │
│  │  e.g. "ex-Google ML engineer, 8 years, first-time founder"   │   │
│  │                                                               │   │
│  │                          [Find My VCs →]                      │   │
│  └───────────────────────────────────────────────────────────────┘   │
│                                                                       │
│  ┌─── RESULTS ───────────────────────────────────────────────────┐   │
│  │                                                               │   │
│  │  Top 10 VCs for "AI infrastructure for real-time pipelines"  │   │
│  │                                                               │   │
│  │  #1  NEA Capital                         Match: ████████ 94% │   │
│  │      Why: Backed 8 AI infra cos recently. Avg founder has    │   │
│  │      7 yrs exp. Sector-leading deals in data pipeline space. │   │
│  │      [View Portfolio →]                                       │   │
│  │                                                               │   │
│  │  #2  Khosla Ventures                     Match: ███████  87% │   │
│  │      Why: ...                                                 │   │
│  │      [View Portfolio →]                                       │   │
│  │                                                               │   │
│  │                          [Export as CSV]                      │   │
│  └───────────────────────────────────────────────────────────────┘   │
│                                                                       │
└──────────────────────────────────────────────────────────────────────┘
```

---

## 6. Visualization Strategy

### Visualization Inventory

| Chart | Page | Library | Interactivity |
|-------|------|---------|---------------|
| **Age histogram** | Home + Founder Analytics | Recharts | Hover tooltip with companies, click to filter |
| **Funding scatter** | Founder Analytics | D3.js | Zoom, hover cards, quadrant overlays |
| **Sector donut** | Home + VC page | Recharts | Click segment to filter table |
| **Investment heatmap** | Home | D3.js | Hover cell = count + company list |
| **Stream / area chart** | Trends | D3.js | Toggle sectors, hover values |
| **Network graph** | /explore (unique feature) | D3-force | Pan/zoom, click nodes |
| **Geo bubble map** | Trends/Geography | Mapbox GL | Zoom, click city |
| **Bar race** | Trends | D3.js | Animated over years |
| **Radar chart** | VC comparison | Recharts | Compare 2–3 VCs side by side |
| **Sankey diagram** | Trends | D3.js | Hover to trace VC → Sector → Stage |

### Signature Visualizations (The WOW moments)

**1. The Network Graph** — `/explore` landing view
```
The most visually striking view. A force-directed graph where:
- Large nodes = VC firms (sized by portfolio count)
- Small nodes = portfolio companies (sized by funding raised)
- Edges = investment relationships
- Color = sector

User can:
  - Drag nodes to rearrange
  - Click a VC node to highlight only its investments
  - Click a company node to see details sidebar
  - Filter by sector (non-matching nodes fade to 10% opacity)
  - Search — matching nodes pulse
```

**2. The Founder Age Bubble Universe** — `/explore/founders`
```
Every company is a bubble:
- x-axis = founder age at founding
- y-axis = total funding raised
- bubble size = current valuation (or funding if no valuation)
- color = sector
- hover = founder name, company, VC, one-line bio

Quadrants labeled:
  Top-left:   "Young & Well-Funded" (sub-30, >$100M)
  Top-right:  "Experienced & Well-Funded" (30+, >$100M)
  Bottom-left: "Young & Early"
  Bottom-right: "Experienced & Early"

Toggle: show/hide labels, filter by VC, animate by year
```

**3. The VC DNA Radar** — `/explore/vcs/[slug]`
```
Radar chart comparing a VC's "investment personality" across 6 axes:
  ① Founder Youth Score (0–10: how young are their founders?)
  ② Stage Aggressiveness (seed vs growth)
  ③ Sector Diversity
  ④ Geographic Diversity
  ⑤ Technical Founder Preference (engineering vs business backgrounds)
  ⑥ Prior Founder Rate

Compare button: overlay two VCs to see their DNA side-by-side
```

**4. The Investment Sankey** — `/trends`
```
Flow diagram showing:
  VCs → Sectors → Investment Stages → Company Status (active/acquired/IPO)

Width of flow = total capital deployed
Hover any band = see exact $ amount and company list
```

**5. The "Who Gets Funded" Scatter** — `/explore/founders`
```
Controversial but interesting. A simple scatter plot:
  x = education tier (no degree → top-10 university)
  y = total funding raised

Each dot = a founder/company
Hover = details

This directly answers the question: does where you went to school
predict how much you raise? The data will tell the truth.
```

### Charting Libraries Decision

```
Recharts      → Most charts (easy React integration, good defaults)
D3.js         → Complex custom charts (network graph, sankey, stream)
Mapbox GL JS  → Geography maps (free tier: 50K loads/month)
Framer Motion → Animations and micro-interactions
```

---

## 7. Data Model & ERD

### Full Entity-Relationship Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                        MERIDIAN DATA MODEL                          │
└─────────────────────────────────────────────────────────────────────┘

┌──────────────────┐          ┌──────────────────────────────────────┐
│    vc_firms      │          │         portfolio_companies           │
├──────────────────┤          ├──────────────────────────────────────┤
│ id (PK)          │◄────┐    │ id (PK)                              │
│ name             │     │    │ vc_id (FK → vc_firms)                │
│ slug             │     └────│ name                                 │
│ website          │          │ slug                                 │
│ description      │          │ sector                               │
│ hq_city          │          │ subsector                            │
│ hq_country       │          │ founded_year                         │
│ hq_region        │          │ city                                 │
│ founded_year     │          │ country                              │
│ aum_usd          │          │ region                               │
│ fund_stage[]     │          │ stage           ← investment stage   │
│ focus_sectors[]  │          │ status                               │
│ logo_url         │          │ website                              │
│ linkedin_url     │          │ description                          │
│ created_at       │          │ source_url                           │
│ updated_at       │          │ last_verified                        │
│ data_quality     │          │ data_quality                         │
└──────────────────┘          │ created_at                           │
        │                     │ updated_at                           │
        │                     └──────────────────────────────────────┘
        │                                      │
        │                                      │ 1:many
        │                                      ▼
        │                     ┌──────────────────────────────────────┐
        │                     │            founders                   │
        │                     ├──────────────────────────────────────┤
        │                     │ id (PK)                              │
        │                     │ company_id (FK → portfolio_companies)│
        │                     │ full_name                            │
        │                     │ role            ← 'primary'/'co'     │
        │                     │ est_birth_year                       │
        │                     │ domain_exp_years                     │
        │                     │ prior_founder                        │
        │                     │ education_tier                       │
        │                     │ university                           │
        │                     │ degree                               │
        │                     │ grad_year                            │
        │                     │ age_at_founding  ← computed          │
        │                     │ current_age_2026 ← computed          │
        │                     │ age_confidence                       │
        │                     │ age_inference_method                 │
        │                     │ linkedin_url                         │
        │                     │ twitter_url                          │
        │                     │ nationality                          │
        │                     │ source_notes                         │
        │                     │ created_at                           │
        │                     └──────────────────────────────────────┘
        │
        │ 1:many
        ▼
┌──────────────────────┐      ┌──────────────────────────────────────┐
│   vc_fund_raises     │      │         funding_rounds               │
├──────────────────────┤      ├──────────────────────────────────────┤
│ id (PK)              │      │ id (PK)                              │
│ vc_id (FK)           │      │ company_id (FK)                      │
│ fund_name            │      │ round_name    ← 'Seed', 'Series A'   │
│ amount_usd           │      │ amount_usd                           │
│ announced_date       │      │ announced_date                       │
│ fund_number          │      │ lead_investor                        │
│ fund_stage_focus     │      │ co_investors[]                       │
│ sec_form_d_url       │      │ valuation_pre_usd                    │
│ source               │      │ valuation_post_usd                   │
│ created_at           │      │ source_url                           │
└──────────────────────┘      │ created_at                           │
                               └──────────────────────────────────────┘

┌──────────────────────┐      ┌──────────────────────────────────────┐
│      sectors         │      │          data_sources                │
├──────────────────────┤      ├──────────────────────────────────────┤
│ id (PK)              │      │ id (PK)                              │
│ name                 │      │ entity_type  ← 'company'/'founder'   │
│ slug                 │      │ entity_id                            │
│ parent_sector_id(FK) │      │ source_type  ← 'exa'/'manual'/etc    │
│ color_hex            │      │ source_url                           │
│ icon                 │      │ extracted_at                         │
│ description          │      │ model_used   ← which AI model        │
└──────────────────────┘      │ confidence                           │
                               └──────────────────────────────────────┘

┌──────────────────────┐
│    pipeline_runs     │  ← Audit log of every data collection run
├──────────────────────┤
│ id (PK)              │
│ vc_id (FK)           │
│ started_at           │
│ completed_at         │
│ companies_found      │
│ companies_added      │
│ companies_updated    │
│ errors_count         │
│ model_used           │
│ tokens_used          │
│ cost_usd             │
│ status               │
└──────────────────────┘
```

### Key Relationships Summary

```
vc_firms          ──< portfolio_companies    (1 VC → many companies)
portfolio_companies ──< founders             (1 company → many founders)
portfolio_companies ──< funding_rounds       (1 company → many rounds)
vc_firms          ──< vc_fund_raises         (1 VC → many fund raises)
sectors           ──< sectors                (self-referencing: subsectors)
*                 ──< data_sources           (any entity → many sources)
*                 ──< pipeline_runs          (any run → audit log)
```

### Computed Fields (Supabase Views)

```sql
-- Materialized view for dashboard stats (refresh daily)
CREATE MATERIALIZED VIEW mv_vc_stats AS
SELECT
  v.id,
  v.name,
  COUNT(c.id)                        AS company_count,
  AVG(f.age_at_founding)             AS avg_founder_age,
  PERCENTILE_CONT(0.5) WITHIN GROUP
    (ORDER BY f.age_at_founding)     AS median_founder_age,
  SUM(fr.amount_usd)                 AS total_portfolio_raised,
  COUNT(DISTINCT c.sector)           AS sector_diversity,
  AVG(f.domain_exp_years)            AS avg_founder_exp
FROM vc_firms v
LEFT JOIN portfolio_companies c ON c.vc_id = v.id
LEFT JOIN founders f ON f.company_id = c.id AND f.role = 'primary'
LEFT JOIN funding_rounds fr ON fr.company_id = c.id
GROUP BY v.id, v.name;
```

---

## 8. Feature Prioritization

### Must Have (Launch / Phase 1)
- [ ] VC directory with profile pages
- [ ] Company database with filters
- [ ] Founder analytics page (age histogram, scatter, education)
- [ ] Basic investment trends (sector breakdown)
- [ ] Mobile responsive layout
- [ ] Data download (CSV export)
- [ ] "Last updated" timestamps on all data
- [ ] Data confidence indicators (🟢 High / 🟡 Medium / 🔴 Low)
- [ ] Contribute page (link to GitHub)

### Should Have (v1.1)
- [ ] VC comparison (side-by-side radar chart)
- [ ] Network graph visualization
- [ ] Search (global, across all entities)
- [ ] Sector taxonomy browser
- [ ] Embeddable charts (for blog posts / reports)
- [ ] RSS / JSON feed of recent investments
- [ ] API endpoint (read-only, for developers)

### Nice to Have (v2)
- [ ] VC fund raise tracker (SEC EDGAR)
- [ ] Startup–VC match engine
- [ ] Email alerts ("new investments from NEA Capital")
- [ ] User accounts (save searches, watchlists)
- [ ] Verified badges (founder confirms their own data)
- [ ] Community corrections (flag incorrect data)

### Future Vision (v3+)
- [ ] Investor co-investment network (who co-invests with whom)
- [ ] LP tracking (who funds the VC funds)
- [ ] Founder exit outcomes (who sold, who IPO'd, who shut down)
- [ ] International expansion (EU, Asia, LatAm)
- [ ] AI-generated VC trend reports (weekly PDF digest)

---

## 9. Technical Architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│                      MERIDIAN ARCHITECTURE                           │
└──────────────────────────────────────────────────────────────────────┘

                    ┌─────────────────┐
                    │   GitHub Repo   │  ← Source of truth
                    │  (vc_list.yaml) │
                    └────────┬────────┘
                             │ Merge triggers
                             ▼
                    ┌─────────────────┐
                    │  GitHub Actions │  ← Weekly cron OR manual
                    │  (data-pipeline)│
                    └────────┬────────┘
                             │
              ┌──────────────┼──────────────┐
              ▼              ▼              ▼
      ┌──────────────┐ ┌──────────┐ ┌──────────────┐
      │   Exa API    │ │Playwright│ │ OpenRouter   │
      │(search+crawl)│ │(fallback)│ │(Deepseek/    │
      └──────┬───────┘ └────┬─────┘ │ Claude)      │
             │              │       └──────┬───────┘
             └──────────────┴──────────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │   Supabase DB   │  ← PostgreSQL
                    │  (data store)   │
                    └────────┬────────┘
                             │
              ┌──────────────┴──────────────┐
              ▼                             ▼
    ┌──────────────────┐         ┌──────────────────┐
    │  Next.js (Vercel)│         │   Excel Export   │
    │    Dashboard     │         │  (in GitHub repo)│
    └──────────────────┘         └──────────────────┘
```

### Stack Summary

| Layer | Technology | Hosting | Cost |
|-------|-----------|---------|------|
| Frontend | Next.js 14 + TypeScript | Vercel | Free |
| Database | PostgreSQL (Supabase) | Supabase | Free (500MB) |
| Pipeline | Python 3.11 | GitHub Actions | Free (2K min/month) |
| Search/Crawl | Exa API | Cloud | ~$10/month |
| AI Extraction | OpenRouter (Deepseek V3) | Cloud | ~$2/month |
| Complex AI | Claude API (Anthropic) | Cloud | ~$10/month |
| Geo Maps | Mapbox GL JS | CDN | Free (50K loads) |
| Monitoring | Axiom (logs) | Axiom | Free |
| **Total** | | | **~$22/month** |

---

## 10. Things You Haven't Covered Yet

Here is a complete gap analysis of what's missing from your current plan:

### Data & Content Gaps

**① Data Freshness & Staleness**
Every data point needs a `last_verified` timestamp and a freshness indicator in the UI. A company's funding round from 2022 is likely stale — they may have raised more. Users need to know this. Plan: show "verified X months ago" badges; flag anything >6 months old.

**② Data Confidence Scoring**
Your current Excel has `age_confidence` (High/Medium/Low) but this needs to be surfaced in the UI clearly. Users should know when they're looking at confirmed data vs. AI-inferred guesses. Without this, the platform lacks credibility.

**③ Company Status Tracking**
Some portfolio companies shut down, some get acquired, some IPO. You need a process to update `status` over time. Plan: include this in the weekly pipeline — if a company has no recent news, flag it for review.

**④ Co-investor Data**
Right now you track which VC led/participated in a round, but not who else co-invested. Co-investor network analysis (who invests alongside whom) is one of the most interesting signals for founders. This belongs in `funding_rounds.co_investors[]`.

### Product Gaps

**⑤ Mobile Experience**
You mentioned "Vercel deployment" but haven't addressed mobile. The network graph and dense data tables won't work on mobile without a completely different layout. Need a mobile-first component strategy — collapsible sections, swipeable cards for VC profiles, simplified charts.

**⑥ SEO Strategy**
Every VC page (`/explore/vcs/nea-capital`), every company page, and every founder analytics page should be server-side rendered (Next.js SSR/SSG) and optimized for search. Searches like "NEA Capital portfolio companies" should surface Meridian. This is free organic acquisition — don't overlook it.

**⑦ Empty State Design**
What does the dashboard look like when data is loading? What happens when a search returns zero results? What happens when the pipeline fails and data is stale? Need skeleton loaders, empty state illustrations, and error states designed upfront.

**⑧ Embeds / Shareability**
Researchers and journalists will want to embed a chart. "What's the average founder age in AI?" should be a shareable link that renders a single chart. Plan: `/embed/founder-age-histogram?sector=ai` returns an iframe-embeddable chart. This drives viral spread.

### Technical Gaps

**⑨ Rate Limiting & Pipeline Resilience**
Exa and OpenRouter have rate limits. The pipeline needs exponential backoff, retry logic, partial run resumption (if it crashes halfway through 50 VCs, it shouldn't restart from zero), and a run log stored in `pipeline_runs`.

**⑩ Data Validation Layer**
When the AI extracts data, it will occasionally hallucinate or return malformed JSON. Need a strict Pydantic schema validator that rejects bad data rather than inserting garbage into the database.

**⑪ Supabase Free Tier Limits**
Supabase free tier is 500MB storage and 50K API requests/day. With 438+ companies and growing, you'll hit this. Plan for upgrading to Pro ($25/month) when you cross ~200 VCs tracked. Budget for this.

**⑫ Search Index**
Full-text search across company names, founder names, VC names, and sectors. Supabase has built-in full-text search (PostgreSQL `tsvector`) — use it from day one, don't bolt it on later.

### Legal & Compliance Gaps

**⑬ Terms of Service / Data Sources**
Scraping LinkedIn is against their ToS. If your pipeline ever tries to scrape LinkedIn profiles (even indirectly via Exa), you're in grey territory. Explicitly document what sources you use and that you only use publicly available information. Add a `source_notes` field and a public data policy page.

**⑭ GDPR / Privacy**
Founder birth year and personal details are personal data under GDPR. Your `founders` table contains personal information about real people. You need: a Privacy Policy page, a way for founders to request their data be removed or corrected, and a note in your README about data sourcing ethics.

**⑮ Open Source License**
Decide on MIT (permissive, anyone can use/fork/commercialize) vs AGPL (copyleft, if you modify and host, you must open-source your version). MIT drives adoption; AGPL protects against someone cloning it and selling it. Recommendation: MIT for the code, but note that the data itself is not licensed for commercial resale.

### Community & Growth Gaps

**⑯ Contribution Recognition**
Contributors who submit VCs or correct data should be credited. GitHub contributors list plus a `/contributors` page showing who added what. This incentivizes participation.

**⑰ Launch Strategy**
Where are you launching this? Product Hunt (needs a launch day plan), Hacker News (Show HN post), LinkedIn, relevant Reddit communities (r/startups, r/venturecapital). Plan this before you build, because your build decisions should support the launch narrative.

**⑱ Analytics on the Dashboard Itself**
How will you know if anyone is using it? Add PostHog (free, open-source analytics) from day one. Track: page views by section, most-searched VCs, filter usage, chart interactions. This data will tell you what to build next.

---

## Summary: Build Order

```
Week 1:   Database schema → Supabase setup → seed with current 142 rows
Week 2:   Exa + OpenRouter pipeline → test on 5 VCs → validate output
Week 3:   Pipeline covers all 20 current VCs + expand to 50 total
Week 4:   Next.js project setup → routing → Supabase integration
Week 5:   Overview page + VC directory + basic charts
Week 6:   Founder analytics page + network graph (the WOW moment)
Week 7:   Company pages + search + mobile responsive
Week 8:   SEO (SSG for all pages) + embeds + PostHog analytics
Week 9:   Performance + data quality pass + privacy policy
Week 10:  Beta launch → Product Hunt / HN / LinkedIn
```

---

*Meridian Design Bible v1.0 — March 2026*
*Built for founders, by founders. Open-source forever.*
