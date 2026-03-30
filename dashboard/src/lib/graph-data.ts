import type { VCFirm, Company, Investment } from './types'
import type { GraphNode, GraphLink, GraphData } from './graph-types'
import { formatCurrency } from './utils'
import { getSectorColor, VC_GRADIENT } from './graph-colors'

function vcNodeSize(vc: VCFirm): number {
  if (!vc.aum_usd) return 10
  return Math.max(8, Math.min(18, Math.log10(vc.aum_usd) * 1.6))
}

function companyNodeSize(company: Company): number {
  if (!company.total_raised_usd) return 4
  return Math.max(3, Math.min(8, Math.log10(company.total_raised_usd) * 1.0))
}

export function buildGraphData(
  vcs: VCFirm[],
  companies: Company[],
  investments: Investment[],
): GraphData {
  const nodes: GraphNode[] = []
  const links: GraphLink[] = []

  // Create VC nodes
  for (const vc of vcs) {
    nodes.push({
      id: vc.id,
      type: 'vc',
      name: vc.name,
      size: vcNodeSize(vc),
      color: VC_GRADIENT.primary,
      glowColor: VC_GRADIENT.glow,
      data: vc,
    })
  }

  // Build a set of company IDs that have investments (only show connected companies)
  const investedCompanyIds = new Set(investments.map(inv => inv.company_id))

  // Create Company nodes (only those with at least one investment link)
  for (const company of companies) {
    if (!investedCompanyIds.has(company.id)) continue
    const sectorColor = getSectorColor(company.sector)
    nodes.push({
      id: company.id,
      type: 'company',
      name: company.name,
      size: companyNodeSize(company),
      color: sectorColor,
      glowColor: sectorColor,
      sector: company.sector ?? undefined,
      data: company,
    })
  }

  // Create investment links
  const nodeIds = new Set(nodes.map(n => n.id))
  for (const inv of investments) {
    if (!nodeIds.has(inv.vc_id) || !nodeIds.has(inv.company_id)) continue
    links.push({
      source: inv.vc_id,
      target: inv.company_id,
      type: 'investment',
      strength: inv.lead_investor ? 1.0 : 0.6,
      label: inv.stage ?? undefined,
    })
  }

  // Compute co-investor links (VC↔VC based on shared portfolio companies)
  const vcPortfolios = new Map<string, Set<string>>()
  for (const inv of investments) {
    if (!nodeIds.has(inv.vc_id)) continue
    if (!vcPortfolios.has(inv.vc_id)) vcPortfolios.set(inv.vc_id, new Set())
    vcPortfolios.get(inv.vc_id)!.add(inv.company_id)
  }

  const vcIds = vcs.map(v => v.id).filter(id => nodeIds.has(id))
  let maxShared = 1
  const coInvestorPairs: { a: string; b: string; count: number }[] = []

  for (let i = 0; i < vcIds.length; i++) {
    for (let j = i + 1; j < vcIds.length; j++) {
      const portA = vcPortfolios.get(vcIds[i])
      const portB = vcPortfolios.get(vcIds[j])
      if (!portA || !portB) continue
      let shared = 0
      for (const compId of portA) {
        if (portB.has(compId)) shared++
      }
      if (shared > 0) {
        coInvestorPairs.push({ a: vcIds[i], b: vcIds[j], count: shared })
        maxShared = Math.max(maxShared, shared)
      }
    }
  }

  for (const pair of coInvestorPairs) {
    links.push({
      source: pair.a,
      target: pair.b,
      type: 'co-investor',
      strength: pair.count / maxShared,
    })
  }

  return { nodes, links }
}

export function getNodeTooltipInfo(node: GraphNode): {
  title: string
  subtitle: string
  details: string[]
} {
  if (node.type === 'vc') {
    const vc = node.data as VCFirm
    return {
      title: vc.name,
      subtitle: `VC Firm${vc.aum_usd ? ' · ' + formatCurrency(vc.aum_usd) + ' AUM' : ''}`,
      details: [
        vc.hq_city && vc.hq_country ? `${vc.hq_city}, ${vc.hq_country}` : '',
        vc.focus_sectors?.length ? `Focus: ${vc.focus_sectors.slice(0, 3).join(', ')}` : '',
      ].filter(Boolean),
    }
  }

  const company = node.data as Company
  return {
    title: company.name,
    subtitle: company.sector ?? 'Company',
    details: [
      company.stage ? `Stage: ${company.stage}` : '',
      company.founded_year ? `Founded ${company.founded_year}` : '',
      company.total_raised_usd ? `Raised ${formatCurrency(company.total_raised_usd)}` : '',
      company.city && company.country ? `${company.city}, ${company.country}` : '',
    ].filter(Boolean),
  }
}
