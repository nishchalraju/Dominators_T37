import { ArrowRight } from 'lucide-react'
import { useMeta } from '@/hooks/meta-context'
import type { RevisionDetails } from '@/types/api'

/** What a revision really did: attribute changes applied, parts of the instruction that were NOT applied, and notes. */
export function RevisionResult({ details }: { details: RevisionDetails }) {
  const { valueLabel } = useMeta()
  return (
    <div className="flex flex-col gap-3 text-sm">
      {details.changes.length > 0 ? (
        <div>
          <p className="mb-1 font-medium text-ink">Applied</p>
          <ul className="flex flex-col gap-1">
            {details.changes.map((c) => (
              <li key={c.attribute} className="flex flex-wrap items-center gap-x-2 text-muted">
                <strong className="text-ink">{c.label}:</strong>
                <span>{valueLabel(c.attribute, c.before)}</span>
                <ArrowRight className="size-3.5 text-accent" aria-label="changed to" />
                <span className="text-accent">{valueLabel(c.attribute, c.after)}</span>
                <span className="witness-text text-xs text-subtle">from “{c.evidence}”</span>
                {c.note ? <span className="w-full text-xs text-warn">{c.note}</span> : null}
              </li>
            ))}
          </ul>
        </div>
      ) : (
        <p className="text-muted">No structured attribute changed.</p>
      )}
      {details.ignored.length > 0 ? (
        <div>
          <p className="mb-1 font-medium text-ink">Not applied</p>
          <ul className="flex flex-col gap-1">
            {details.ignored.map((i) => (
              <li key={i.text} className="text-muted">
                <span className="witness-text text-ink">“{i.text}”</span> — {i.reason}
              </li>
            ))}
          </ul>
        </div>
      ) : null}
      {details.notes.length > 0 ? (
        <ul className="list-disc space-y-1 pl-5 text-muted">
          {details.notes.map((n) => <li key={n}>{n}</li>)}
        </ul>
      ) : null}
    </div>
  )
}
