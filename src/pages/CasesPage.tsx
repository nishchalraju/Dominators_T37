import { FilePlus2, FolderOpen, PencilRuler } from 'lucide-react'
import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { StatusBadge } from '@/components/StatusBadge'
import { Button } from '@/components/ui/Button'
import { Card, CardBody } from '@/components/ui/Card'
import { EmptyState, ErrorState, LoadingBlock } from '@/components/ui/Feedback'
import { SelectField, TextField } from '@/components/ui/FormControls'
import { PageHeader } from '@/components/ui/PageHeader'
import { useActiveCase } from '@/hooks/active-case-context'
import { useAsync } from '@/hooks/useAsync'
import { useDebouncedValue } from '@/hooks/useDebouncedValue'
import { useDocumentTitle } from '@/hooks/useDocumentTitle'
import { api } from '@/services/api'
import type { CaseQuery, CaseStatus } from '@/types/api'
import { errorMessage } from '@/utils/errors'
import { formatDate, formatDateTime, STATUS_LABELS } from '@/utils/format'

export function CasesPage() {
  useDocumentTitle('Case Management')
  const navigate = useNavigate()
  const { activeCaseId, selectCase } = useActiveCase()
  const [query, setQuery] = useState('')
  const q = useDebouncedValue(query)
  const [status, setStatus] = useState<CaseStatus | ''>('')
  const [sort, setSort] = useState<NonNullable<CaseQuery['sort']>>('updated_desc')
  const [page, setPage] = useState(1)
  const { data, error, loading, reload } = useAsync((signal) => api.listCases({ q, status, sort, page, page_size: 15 }, { signal }), [q, status, sort, page])
  const totalPages = data ? Math.max(1, Math.ceil(data.total / data.page_size)) : 1

  return (
    <>
      <PageHeader
        title="Case Management"
        description="Open, search and manage your cases. The case you select stays selected on the Sketch Workspace and Reports pages."
        actions={
          <Link to="/investigations/new" className="inline-flex h-10 items-center gap-2 rounded-lg bg-accent px-4 text-sm font-semibold text-accent-ink hover:bg-accent-strong">
            <FilePlus2 className="size-4" aria-hidden="true" /> New investigation
          </Link>
        }
      />
      <Card>
        <CardBody className="flex flex-col gap-4">
          <div className="grid gap-3 md:grid-cols-[1fr_12rem_13rem]">
            <TextField label="Search" type="search" value={query} onChange={(e) => { setQuery(e.target.value); setPage(1) }} placeholder="Case ID, title, name or reference" />
            <SelectField label="Status" value={status} onChange={(e) => { setStatus(e.target.value as CaseStatus | ''); setPage(1) }}>
              <option value="">All statuses</option>
              {(Object.keys(STATUS_LABELS) as CaseStatus[]).map((k) => (
                <option key={k} value={k}>{STATUS_LABELS[k]}</option>
              ))}
            </SelectField>
            <SelectField label="Sort by" value={sort} onChange={(e) => { setSort(e.target.value as NonNullable<CaseQuery['sort']>); setPage(1) }}>
              <option value="updated_desc">Recently updated</option>
              <option value="created_desc">Newest first</option>
              <option value="incident_desc">Incident date</option>
              <option value="title_asc">Title A to Z</option>
            </SelectField>
          </div>

          {loading && !data ? <LoadingBlock label="Loading cases" /> : null}
          {error ? <ErrorState message={errorMessage(error)} onRetry={reload} title="Could not load the cases" /> : null}
          {data && data.items.length === 0 ? (
            <EmptyState icon={FolderOpen} title={q || status ? 'No case matches these filters' : 'No cases yet'}>
              {q || status ? 'Clear the filters to see all your cases.' : 'Start with a new investigation.'}
            </EmptyState>
          ) : null}

          {data && data.items.length > 0 ? (
            <>
              <div className="overflow-x-auto rounded-lg border border-line">
                <table className="w-full min-w-[66rem] text-left text-sm">
                  <caption className="sr-only">Your cases</caption>
                  <thead className="bg-raised text-xs text-muted uppercase">
                    <tr>
                      <th scope="col" className="px-3 py-2 font-medium">Case</th>
                      <th scope="col" className="px-3 py-2 font-medium">Incident</th>
                      <th scope="col" className="px-3 py-2 font-medium">Investigator</th>
                      <th scope="col" className="px-3 py-2 font-medium">Witness</th>
                      <th scope="col" className="px-3 py-2 font-medium">Status</th>
                      <th scope="col" className="px-3 py-2 text-right font-medium">Descriptions</th>
                      <th scope="col" className="px-3 py-2 text-right font-medium">Sketch versions</th>
                      <th scope="col" className="px-3 py-2 font-medium">Updated</th>
                      <th scope="col" className="px-3 py-2 font-medium"><span className="sr-only">Actions</span></th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-line">
                    {data.items.map((c) => (
                      <tr key={c.case_id} className={c.case_id === activeCaseId ? 'bg-accent/5' : 'hover:bg-raised/60'}>
                        <th scope="row" className="max-w-[18rem] px-3 py-2 font-normal">
                          <Link to={`/cases/${c.case_id}`} className="block truncate font-medium text-ink hover:underline">{c.title}</Link>
                          <span className="font-mono text-xs text-accent">{c.case_id}</span>
                          <span className="text-xs text-subtle"> · ref {c.investigator_ref}</span>
                        </th>
                        <td className="px-3 py-2 whitespace-nowrap text-muted">{formatDate(c.incident_date)}</td>
                        <td className="max-w-[11rem] truncate px-3 py-2 text-ink" title={c.investigator_name || undefined}>{c.investigator_name || <span className="text-muted">Not recorded</span>}</td>
                        <td className="max-w-[11rem] truncate px-3 py-2 text-ink" title={c.witness_name || undefined}>{c.witness_name || <span className="text-muted">Not recorded</span>}</td>
                        <td className="px-3 py-2"><StatusBadge status={c.status} /></td>
                        <td className="px-3 py-2 text-right tabular-nums text-muted">{c.description_count}</td>
                        <td className="px-3 py-2 text-right tabular-nums text-muted">{c.sketch_count}</td>
                        <td className="px-3 py-2 text-xs whitespace-nowrap text-subtle">{formatDateTime(c.updated_at)}</td>
                        <td className="px-3 py-2">
                          <div className="flex justify-end gap-2">
                            <Button size="sm" variant={c.case_id === activeCaseId ? 'ghost' : 'secondary'} disabled={c.case_id === activeCaseId} onClick={() => selectCase(c.case_id)}>
                              {c.case_id === activeCaseId ? 'Selected' : 'Select'}
                              {' '}<span className="sr-only">{c.title}</span>
                            </Button>
                            <Button size="sm" icon={PencilRuler} onClick={() => { selectCase(c.case_id); navigate('/workspace') }}>
                              Workspace{' '}<span className="sr-only">for {c.title}</span>
                            </Button>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <div className="flex flex-wrap items-center justify-between gap-3 text-sm text-muted">
                <span>{data.total} case{data.total === 1 ? '' : 's'} · page {data.page} of {totalPages}</span>
                <div className="flex gap-2">
                  <Button size="sm" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>Previous</Button>
                  <Button size="sm" disabled={page >= totalPages} onClick={() => setPage((p) => p + 1)}>Next</Button>
                </div>
              </div>
            </>
          ) : null}
        </CardBody>
      </Card>
    </>
  )
}
