import { Search } from 'lucide-react'
import { useState } from 'react'
import { useActiveCase } from '@/hooks/active-case-context'
import { useAsync } from '@/hooks/useAsync'
import { useDebouncedValue } from '@/hooks/useDebouncedValue'
import { api } from '@/services/api'
import { errorMessage } from '@/utils/errors'
import { formatDate } from '@/utils/format'
import { StatusBadge } from './StatusBadge'
import { Button } from './ui/Button'
import { EmptyState, ErrorState, LoadingBlock } from './ui/Feedback'
import { TextField } from './ui/FormControls'

/** Pick the case to work on. The choice is remembered across pages. */
export function CaseChooser({ onSelected }: { onSelected?: (caseId: string) => void }) {
  const { selectCase, activeCaseId } = useActiveCase()
  const [query, setQuery] = useState('')
  const q = useDebouncedValue(query)
  const { data, error, loading, reload } = useAsync((signal) => api.listCases({ q, page_size: 8, sort: 'updated_desc' }, { signal }), [q])

  return (
    <div className="flex flex-col gap-4">
      <TextField label="Search your cases" placeholder="Case ID, title, name or reference" value={query} onChange={(e) => setQuery(e.target.value)} type="search" />
      {loading && !data ? <LoadingBlock label="Loading cases" /> : null}
      {error ? <ErrorState message={errorMessage(error)} onRetry={reload} /> : null}
      {data && data.items.length === 0 ? (
        <EmptyState icon={Search} title={q ? 'No case matches your search' : 'You have no cases yet'}>
          {q ? 'Try a different word, or clear the search box.' : 'Open a new investigation to create your first case.'}
        </EmptyState>
      ) : null}
      {data && data.items.length > 0 ? (
        <ul className="divide-y divide-line rounded-lg border border-line">
          {data.items.map((c) => (
            <li key={c.case_id} className="flex flex-wrap items-center justify-between gap-3 px-4 py-3">
              <div className="min-w-0">
                <p className="truncate font-medium text-ink">{c.title}</p>
                <p className="text-xs text-subtle">
                  <span className="font-mono">{c.case_id}</span> · incident {formatDate(c.incident_date)} · {c.sketch_count} sketch version{c.sketch_count === 1 ? '' : 's'}
                </p>
                <p className="text-xs text-subtle">
                  Investigator {c.investigator_name || 'not recorded'} · witness {c.witness_name || 'not recorded'}
                </p>
              </div>
              <div className="flex items-center gap-3">
                <StatusBadge status={c.status} />
                <Button
                  size="sm"
                  variant={c.case_id === activeCaseId ? 'secondary' : 'primary'}
                  onClick={() => {
                    selectCase(c.case_id)
                    onSelected?.(c.case_id)
                  }}
                >
                  {c.case_id === activeCaseId ? 'Selected' : 'Select'}
                  {' '}<span className="sr-only">{c.title}</span>
                </Button>
              </div>
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  )
}
