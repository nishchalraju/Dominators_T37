import type { CaseSummary } from '@/types/api'

type People = Pick<CaseSummary, 'investigator_name' | 'witness_name'>

/** Who is investigating and who the witness is. A blank name (a case from before names existed) says so. */
export function CasePeople({ people, className = '' }: { people: People; className?: string }) {
  return (
    <dl className={`flex flex-wrap gap-x-6 gap-y-1 text-sm ${className}`}>
      <Person label="Investigator" name={people.investigator_name} />
      <Person label="Witness" name={people.witness_name} />
    </dl>
  )
}

function Person({ label, name }: { label: string; name: string }) {
  return (
    <div className="flex min-w-0 items-baseline gap-1.5">
      <dt className="text-subtle">{label}:</dt>
      <dd className="min-w-0 truncate text-ink" title={name || undefined}>
        {name || <span className="text-muted">not recorded</span>}
      </dd>
    </div>
  )
}
