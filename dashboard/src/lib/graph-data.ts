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
  // Use company→VCs reverse index for O(companies * avgVCsPerCompany²) instead of O(VCs²)
  const companyToVCs = new Map<string, string[]>()
  for (const inv of investments) {
    if (!nodeIds.has(inv.vc_id) || !nodeIds.has(inv.company_id)) continue
    if (!companyToVCs.has(inv.company_id)) companyToVCs.set(inv.company_id, [])
    companyToVCs.get(inv.company_id)!.push(inv.vc_id)
  }

  const pairCounts = new Map<string, number>()
  let maxShared = 1
  for (const [, vcList] of companyToVCs) {
    if (vcList.length < 2) continue
    for (let i = 0; i < vcList.length; i++) {
      for (let j = i + 1; j < vcList.length; j++) {
        const key = vcList[i] < vcList[j] ? `${vcList[i]}|${vcList[j]}` : `${vcList[j]}|${vcList[i]}`
        const count = (pairCounts.get(key) || 0) + 1
        pairCounts.set(key, count)
        maxShared = Math.max(maxShared, count)
      }
    }
  }

  // On large graphs, only keep significant co-investor links (2+ shared companies)
  const minShared = nodes.length > 3000 ? 3 : nodes.length > 1000 ? 2 : 1
  for (const [key, count] of pairCounts) {
    if (count < minShared) continue
    const [a, b] = key.split('|')
    links.push({
      source: a,
      target: b,
      type: 'co-investor',
      strength: count / maxShared,
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
