// ============================================================================
// Meridian — TypeScript Types (matching Supabase schema)
// ============================================================================

export interface VCFirm {
  id: string
  name: string
  slug: string
  website: string | null
  description: string | null
  hq_city: string | null
  hq_country: string | null
  hq_region: string | null
  founded_year: number | null
  aum_usd: number | null
  fund_stage: string[]
  focus_sectors: string[]
  logo_url: string | null
  linkedin_url: string | null
  data_quality: 'high' | 'medium' | 'low'
  created_at: string
  updated_at: string
}

export interface Company {
  id: string
  name: string
  slug: string
  sector: string | null
  subsector: string | null
  founded_year: number | null
  city: string | null
  country: string | null
  region: string | null
  stage: string | null
  status: 'Active' | 'Acquired' | 'IPO' | 'Shutdown' | 'Unknown'
  status_detail: string | null
  website: string | null
  description: string | null
  total_raised_usd: number | null
  valuation_usd: number | null
  source_url: string | null
  last_verified: string | null
  data_quality: 'high' | 'medium' | 'low'
  created_at: string
  updated_at: string
}

export interface Investment {
  id: string
  vc_id: string
  company_id: string
  stage: string | null
  lead_investor: boolean
  announced_date: string | null
  source_url: string | null
  created_at: string
}

export interface Founder {
  id: string
  company_id: string
  full_name: string
  role: 'primary' | 'co-founder'
  est_birth_year: number | null
  domain_exp_years: number | null
  prior_founder: boolean
  education_tier: 'Top-10' | 'Top-50' | 'Other' | null
  university: string | null
  degree: string | null
  grad_year: number | null
  age_at_founding: number | null
  current_age_2026: number | null
  age_confidence: 'High' | 'Medium' | 'Low'
  age_inference_method: string | null
  linkedin_url: string | null
  twitter_url: string | null
  nationality: string | null
  source_notes: string | null
  created_at: string
}

export interface FundingRound {
  id: string
  company_id: string
  round_name: string | null
  amount_usd: number | null
  announced_date: string | null
  lead_investor: string | null
  co_investors: string[]
  valuation_pre_usd: number | null
  valuation_post_usd: number | null
  source_url: string | null
  created_at: string
}

export interface VCFundRaise {
  id: string
  vc_id: string
  fund_name: string | null
  amount_usd: number | null
  announced_date: string | null
  fund_number: number | null
  fund_stage_focus: string | null
  sec_form_d_url: string | null
  source: string | null
  created_at: string
}

// Materialized view types
export interface VCStats {
  id: string
  name: string
  slug: string
  company_count: number
  avg_founder_age: number | null
  median_founder_age: number | null
  min_founder_age: number | null
  max_founder_age: number | null
  sector_diversity: number
  avg_founder_exp: number | null
  prior_founder_count: number
  total_founders_profiled: number
  top_sector: string | null
}

export interface GlobalStats {
  total_vcs: number
  total_companies: number
  total_founders: number
  avg_founder_age: number | null
  median_founder_age: number | null
  youngest_founder_age: number | null
  oldest_founder_age: number | null
}

export interface SectorStat {
  sector: string
  company_count: number
  avg_founder_age: number | null
  recent_count: number
}

export interface AgeBucket {
  age_bucket: string
  count: number
  percentage: number
}

// Joined types for UI
export interface CompanyWithFounders extends Company {
  founders: Founder[]
  investments: (Investment & { vc_firm: VCFirm })[]
}

export interface VCWithPortfolio extends VCFirm {
  investments: (Investment & { company: Company })[]
  stats: VCStats | null
}

// Chart data types
export interface ChartDataPoint {
  name: string
  value: number
  color?: string
}

export interface ScatterDataPoint {
  x: number
  y: number
  name: string
  company: string
  sector: string
  size: number
}
