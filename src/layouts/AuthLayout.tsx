import { PencilRuler } from 'lucide-react'
import type { ReactNode } from 'react'
import { DisclaimerBanner } from '@/components/DisclaimerBanner'

export function AuthLayout({ title, subtitle, children }: { title: string; subtitle: string; children: ReactNode }) {
  return (
    <div className="mx-auto flex min-h-screen w-full max-w-xl flex-col justify-center gap-6 px-4 py-10">
      <div className="flex items-center gap-3">
        <span className="grid size-11 place-items-center rounded-xl border border-accent/40 bg-accent/10 text-accent">
          <PencilRuler className="size-5" aria-hidden="true" />
        </span>
        <div>
          <p className="text-lg font-semibold text-ink">SketchAssist AI</p>
          <p className="text-sm text-muted">Multilingual forensic sketch assistance · version 3.0</p>
        </div>
      </div>
      <main id="main" className="rounded-xl border border-line bg-surface p-6 shadow-xl">
        <h1 className="text-xl font-semibold text-ink">{title}</h1>
        <p className="mt-1 mb-5 text-sm text-muted">{subtitle}</p>
        {children}
      </main>
      <DisclaimerBanner />
    </div>
  )
}
