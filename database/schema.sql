-- ============================================================================
-- MERIDIAN — Database Schema for Supabase (PostgreSQL)
-- ============================================================================
-- Run this in your Supabase SQL Editor to set up the full schema.
-- ============================================================================

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";  -- For fuzzy text search

-- ============================================================================
-- CORE TABLES
-- ============================================================================

-- VC Firms
CREATE TABLE vc_firms (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  name TEXT NOT NULL UNIQUE,
  slug TEXT NOT NULL UNIQUE,
  website TEXT,
  description TEXT,
  hq_city TEXT,
  hq_country TEXT,
  hq_region TEXT,
  founded_year INT,
  aum_usd BIGINT,                      -- Assets under management
  fund_stage TEXT[] DEFAULT '{}',       -- ['seed', 'series_a', 'series_b']
  focus_sectors TEXT[] DEFAULT '{}',    -- ['ai', 'fintech', 'deeptech']
  logo_url TEXT,
  linkedin_url TEXT,
  data_quality TEXT DEFAULT 'medium' CHECK (data_quality IN ('high', 'medium', 'low')),
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

-- Portfolio Companies
CREATE TABLE portfolio_companies (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  name TEXT NOT NULL,
  slug TEXT NOT NULL UNIQUE,
  sector TEXT,
  subsector TEXT,
  founded_year INT,
  city TEXT,
  country TEXT,
  region TEXT,
  stage TEXT CHECK (stage IN ('Pre-Seed', 'Seed', 'Early', 'Series A', 'Series B', 'Series C', 'Series D', 'Series E', 'Growth', NULL)),
  status TEXT DEFAULT 'Active' CHECK (status IN ('Active', 'Acquired', 'IPO', 'Shutdown', 'Unknown')),
  status_detail TEXT,                   -- e.g. "Acquired by Amazon 2024"
  website TEXT,
  description TEXT,
  total_raised_usd BIGINT,
  valuation_usd BIGINT,
  source_url TEXT,
  last_verified TIMESTAMPTZ DEFAULT now(),
  data_quality TEXT DEFAULT 'medium' CHECK (data_quality IN ('high', 'medium', 'low')),
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

-- Investments (junction table: VC → Company, many-to-many)
CREATE TABLE investments (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  vc_id UUID NOT NULL REFERENCES vc_firms(id) ON DELETE CASCADE,
  company_id UUID NOT NULL REFERENCES portfolio_companies(id) ON DELETE CASCADE,
  stage TEXT,                           -- Investment stage at time of investment
  lead_investor BOOLEAN DEFAULT false,
  announced_date DATE,
  source_url TEXT,
  created_at TIMESTAMPTZ DEFAULT now(),
  UNIQUE(vc_id, company_id)
);

-- Founders
CREATE TABLE founders (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  company_id UUID NOT NULL REFERENCES portfolio_companies(id) ON DELETE CASCADE,
  full_name TEXT NOT NULL,
  role TEXT DEFAULT 'primary' CHECK (role IN ('primary', 'co-founder')),
  est_birth_year INT,
  domain_exp_years INT,
  prior_founder BOOLEAN DEFAULT false,
  education_tier TEXT CHECK (education_tier IN ('Top-10', 'Top-50', 'Other', NULL)),
  university TEXT,
  degree TEXT,
  grad_year INT,
  age_at_founding INT,                  -- Computed: founded_year - est_birth_year
  current_age_2026 INT,                 -- Computed: 2026 - est_birth_year
  age_confidence TEXT DEFAULT 'low' CHECK (age_confidence IN ('High', 'Medium', 'Low')),
  age_inference_method TEXT,
  linkedin_url TEXT,
  twitter_url TEXT,
  nationality TEXT,
  source_notes TEXT,
  created_at TIMESTAMPTZ DEFAULT now()
);

-- Funding Rounds (per company)
CREATE TABLE funding_rounds (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  company_id UUID NOT NULL REFERENCES portfolio_companies(id) ON DELETE CASCADE,
  round_name TEXT,                      -- 'Seed', 'Series A', etc.
  amount_usd BIGINT,
  announced_date DATE,
  lead_investor TEXT,
  co_investors TEXT[] DEFAULT '{}',
  valuation_pre_usd BIGINT,
  valuation_post_usd BIGINT,
  source_url TEXT,
  created_at TIMESTAMPTZ DEFAULT now()
);

-- VC Fund Raises (Phase 3 - the VC's own fundraising)
CREATE TABLE vc_fund_raises (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  vc_id UUID NOT NULL REFERENCES vc_firms(id) ON DELETE CASCADE,
  fund_name TEXT,
  amount_usd BIGINT,
  announced_date DATE,
  fund_number INT,
  fund_stage_focus TEXT,
  sec_form_d_url TEXT,
  source TEXT,
  created_at TIMESTAMPTZ DEFAULT now()
);

-- Sectors taxonomy
CREATE TABLE sectors (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  name TEXT NOT NULL UNIQUE,
  slug TEXT NOT NULL UNIQUE,
  parent_sector_id UUID REFERENCES sectors(id),
  color_hex TEXT,
  icon TEXT,
  description TEXT
);

-- Data provenance tracking
CREATE TABLE data_sources (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  entity_type TEXT NOT NULL CHECK (entity_type IN ('company', 'founder', 'vc_firm', 'funding_round')),
  entity_id UUID NOT NULL,
  source_type TEXT CHECK (source_type IN ('manual', 'exa', 'serper', 'playwright', 'sec_edgar', 'user_submission')),
  source_url TEXT,
  extracted_at TIMESTAMPTZ DEFAULT now(),
  model_used TEXT,                       -- Which AI model extracted the data
  confidence FLOAT CHECK (confidence BETWEEN 0 AND 1)
);

-- Pipeline run audit log
CREATE TABLE pipeline_runs (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  vc_id UUID REFERENCES vc_firms(id),
  started_at TIMESTAMPTZ DEFAULT now(),
  completed_at TIMESTAMPTZ,
  companies_found INT DEFAULT 0,
  companies_added INT DEFAULT 0,
  companies_updated INT DEFAULT 0,
  founders_added INT DEFAULT 0,
  errors_count INT DEFAULT 0,
  error_details JSONB DEFAULT '[]',
  model_used TEXT,
  tokens_used INT DEFAULT 0,
  cost_usd NUMERIC(10, 4) DEFAULT 0,
  status TEXT DEFAULT 'running' CHECK (status IN ('running', 'completed', 'failed', 'partial'))
);

-- ============================================================================
-- INDEXES
-- ============================================================================

-- VC Firms
CREATE INDEX idx_vc_firms_slug ON vc_firms(slug);
CREATE INDEX idx_vc_firms_name_trgm ON vc_firms USING gin(name gin_trgm_ops);

-- Portfolio Companies
CREATE INDEX idx_companies_slug ON portfolio_companies(slug);
CREATE INDEX idx_companies_sector ON portfolio_companies(sector);
CREATE INDEX idx_companies_status ON portfolio_companies(status);
CREATE INDEX idx_companies_founded_year ON portfolio_companies(founded_year);
CREATE INDEX idx_companies_region ON portfolio_companies(region);
CREATE INDEX idx_companies_name_trgm ON portfolio_companies USING gin(name gin_trgm_ops);

-- Investments
CREATE INDEX idx_investments_vc_id ON investments(vc_id);
CREATE INDEX idx_investments_company_id ON investments(company_id);

-- Founders
CREATE INDEX idx_founders_company_id ON founders(company_id);
CREATE INDEX idx_founders_role ON founders(role);
CREATE INDEX idx_founders_age_at_founding ON founders(age_at_founding);
CREATE INDEX idx_founders_education_tier ON founders(education_tier);
CREATE INDEX idx_founders_name_trgm ON founders USING gin(full_name gin_trgm_ops);

-- Funding Rounds
CREATE INDEX idx_funding_rounds_company_id ON funding_rounds(company_id);

-- VC Fund Raises
CREATE INDEX idx_fund_raises_vc_id ON vc_fund_raises(vc_id);

-- Data Sources
CREATE INDEX idx_data_sources_entity ON data_sources(entity_type, entity_id);

-- Pipeline Runs
CREATE INDEX idx_pipeline_runs_vc_id ON pipeline_runs(vc_id);
CREATE INDEX idx_pipeline_runs_status ON pipeline_runs(status);

-- ============================================================================
-- FULL-TEXT SEARCH
-- ============================================================================

-- Add tsvector columns for full-text search
ALTER TABLE vc_firms ADD COLUMN fts tsvector
  GENERATED ALWAYS AS (to_tsvector('english', coalesce(name, '') || ' ' || coalesce(description, ''))) STORED;

ALTER TABLE portfolio_companies ADD COLUMN fts tsvector
  GENERATED ALWAYS AS (to_tsvector('english', coalesce(name, '') || ' ' || coalesce(sector, '') || ' ' || coalesce(subsector, '') || ' ' || coalesce(description, ''))) STORED;

ALTER TABLE founders ADD COLUMN fts tsvector
  GENERATED ALWAYS AS (to_tsvector('english', coalesce(full_name, '') || ' ' || coalesce(university, '') || ' ' || coalesce(source_notes, ''))) STORED;

CREATE INDEX idx_vc_firms_fts ON vc_firms USING gin(fts);
CREATE INDEX idx_companies_fts ON portfolio_companies USING gin(fts);
CREATE INDEX idx_founders_fts ON founders USING gin(fts);

-- ============================================================================
-- MATERIALIZED VIEWS
-- ============================================================================

-- VC stats aggregation (refresh daily or after pipeline runs)
CREATE MATERIALIZED VIEW mv_vc_stats AS
SELECT
  v.id,
  v.name,
  v.slug,
  COUNT(DISTINCT c.id) AS company_count,
  AVG(f.age_at_founding)::NUMERIC(4,1) AS avg_founder_age,
  PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY f.age_at_founding)::NUMERIC(4,1) AS median_founder_age,
  MIN(f.age_at_founding) AS min_founder_age,
  MAX(f.age_at_founding) AS max_founder_age,
  COUNT(DISTINCT c.sector) AS sector_diversity,
  AVG(f.domain_exp_years)::NUMERIC(4,1) AS avg_founder_exp,
  COUNT(CASE WHEN f.prior_founder THEN 1 END) AS prior_founder_count,
  COUNT(f.id) AS total_founders_profiled,
  MODE() WITHIN GROUP (ORDER BY c.sector) AS top_sector
FROM vc_firms v
LEFT JOIN investments i ON i.vc_id = v.id
LEFT JOIN portfolio_companies c ON c.id = i.company_id
LEFT JOIN founders f ON f.company_id = c.id AND f.role = 'primary'
GROUP BY v.id, v.name, v.slug;

CREATE UNIQUE INDEX idx_mv_vc_stats_id ON mv_vc_stats(id);

-- Global stats for overview page
CREATE MATERIALIZED VIEW mv_global_stats AS
SELECT
  (SELECT COUNT(*) FROM vc_firms) AS total_vcs,
  (SELECT COUNT(*) FROM portfolio_companies) AS total_companies,
  (SELECT COUNT(*) FROM founders) AS total_founders,
  (SELECT AVG(age_at_founding)::NUMERIC(4,1) FROM founders WHERE role = 'primary') AS avg_founder_age,
  (SELECT PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY age_at_founding)::NUMERIC(4,1) FROM founders WHERE role = 'primary') AS median_founder_age,
  (SELECT MIN(age_at_founding) FROM founders WHERE role = 'primary') AS youngest_founder_age,
  (SELECT MAX(age_at_founding) FROM founders WHERE role = 'primary') AS oldest_founder_age;

-- Sector breakdown
CREATE MATERIALIZED VIEW mv_sector_stats AS
SELECT
  c.sector,
  COUNT(*) AS company_count,
  AVG(f.age_at_founding)::NUMERIC(4,1) AS avg_founder_age,
  COUNT(CASE WHEN c.founded_year >= 2023 THEN 1 END) AS recent_count
FROM portfolio_companies c
LEFT JOIN founders f ON f.company_id = c.id AND f.role = 'primary'
WHERE c.sector IS NOT NULL
GROUP BY c.sector
ORDER BY company_count DESC;

-- Age bucket distribution
CREATE MATERIALIZED VIEW mv_age_buckets AS
SELECT
  CASE
    WHEN f.age_at_founding < 22 THEN '<22'
    WHEN f.age_at_founding BETWEEN 22 AND 25 THEN '22-25'
    WHEN f.age_at_founding BETWEEN 26 AND 29 THEN '26-29'
    WHEN f.age_at_founding BETWEEN 30 AND 33 THEN '30-33'
    WHEN f.age_at_founding BETWEEN 34 AND 37 THEN '34-37'
    WHEN f.age_at_founding BETWEEN 38 AND 41 THEN '38-41'
    WHEN f.age_at_founding BETWEEN 42 AND 45 THEN '42-45'
    WHEN f.age_at_founding > 45 THEN '46+'
  END AS age_bucket,
  COUNT(*) AS count,
  ROUND(COUNT(*)::NUMERIC / NULLIF(SUM(COUNT(*)) OVER(), 0) * 100, 1) AS percentage
FROM founders f
WHERE f.role = 'primary' AND f.age_at_founding IS NOT NULL
GROUP BY age_bucket
ORDER BY MIN(f.age_at_founding);

-- ============================================================================
-- ROW LEVEL SECURITY (RLS)
-- ============================================================================

-- Enable RLS on all tables (read-only for anonymous users)
ALTER TABLE vc_firms ENABLE ROW LEVEL SECURITY;
ALTER TABLE portfolio_companies ENABLE ROW LEVEL SECURITY;
ALTER TABLE investments ENABLE ROW LEVEL SECURITY;
ALTER TABLE founders ENABLE ROW LEVEL SECURITY;
ALTER TABLE funding_rounds ENABLE ROW LEVEL SECURITY;
ALTER TABLE vc_fund_raises ENABLE ROW LEVEL SECURITY;
ALTER TABLE sectors ENABLE ROW LEVEL SECURITY;
ALTER TABLE pipeline_runs ENABLE ROW LEVEL SECURITY;

-- Public read access for all tables
CREATE POLICY "Public read access" ON vc_firms FOR SELECT USING (true);
CREATE POLICY "Public read access" ON portfolio_companies FOR SELECT USING (true);
CREATE POLICY "Public read access" ON investments FOR SELECT USING (true);
CREATE POLICY "Public read access" ON founders FOR SELECT USING (true);
CREATE POLICY "Public read access" ON funding_rounds FOR SELECT USING (true);
CREATE POLICY "Public read access" ON vc_fund_raises FOR SELECT USING (true);
CREATE POLICY "Public read access" ON sectors FOR SELECT USING (true);
CREATE POLICY "Public read access" ON pipeline_runs FOR SELECT USING (true);

-- Service role can write (used by pipeline)
CREATE POLICY "Service role write" ON vc_firms FOR ALL USING (auth.role() = 'service_role');
CREATE POLICY "Service role write" ON portfolio_companies FOR ALL USING (auth.role() = 'service_role');
CREATE POLICY "Service role write" ON investments FOR ALL USING (auth.role() = 'service_role');
CREATE POLICY "Service role write" ON founders FOR ALL USING (auth.role() = 'service_role');
CREATE POLICY "Service role write" ON funding_rounds FOR ALL USING (auth.role() = 'service_role');
CREATE POLICY "Service role write" ON vc_fund_raises FOR ALL USING (auth.role() = 'service_role');
CREATE POLICY "Service role write" ON sectors FOR ALL USING (auth.role() = 'service_role');
CREATE POLICY "Service role write" ON pipeline_runs FOR ALL USING (auth.role() = 'service_role');

-- ============================================================================
-- FUNCTIONS
-- ============================================================================

-- Function to refresh all materialized views
CREATE OR REPLACE FUNCTION refresh_materialized_views()
RETURNS void AS $$
BEGIN
  REFRESH MATERIALIZED VIEW CONCURRENTLY mv_vc_stats;
  REFRESH MATERIALIZED VIEW mv_global_stats;
  REFRESH MATERIALIZED VIEW mv_sector_stats;
  REFRESH MATERIALIZED VIEW mv_age_buckets;
END;
$$ LANGUAGE plpgsql;

-- Auto-update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER tr_vc_firms_updated_at
  BEFORE UPDATE ON vc_firms
  FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER tr_companies_updated_at
  BEFORE UPDATE ON portfolio_companies
  FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- Slug generation helper
CREATE OR REPLACE FUNCTION generate_slug(input TEXT)
RETURNS TEXT AS $$
BEGIN
  RETURN lower(regexp_replace(regexp_replace(input, '[^a-zA-Z0-9\s-]', '', 'g'), '\s+', '-', 'g'));
END;
$$ LANGUAGE plpgsql;
