import { createClient } from '@supabase/supabase-js'
import type {
  VCFirm, Company, Founder, Investment,
  VCStats, GlobalStats, SectorStat, AgeBucket,
} from './types'

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL ?? ''
const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY ?? ''

// Returns null if env vars not configured — callers fall back to demo data
export const supabase = supabaseUrl && supabaseAnonKey
  ? createClient(supabaseUrl, supabaseAnonKey)
  : null as any

// ============================================================================
// VC Firms
// ============================================================================

export async function getVCFirms(): Promise<VCFirm[]> {
  // Supabase default limit is 1000 — paginate to get all
  const all: VCFirm[] = []
  let from = 0
  const batchSize = 1000
  while (true) {
    const { data, error } = await supabase
      .from('vc_firms')
      .select('*')
      .order('name')
      .range(from, from + batchSize - 1)
    if (error) throw error
    if (!data || data.length === 0) break
    all.push(...data)
    if (data.length < batchSize) break
    from += batchSize
  }
  return all
}

export async function getVCBySlug(slug: string): Promise<VCFirm | null> {
  const { data, error } = await supabase
    .from('vc_firms')
    .select('*')
    .eq('slug', slug)
    .single()
  if (error) return null
  return data
}

// ============================================================================
// Companies
// ============================================================================

export async function getCompanies(): Promise<Company[]> {
  const all: Company[] = []
  let from = 0
  const batchSize = 1000
  while (true) {
    const { data, error } = await supabase
      .from('portfolio_companies')
      .select('*')
      .order('name')
      .range(from, from + batchSize - 1)
    if (error) throw error
    if (!data || data.length === 0) break
    all.push(...data)
    if (data.length < batchSize) break
    from += batchSize
  }
  return all
}

export async function getCompanyBySlug(slug: string): Promise<Company | null> {
  const { data, error } = await supabase
    .from('portfolio_companies')
    .select('*')
    .eq('slug', slug)
    .single()
  if (error) return null
  return data
}

export async function getCompaniesByVC(vcId: string): Promise<(Company & { stage: string | null })[]> {
  const { data, error } = await supabase
    .from('investments')
    .select(`
      stage,
      company:portfolio_companies(*)
    `)
    .eq('vc_id', vcId)
  if (error) throw error
  return (data ?? []).map((d: Record<string, unknown>) => ({
    ...(d.company as Company),
    stage: d.stage as string | null,
  }))
}

// ============================================================================
// Founders
// ============================================================================

export async function getFounders(): Promise<Founder[]> {
  const all: Founder[] = []
  let from = 0
  const batchSize = 1000
  while (true) {
    const { data, error } = await supabase
      .from('founders')
      .select('*')
      .order('full_name')
      .range(from, from + batchSize - 1)
    if (error) throw error
    if (!data || data.length === 0) break
    all.push(...data)
    if (data.length < batchSize) break
    from += batchSize
  }
  return all
}

export async function getFoundersByCompany(companyId: string): Promise<Founder[]> {
  const { data, error } = await supabase
    .from('founders')
    .select('*')
    .eq('company_id', companyId)
    .order('role')
  if (error) throw error
  return data ?? []
}

export async function getPrimaryFounders(): Promise<Founder[]> {
  const { data, error } = await supabase
    .from('founders')
    .select('*')
    .eq('role', 'primary')
  if (error) throw error
  return data ?? []
}

// ============================================================================
// Investments
// ============================================================================

export async function getInvestmentsByVC(vcId: string): Promise<Investment[]> {
  const { data, error } = await supabase
    .from('investments')
    .select('*')
    .eq('vc_id', vcId)
  if (error) throw error
  return data ?? []
}

export async function getVCsForCompany(companyId: string): Promise<VCFirm[]> {
  const { data, error } = await supabase
    .from('investments')
    .select('vc:vc_firms(*)')
    .eq('company_id', companyId)
  if (error) throw error
  return (data ?? []).map((d: Record<string, unknown>) => d.vc as VCFirm)
}

// ============================================================================
// VCs with Investment Counts (replaces mv_vc_stats dependency)
// ============================================================================

export async function getVCsWithCounts(): Promise<(VCFirm & { company_count: number })[]> {
  // Fetch all VCs
  const vcs = await getVCFirms()

  // Fetch investment counts grouped by vc_id
  const { data: counts, error } = await supabase
    .from('investments')
    .select('vc_id')
  if (error) throw error

  // Count investments per VC
  const countMap = new Map<string, number>()
  for (const inv of counts ?? []) {
    countMap.set(inv.vc_id, (countMap.get(inv.vc_id) ?? 0) + 1)
  }

  return vcs.map(vc => ({
    ...vc,
    company_count: countMap.get(vc.id) ?? 0,
  }))
}

// ============================================================================
// Materialized Views (Stats)
// ============================================================================

export async function getVCStats(): Promise<VCStats[]> {
  const { data, error } = await supabase
    .from('mv_vc_stats')
    .select('*')
    .order('company_count', { ascending: false })
  if (error) throw error
  return data ?? []
}

export async function getGlobalStats(): Promise<GlobalStats | null> {
  const { data, error } = await supabase
    .from('mv_global_stats')
    .select('*')
    .single()
  if (error) return null
  return data
}

export async function getSectorStats(): Promise<SectorStat[]> {
  const { data, error } = await supabase
    .from('mv_sector_stats')
    .select('*')
  if (error) throw error
  return data ?? []
}

export async function getAgeBuckets(): Promise<AgeBucket[]> {
  const { data, error } = await supabase
    .from('mv_age_buckets')
    .select('*')
  if (error) throw error
  return data ?? []
}

// ============================================================================
// All Investments (for graph visualization)
// ============================================================================

export async function getInvestments(): Promise<Investment[]> {
  const all: Investment[] = []
  let from = 0
  const batchSize = 1000
  while (true) {
    const { data, error } = await supabase
      .from('investments')
      .select('*')
      .range(from, from + batchSize - 1)
    if (error) throw error
    if (!data || data.length === 0) break
    all.push(...data)
    if (data.length < batchSize) break
    from += batchSize
  }
  return all
}

// ============================================================================
// Search
// ============================================================================

export async function searchAll(query: string) {
  const tsQuery = query.split(' ').join(' & ')

  const [vcs, companies, founders] = await Promise.all([
    supabase.from('vc_firms').select('id, name, slug').textSearch('fts', tsQuery).limit(5),
    supabase.from('portfolio_companies').select('id, name, slug, sector').textSearch('fts', tsQuery).limit(10),
    supabase.from('founders').select('id, full_name, company_id').textSearch('fts', tsQuery).limit(10),
  ])

  return {
    vcs: vcs.data ?? [],
    companies: companies.data ?? [],
    founders: founders.data ?? [],
  }
}
