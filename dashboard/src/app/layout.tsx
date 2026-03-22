import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: 'VC Radar — Navigate the AI Investment Landscape',
  description: 'Open-source intelligence platform tracking VC investments, founder profiles, and fund activity across North America\'s AI ecosystem.',
  keywords: ['VC', 'venture capital', 'AI', 'startup', 'founder', 'investment', 'analytics'],
  openGraph: {
    title: 'VC Radar — Navigate the AI Investment Landscape',
    description: 'Open-source VC intelligence for founders, researchers, and operators.',
    type: 'website',
  },
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en" className="dark">
      <body className="min-h-screen flex flex-col">
        {children}
      </body>
    </html>
  )
}
