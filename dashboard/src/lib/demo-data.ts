// ============================================================================
// VC Radar — Demo/Seed Data for development without Supabase
// ============================================================================
// This data is derived from the seed Excel file and is used when
// NEXT_PUBLIC_SUPABASE_URL is not set.
// ============================================================================

import type {
  VCFirm, Company, Founder, Investment, VCStats,
  GlobalStats, SectorStat, AgeBucket,
} from './types'

export const demoVCFirms: VCFirm[] = [
  { id: '1', name: 'NEA Capital', slug: 'nea-capital', website: 'https://www.nea.com', description: 'New Enterprise Associates — one of the largest VC firms globally', hq_city: 'Menlo Park', hq_country: 'USA', hq_region: 'US-SF Bay', founded_year: 1978, aum_usd: 25000000000, fund_stage: ['Seed', 'Series A', 'Series B', 'Series C'], focus_sectors: ['AI', 'Enterprise', 'Consumer', 'Healthcare'], logo_url: null, linkedin_url: null, data_quality: 'high', created_at: '', updated_at: '' },
  { id: '2', name: 'NFX', slug: 'nfx', website: 'https://www.nfx.com', description: 'Seed-stage venture firm built by founders', hq_city: 'San Francisco', hq_country: 'USA', hq_region: 'US-SF Bay', founded_year: 2015, aum_usd: 2000000000, fund_stage: ['Pre-Seed', 'Seed'], focus_sectors: ['AI', 'Marketplace', 'Network Effects'], logo_url: null, linkedin_url: null, data_quality: 'high', created_at: '', updated_at: '' },
  { id: '3', name: 'Quiet Capital', slug: 'quiet-capital', website: 'https://quiet.com', description: 'Early-stage venture capital', hq_city: 'Los Angeles', hq_country: 'USA', hq_region: 'US-Other', founded_year: 2016, aum_usd: null, fund_stage: ['Seed', 'Series A'], focus_sectors: ['AI', 'Consumer', 'Enterprise'], logo_url: null, linkedin_url: null, data_quality: 'medium', created_at: '', updated_at: '' },
  { id: '4', name: 'Khosla Ventures', slug: 'khosla-ventures', website: 'https://www.khosla.com', description: 'Venture capital firm focused on impactful technologies', hq_city: 'Menlo Park', hq_country: 'USA', hq_region: 'US-SF Bay', founded_year: 2004, aum_usd: 15000000000, fund_stage: ['Seed', 'Series A', 'Series B'], focus_sectors: ['AI', 'Climate', 'Healthcare', 'Robotics'], logo_url: null, linkedin_url: null, data_quality: 'high', created_at: '', updated_at: '' },
  { id: '5', name: 'Basis Set Ventures', slug: 'basis-set-ventures', website: 'https://www.basisset.com', description: 'AI-focused venture capital', hq_city: 'San Francisco', hq_country: 'USA', hq_region: 'US-SF Bay', founded_year: 2018, aum_usd: null, fund_stage: ['Seed', 'Series A'], focus_sectors: ['AI', 'Enterprise'], logo_url: null, linkedin_url: null, data_quality: 'medium', created_at: '', updated_at: '' },
  { id: '6', name: 'Matrix Partners', slug: 'matrix-partners', website: 'https://www.matrixpartners.com', description: 'Early-stage venture capital since 1977', hq_city: 'San Francisco', hq_country: 'USA', hq_region: 'US-SF Bay', founded_year: 1977, aum_usd: 4000000000, fund_stage: ['Seed', 'Series A', 'Series B'], focus_sectors: ['AI', 'Enterprise', 'Infrastructure'], logo_url: null, linkedin_url: null, data_quality: 'high', created_at: '', updated_at: '' },
  { id: '7', name: 'Bain Capital Ventures', slug: 'bain-capital-ventures', website: 'https://www.baincapitalventures.com', description: 'Venture arm of Bain Capital', hq_city: 'Boston', hq_country: 'USA', hq_region: 'US-Other', founded_year: 2001, aum_usd: 8000000000, fund_stage: ['Seed', 'Series A', 'Series B', 'Growth'], focus_sectors: ['AI', 'Enterprise', 'Fintech', 'Healthcare'], logo_url: null, linkedin_url: null, data_quality: 'high', created_at: '', updated_at: '' },
  { id: '8', name: 'Race Capital', slug: 'race-capital', website: 'https://race.capital', description: 'Early-stage venture capital', hq_city: 'Palo Alto', hq_country: 'USA', hq_region: 'US-SF Bay', founded_year: 2020, aum_usd: null, fund_stage: ['Pre-Seed', 'Seed'], focus_sectors: ['AI', 'Fintech', 'Web3'], logo_url: null, linkedin_url: null, data_quality: 'medium', created_at: '', updated_at: '' },
  { id: '9', name: 'Unusual Ventures', slug: 'unusual-ventures', website: 'https://unusual.vc', description: 'Pre-seed and seed venture capital', hq_city: 'Menlo Park', hq_country: 'USA', hq_region: 'US-SF Bay', founded_year: 2018, aum_usd: null, fund_stage: ['Pre-Seed', 'Seed'], focus_sectors: ['AI', 'Enterprise', 'Security'], logo_url: null, linkedin_url: null, data_quality: 'medium', created_at: '', updated_at: '' },
  { id: '10', name: 'Kindred Ventures', slug: 'kindred-ventures', website: 'https://kindredventures.com', description: 'Seed-stage venture capital', hq_city: 'San Francisco', hq_country: 'USA', hq_region: 'US-SF Bay', founded_year: 2014, aum_usd: null, fund_stage: ['Seed'], focus_sectors: ['AI', 'Consumer', 'Fintech'], logo_url: null, linkedin_url: null, data_quality: 'medium', created_at: '', updated_at: '' },
]

export const demoCompanies: Company[] = [
  { id: 'c1', name: 'Perplexity AI', slug: 'perplexity-ai', sector: 'Consumer AI / Search', subsector: null, founded_year: 2022, city: 'San Francisco', country: 'USA', region: 'US-SF Bay', stage: 'Seed', status: 'Active', status_detail: null, website: null, description: null, total_raised_usd: null, valuation_usd: null, source_url: null, last_verified: null, data_quality: 'high', created_at: '', updated_at: '' },
  { id: 'c2', name: 'ElevenLabs', slug: 'elevenlabs', sector: 'AI Audio / Voice', subsector: null, founded_year: 2022, city: 'London', country: 'UK', region: 'Europe', stage: 'Series C', status: 'Active', status_detail: null, website: null, description: null, total_raised_usd: null, valuation_usd: null, source_url: null, last_verified: null, data_quality: 'high', created_at: '', updated_at: '' },
  { id: 'c3', name: 'Synthesia', slug: 'synthesia', sector: 'AI Video Generation', subsector: null, founded_year: 2017, city: 'London', country: 'UK', region: 'Europe', stage: 'Series D', status: 'Active', status_detail: null, website: null, description: null, total_raised_usd: null, valuation_usd: null, source_url: null, last_verified: null, data_quality: 'high', created_at: '', updated_at: '' },
  { id: 'c4', name: 'Together AI', slug: 'together-ai', sector: 'AI Infrastructure / Cloud', subsector: null, founded_year: 2022, city: 'San Francisco', country: 'USA', region: 'US-SF Bay', stage: 'Series A', status: 'Active', status_detail: null, website: null, description: null, total_raised_usd: null, valuation_usd: null, source_url: null, last_verified: null, data_quality: 'medium', created_at: '', updated_at: '' },
  { id: 'c5', name: 'World Labs', slug: 'world-labs', sector: 'Spatial AI / 3D Intelligence', subsector: null, founded_year: 2024, city: 'San Francisco', country: 'USA', region: 'US-SF Bay', stage: 'Seed', status: 'Active', status_detail: null, website: null, description: null, total_raised_usd: null, valuation_usd: null, source_url: null, last_verified: null, data_quality: 'medium', created_at: '', updated_at: '' },
  { id: 'c6', name: 'Poolside', slug: 'poolside', sector: 'AI Coding / Foundation Model', subsector: null, founded_year: 2023, city: 'San Francisco', country: 'USA', region: 'US-SF Bay', stage: 'Series B', status: 'Active', status_detail: null, website: null, description: null, total_raised_usd: 500000000, valuation_usd: null, source_url: null, last_verified: null, data_quality: 'high', created_at: '', updated_at: '' },
  { id: 'c7', name: 'Runway', slug: 'runway', sector: 'AI Video / Generative', subsector: null, founded_year: 2018, city: 'New York', country: 'USA', region: 'US-Other', stage: 'Series D', status: 'Active', status_detail: null, website: null, description: null, total_raised_usd: 237000000, valuation_usd: null, source_url: null, last_verified: null, data_quality: 'high', created_at: '', updated_at: '' },
  { id: 'c8', name: 'Cognition', slug: 'cognition', sector: 'AI Coding / Agent', subsector: null, founded_year: 2023, city: 'San Francisco', country: 'USA', region: 'US-SF Bay', stage: 'Series A', status: 'Active', status_detail: null, website: null, description: null, total_raised_usd: 175000000, valuation_usd: null, source_url: null, last_verified: null, data_quality: 'high', created_at: '', updated_at: '' },
]

export const demoFounders: Founder[] = [
  { id: 'f1', company_id: 'c1', full_name: 'Aravind Srinivas', role: 'primary', est_birth_year: 1993, domain_exp_years: 5, prior_founder: false, education_tier: 'Top-10', university: 'UC Berkeley', degree: null, grad_year: null, age_at_founding: 29, current_age_2026: 33, age_confidence: 'High', age_inference_method: 'Wikipedia', linkedin_url: null, twitter_url: null, nationality: null, source_notes: null, created_at: '' },
  { id: 'f2', company_id: 'c2', full_name: 'Mati Staniszewski', role: 'primary', est_birth_year: 1994, domain_exp_years: 4, prior_founder: false, education_tier: 'Top-50', university: 'University of Warsaw', degree: null, grad_year: null, age_at_founding: 28, current_age_2026: 32, age_confidence: 'Medium', age_inference_method: 'LinkedIn-education', linkedin_url: null, twitter_url: null, nationality: null, source_notes: null, created_at: '' },
  { id: 'f3', company_id: 'c3', full_name: 'Victor Riparbelli', role: 'primary', est_birth_year: 1991, domain_exp_years: 3, prior_founder: true, education_tier: 'Other', university: null, degree: null, grad_year: null, age_at_founding: 26, current_age_2026: 35, age_confidence: 'Medium', age_inference_method: 'LinkedIn-education', linkedin_url: null, twitter_url: null, nationality: null, source_notes: null, created_at: '' },
  { id: 'f4', company_id: 'c4', full_name: 'Vipul Ved Prakash', role: 'primary', est_birth_year: 1978, domain_exp_years: 20, prior_founder: true, education_tier: 'Top-50', university: null, degree: null, grad_year: null, age_at_founding: 44, current_age_2026: 48, age_confidence: 'Medium', age_inference_method: 'Career-timeline', linkedin_url: null, twitter_url: null, nationality: null, source_notes: null, created_at: '' },
  { id: 'f5', company_id: 'c5', full_name: 'Fei-Fei Li', role: 'primary', est_birth_year: 1976, domain_exp_years: 25, prior_founder: false, education_tier: 'Top-10', university: 'Stanford', degree: null, grad_year: null, age_at_founding: 48, current_age_2026: 50, age_confidence: 'High', age_inference_method: 'Wikipedia', linkedin_url: null, twitter_url: null, nationality: null, source_notes: null, created_at: '' },
  { id: 'f6', company_id: 'c6', full_name: 'Jason Warner', role: 'primary', est_birth_year: 1980, domain_exp_years: 20, prior_founder: false, education_tier: 'Other', university: 'Penn State', degree: null, grad_year: null, age_at_founding: 43, current_age_2026: 46, age_confidence: 'Low', age_inference_method: 'Pattern-inference', linkedin_url: null, twitter_url: null, nationality: null, source_notes: null, created_at: '' },
  { id: 'f7', company_id: 'c7', full_name: 'Cristóbal Valenzuela', role: 'primary', est_birth_year: 1994, domain_exp_years: 3, prior_founder: false, education_tier: 'Top-50', university: 'NYU', degree: null, grad_year: null, age_at_founding: 24, current_age_2026: 32, age_confidence: 'Medium', age_inference_method: 'LinkedIn-education', linkedin_url: null, twitter_url: null, nationality: null, source_notes: null, created_at: '' },
  { id: 'f8', company_id: 'c8', full_name: 'Scott Wu', role: 'primary', est_birth_year: 1999, domain_exp_years: 2, prior_founder: false, education_tier: 'Top-10', university: 'MIT', degree: null, grad_year: null, age_at_founding: 24, current_age_2026: 27, age_confidence: 'Medium', age_inference_method: 'Public-media', linkedin_url: null, twitter_url: null, nationality: null, source_notes: null, created_at: '' },
]

export const demoInvestments: Investment[] = [
  // NEA Capital investments
  { id: 'inv-1', vc_id: '1', company_id: 'c1', stage: 'Seed', lead_investor: true, announced_date: '2022-06-15', source_url: null, created_at: '' },
  { id: 'inv-2', vc_id: '1', company_id: 'c4', stage: 'Series A', lead_investor: false, announced_date: '2023-01-10', source_url: null, created_at: '' },
  { id: 'inv-3', vc_id: '1', company_id: 'c6', stage: 'Series B', lead_investor: true, announced_date: '2024-03-20', source_url: null, created_at: '' },
  // NFX investments
  { id: 'inv-4', vc_id: '2', company_id: 'c1', stage: 'Seed', lead_investor: false, announced_date: '2022-06-15', source_url: null, created_at: '' },
  { id: 'inv-5', vc_id: '2', company_id: 'c8', stage: 'Seed', lead_investor: true, announced_date: '2023-04-05', source_url: null, created_at: '' },
  // Quiet Capital investments
  { id: 'inv-6', vc_id: '3', company_id: 'c8', stage: 'Seed', lead_investor: false, announced_date: '2023-04-05', source_url: null, created_at: '' },
  { id: 'inv-7', vc_id: '3', company_id: 'c7', stage: 'Series A', lead_investor: false, announced_date: '2020-11-15', source_url: null, created_at: '' },
  // Khosla Ventures investments
  { id: 'inv-8', vc_id: '4', company_id: 'c5', stage: 'Seed', lead_investor: true, announced_date: '2024-05-01', source_url: null, created_at: '' },
  { id: 'inv-9', vc_id: '4', company_id: 'c4', stage: 'Series A', lead_investor: true, announced_date: '2023-01-10', source_url: null, created_at: '' },
  { id: 'inv-10', vc_id: '4', company_id: 'c1', stage: 'Series B', lead_investor: false, announced_date: '2024-01-20', source_url: null, created_at: '' },
  // Basis Set Ventures investments
  { id: 'inv-11', vc_id: '5', company_id: 'c4', stage: 'Seed', lead_investor: false, announced_date: '2022-08-01', source_url: null, created_at: '' },
  { id: 'inv-12', vc_id: '5', company_id: 'c2', stage: 'Series A', lead_investor: false, announced_date: '2023-06-15', source_url: null, created_at: '' },
  // Matrix Partners investments
  { id: 'inv-13', vc_id: '6', company_id: 'c2', stage: 'Series B', lead_investor: true, announced_date: '2024-01-10', source_url: null, created_at: '' },
  { id: 'inv-14', vc_id: '6', company_id: 'c3', stage: 'Series C', lead_investor: false, announced_date: '2023-07-20', source_url: null, created_at: '' },
  // Bain Capital Ventures investments
  { id: 'inv-15', vc_id: '7', company_id: 'c6', stage: 'Series A', lead_investor: false, announced_date: '2023-09-15', source_url: null, created_at: '' },
  { id: 'inv-16', vc_id: '7', company_id: 'c3', stage: 'Series D', lead_investor: true, announced_date: '2024-06-01', source_url: null, created_at: '' },
  // Race Capital investments
  { id: 'inv-17', vc_id: '8', company_id: 'c1', stage: 'Pre-Seed', lead_investor: false, announced_date: '2022-01-10', source_url: null, created_at: '' },
  { id: 'inv-18', vc_id: '8', company_id: 'c7', stage: 'Seed', lead_investor: false, announced_date: '2019-05-20', source_url: null, created_at: '' },
  // Unusual Ventures investments
  { id: 'inv-19', vc_id: '9', company_id: 'c8', stage: 'Seed', lead_investor: false, announced_date: '2023-04-05', source_url: null, created_at: '' },
  { id: 'inv-20', vc_id: '9', company_id: 'c5', stage: 'Seed', lead_investor: false, announced_date: '2024-05-01', source_url: null, created_at: '' },
  // Kindred Ventures investments
  { id: 'inv-21', vc_id: '10', company_id: 'c7', stage: 'Seed', lead_investor: true, announced_date: '2019-05-20', source_url: null, created_at: '' },
  { id: 'inv-22', vc_id: '10', company_id: 'c2', stage: 'Seed', lead_investor: false, announced_date: '2022-10-01', source_url: null, created_at: '' },
]

export const demoVCStats: VCStats[] = [
  { id: '1', name: 'NEA Capital', slug: 'nea-capital', company_count: 32, avg_founder_age: 31.2, median_founder_age: 30, min_founder_age: 22, max_founder_age: 52, sector_diversity: 12, avg_founder_exp: 8.5, prior_founder_count: 9, total_founders_profiled: 32, top_sector: 'AI Infrastructure' },
  { id: '2', name: 'NFX', slug: 'nfx', company_count: 16, avg_founder_age: 29.8, median_founder_age: 29, min_founder_age: 22, max_founder_age: 45, sector_diversity: 8, avg_founder_exp: 6.2, prior_founder_count: 5, total_founders_profiled: 16, top_sector: 'AI Apps' },
  { id: '3', name: 'Quiet Capital', slug: 'quiet-capital', company_count: 13, avg_founder_age: 28.5, median_founder_age: 27, min_founder_age: 20, max_founder_age: 40, sector_diversity: 7, avg_founder_exp: 5.1, prior_founder_count: 3, total_founders_profiled: 13, top_sector: 'AI Coding' },
  { id: '4', name: 'Khosla Ventures', slug: 'khosla-ventures', company_count: 10, avg_founder_age: 33.8, median_founder_age: 33, min_founder_age: 24, max_founder_age: 48, sector_diversity: 6, avg_founder_exp: 10.3, prior_founder_count: 4, total_founders_profiled: 10, top_sector: 'AI / Deep Tech' },
  { id: '5', name: 'Basis Set Ventures', slug: 'basis-set-ventures', company_count: 7, avg_founder_age: 31.0, median_founder_age: 30, min_founder_age: 25, max_founder_age: 38, sector_diversity: 5, avg_founder_exp: 7.5, prior_founder_count: 2, total_founders_profiled: 7, top_sector: 'AI Enterprise' },
  { id: '6', name: 'Matrix Partners', slug: 'matrix-partners', company_count: 7, avg_founder_age: 29.4, median_founder_age: 28, min_founder_age: 23, max_founder_age: 40, sector_diversity: 5, avg_founder_exp: 6.0, prior_founder_count: 2, total_founders_profiled: 7, top_sector: 'AI Apps' },
  { id: '7', name: 'Bain Capital Ventures', slug: 'bain-capital-ventures', company_count: 6, avg_founder_age: 35.2, median_founder_age: 34, min_founder_age: 28, max_founder_age: 43, sector_diversity: 4, avg_founder_exp: 11.0, prior_founder_count: 3, total_founders_profiled: 6, top_sector: 'AI Coding' },
  { id: '8', name: 'Race Capital', slug: 'race-capital', company_count: 6, avg_founder_age: 27.5, median_founder_age: 27, min_founder_age: 22, max_founder_age: 35, sector_diversity: 5, avg_founder_exp: 4.2, prior_founder_count: 1, total_founders_profiled: 6, top_sector: 'AI Apps' },
  { id: '9', name: 'Unusual Ventures', slug: 'unusual-ventures', company_count: 6, avg_founder_age: 30.0, median_founder_age: 29, min_founder_age: 24, max_founder_age: 38, sector_diversity: 4, avg_founder_exp: 7.0, prior_founder_count: 2, total_founders_profiled: 6, top_sector: 'AI Security' },
  { id: '10', name: 'Kindred Ventures', slug: 'kindred-ventures', company_count: 5, avg_founder_age: 29.0, median_founder_age: 28, min_founder_age: 24, max_founder_age: 36, sector_diversity: 4, avg_founder_exp: 5.5, prior_founder_count: 1, total_founders_profiled: 5, top_sector: 'AI Consumer' },
]

export const demoGlobalStats: GlobalStats = {
  total_vcs: 20,
  total_companies: 142,
  total_founders: 142,
  avg_founder_age: 31.4,
  median_founder_age: 29,
  youngest_founder_age: 20,
  oldest_founder_age: 55,
}

export const demoSectorStats: SectorStat[] = [
  { sector: 'AI Infrastructure / Cloud', company_count: 28, avg_founder_age: 33.2, recent_count: 15 },
  { sector: 'AI Apps / Consumer', company_count: 22, avg_founder_age: 28.5, recent_count: 14 },
  { sector: 'AI Coding / Dev Tools', company_count: 18, avg_founder_age: 27.8, recent_count: 12 },
  { sector: 'AI Security / Cybersecurity', company_count: 14, avg_founder_age: 32.1, recent_count: 8 },
  { sector: 'AI Healthcare / Biotech', company_count: 12, avg_founder_age: 35.4, recent_count: 6 },
  { sector: 'Robotics / Autonomy', company_count: 10, avg_founder_age: 34.0, recent_count: 5 },
  { sector: 'Fintech / AI Finance', company_count: 9, avg_founder_age: 31.0, recent_count: 4 },
  { sector: 'AI Video / Generative', company_count: 8, avg_founder_age: 28.0, recent_count: 6 },
  { sector: 'Enterprise AI / SaaS', company_count: 7, avg_founder_age: 30.5, recent_count: 3 },
  { sector: 'Other', company_count: 14, avg_founder_age: 31.8, recent_count: 5 },
]

export const demoAgeBuckets: AgeBucket[] = [
  { age_bucket: '<22', count: 3, percentage: 2.1 },
  { age_bucket: '22-25', count: 18, percentage: 12.7 },
  { age_bucket: '26-29', count: 42, percentage: 29.6 },
  { age_bucket: '30-33', count: 35, percentage: 24.6 },
  { age_bucket: '34-37', count: 20, percentage: 14.1 },
  { age_bucket: '38-41', count: 12, percentage: 8.5 },
  { age_bucket: '42-45', count: 8, percentage: 5.6 },
  { age_bucket: '46+', count: 4, percentage: 2.8 },
]
