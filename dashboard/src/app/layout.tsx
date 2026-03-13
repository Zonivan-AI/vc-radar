import type { Metadata } from 'next'
import './globals.css'
import { Navbar } from '@/components/layout/navbar'
import { Footer } from '@/components/layout/footer'

export const metadata: Metadata = {
  title: 'Meridian — Navigate the AI Investment Landscape',
  description: 'Open-source intelligence platform tracking VC investments, founder profiles, and fund activity across North America\'s AI ecosystem.',
  keywords: ['VC', 'venture capital', 'AI', 'startup', 'founder', 'investment', 'analytics'],
  openGraph: {
    title: 'Meridian — Navigate the AI Investment Landscape',
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
        <Navbar />
        <main className="flex-1">
          {children}
        </main>
        <Footer />
      </body>
    </html>
  )
}
