import { ShieldAlert } from 'lucide-react'
import { useMeta } from '@/hooks/meta-context'

const FALLBACK = 'Preliminary investigative aid - requires human review.'

/** Always-visible reminder. The text comes from the backend so the UI, API and PDF never disagree. */
export function DisclaimerBanner({ compact = false }: { compact?: boolean }) {
  const { meta } = useMeta()
  const preliminary = meta?.disclaimers.preliminary ?? FALLBACK
  return (
    <div role="note" className={`flex items-start gap-3 rounded-lg border border-warn/30 bg-warn/5 text-sm ${compact ? 'px-3 py-2' : 'p-3'}`}>
      <ShieldAlert className="mt-0.5 size-4 shrink-0 text-warn" aria-hidden="true" />
      <p className="text-muted">
        <strong className="font-semibold text-ink">{preliminary}</strong>
        {compact ? null : <> {meta?.disclaimers.no_identification ?? 'This system does not identify people.'}</>}
      </p>
    </div>
  )
}
