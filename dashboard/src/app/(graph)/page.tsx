import { GraphPage } from '@/components/graph/GraphPage'
import {
  demoVCFirms, demoCompanies, demoInvestments,
} from '@/lib/demo-data'
import { getVCFirms, getCompanies, getInvestments } from '@/lib/supabase'
import type { VCFirm, Company, Investment } from '@/lib/types'

async function fetchGraphData(): Promise<{
  vcs: VCFirm[]
  companies: Company[]
  investments: Investment[]
}> {
  try {
    const [vcs, companies, investments] = await Promise.all([
      getVCFirms(),
      getCompanies(),
      getInvestments(),
    ])

    if (vcs.length === 0 || companies.length === 0) {
      return {
        vcs: demoVCFirms,
        companies: demoCompanies,
        investments: demoInvestments,
      }
    }

    return { vcs, companies, investments }
  } catch {
    return {
      vcs: demoVCFirms,
      companies: demoCompanies,
      investments: demoInvestments,
    }
  }
}

export default async function HomePage() {
  const { vcs, companies, investments } = await fetchGraphData()

  return <GraphPage vcs={vcs} companies={companies} investments={investments} />
}
