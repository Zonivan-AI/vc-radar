import { Navbar } from '@/components/layout/navbar'

export default function GraphLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <>
      <Navbar variant="transparent" />
      <main className="flex-1 relative">
        {children}
      </main>
    </>
  )
}
