import { FilePlus2, FolderOpen, PencilRuler } from 'lucide-react'
import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { StatusBadge } from '@/components/StatusBadge'
import { Button } from '@/components/ui/Button'
import { Card, CardBody, CardHeader } from '@/components/ui/Card'
import { EmptyState, ErrorState, LoadingBlock, Notice } from '@/components/ui/Feedback'
import { SelectField, TextField } from '@/components/ui/FormControls'
import { PageHeader } from '@/components/ui/PageHeader'
import { useActiveCase } from '@/hooks/active-case-context'
import { useAuth } from '@/hooks/auth-context'
import { useAsync } from '@/hooks/useAsync'
import { useDebouncedValue } from '@/hooks/useDebouncedValue'
import { useDocumentTitle } from '@/hooks/useDocumentTitle'
import { api } from '@/services/api'
import type { CaseStatus } from '@/types/api'
import { errorMessage } from '@/utils/errors'
import { formatDate, formatDateTime, STATUS_LABELS } from '@/utils/format'

function StatCard({ label, value, hint }: { label: string; value: number; hint?: string }) {
  return (
    <div className="rounded-xl border border-line bg-surface p-4">
      <p className="text-xs tracking-wide text-subtle uppercase">{label}</p>
      <p className="mt-1 text-3xl font-semibold text-ink tabular-nums">{value}</p>
      {hint ? <p className="mt-1 text-xs text-muted">{hint}</p> : null}
    </div>
  )
}

export function DashboardPage() {
  useDocumentTitle('Dashboard')
  const { user } = useAuth()
  const navigate = useNavigate()
  const { selectCase } = useActiveCase()
  const stats = useAsync((signal) => api.dashboard({ signal }), [])
  const engines = useAsync((signal) => api.engines({ signal }), [])

  const [query, setQuery] = useState('')
  const q = useDebouncedValue(query)
  const [status, setStatus] = useState<CaseStatus | ''>('')
  const [page, setPage] = useState(1)
  const cases = useAsync((signal) => api.listCases({ q, status, page, page_size: 8, sort: 'updated_desc' }, { signal }), [q, status, page])

  const s = stats.data
  const aiReady = (engines.data ?? []).some((e) => e.is_ai && e.available)
  const totalPages = cases.data ? Math.max(1, Math.ceil(cases.data.total / cases.data.page_size)) : 1

  return (
    <>
      <PageHeader
        title="Dashboard"
        description={`Welcome, ${user?.display_name ?? user?.username}. Every number below is counted from the database${s?.scope === 'all' ? ' (all investigators)' : ' for your own cases'}.`}
        actions={
          <Link to="/investigations/new" className="inline-flex h-10 items-center gap-2 rounded-lg bg-accent px-4 text-sm font-semibold text-accent-ink hover:bg-accent-strong">
            <FilePlus2 className="size-4" aria-hidden="true" /> New investigation
          </Link>
        }
      />

      {engines.data && !aiReady ? (
        <Notice tone="info" title="AI engines are not set up" className="mb-6">
          Only the schematic engine (rule-based, not AI) can draw sketches right now. Setup steps are on the{' '}
          <Link to="/datasets" className="inline-link text-accent hover:text-accent-strong">Dataset and AI Evaluation</Link> page.
        </Notice>
      ) : null}

      {stats.loading && !s ? <LoadingBlock label="Loading statistics" /> : null}
      {stats.error ? <ErrorState message={errorMessage(stats.error)} onRetry={stats.reload} title="Could not load the statistics" /> : null}
      {s ? (
        <section aria-label="Statistics" className="mb-8 grid grid-cols-2 gap-4 md:grid-cols-4">
          <StatCard label="Cases" value={s.total_cases} hint={`${s.cases_with_selected_sketch} with a selected sketch`} />
          <StatCard label={STATUS_LABELS.in_progress} value={s.status_counts.in_progress} />
          <StatCard label={STATUS_LABELS.under_review} value={s.status_counts.under_review} />
          <StatCard label={STATUS_LABELS.closed} value={s.status_counts.closed} />
          <StatCard label="Sketch versions" value={s.sketch_versions} hint={`${s.schematic_versions} schematic (not AI) · ${s.ai_versions} AI-generated`} />
          <StatCard label="Witness descriptions" value={s.witness_descriptions} />
          <StatCard label="Investigator notes" value={s.notes} />
        </section>
      ) : null}

      <div className="grid gap-6 xl:grid-cols-[1fr_22rem]">
        <Card aria-labelledby="cases-title">
          <CardHeader id="cases-title" title="Cases" description="Search by case ID, title, investigator or witness name, or your reference number." />
          <CardBody className="flex flex-col gap-4">
            <div className="grid gap-3 sm:grid-cols-[1fr_12rem]">
              <TextField label="Search" type="search" placeholder="e.g. SA-2026 or market" value={query} onChange={(e) => { setQuery(e.target.value); setPage(1) }} />
              <SelectField label="Status" value={status} onChange={(e) => { setStatus(e.target.value as CaseStatus | ''); setPage(1) }}>
                <option value="">All statuses</option>
                {(Object.keys(STATUS_LABELS) as CaseStatus[]).map((k) => (
                  <option key={k} value={k}>{STATUS_LABELS[k]}</option>
                ))}
              </SelectField>
            </div>
            {cases.loading && !cases.data ? <LoadingBlock label="Loading cases" /> : null}
            {cases.error ? <ErrorState message={errorMessage(cases.error)} onRetry={cases.reload} /> : null}
            {cases.data && cases.data.items.length === 0 ? (
              q || status ? (
                <EmptyState icon={FolderOpen} title="No case matches these filters">Clear the search box or choose “All statuses”.</EmptyState>
              ) : (
                <EmptyState icon={FolderOpen} title="No cases yet" action={<Link to="/investigations/new" className="rounded-lg bg-accent px-4 py-2 text-sm font-semibold text-accent-ink">Open the first investigation</Link>}>
                  Cases you create appear here.
                </EmptyState>
              )
            ) : null}
            {cases.data && cases.data.items.length > 0 ? (
              <>
                <div className="overflow-x-auto rounded-lg border border-line">
                  <table className="w-full min-w-[54rem] text-left text-sm">
                    <caption className="sr-only">Cases, most recently updated first</caption>
                    <thead className="bg-raised text-xs text-muted uppercase">
                      <tr>
                        <th scope="col" className="px-3 py-2 font-medium">Case ID</th>
                        <th scope="col" className="px-3 py-2 font-medium">Title</th>
                        <th scope="col" className="px-3 py-2 font-medium">Incident</th>
                        <th scope="col" className="px-3 py-2 font-medium">Investigator</th>
                        <th scope="col" className="px-3 py-2 font-medium">Witness</th>
                        <th scope="col" className="px-3 py-2 font-medium">Status</th>
                        <th scope="col" className="px-3 py-2 text-right font-medium">Sketches</th>
                        <th scope="col" className="px-3 py-2 font-medium"><span className="sr-only">Actions</span></th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-line">
                      {cases.data.items.map((c) => (
                        <tr key={c.case_id} className="hover:bg-raised/60">
                          <td className="px-3 py-2 font-mono text-xs text-accent">{c.case_id}</td>
                          <td className="max-w-[16rem] truncate px-3 py-2 text-ink">
                            <Link to={`/cases/${c.case_id}`} onClick={() => selectCase(c.case_id)} className="hover:underline">{c.title}</Link>
                          </td>
                          <td className="px-3 py-2 whitespace-nowrap text-muted">{formatDate(c.incident_date)}</td>
                          <td className="max-w-[9rem] truncate px-3 py-2 text-ink" title={c.investigator_name || undefined}>{c.investigator_name || <span className="text-muted">Not recorded</span>}</td>
                          <td className="max-w-[9rem] truncate px-3 py-2 text-ink" title={c.witness_name || undefined}>{c.witness_name || <span className="text-muted">Not recorded</span>}</td>
                          <td className="px-3 py-2"><StatusBadge status={c.status} /></td>
                          <td className="px-3 py-2 text-right tabular-nums text-muted">{c.sketch_count}</td>
                          <td className="px-3 py-2 text-right">
                            <Button size="sm" icon={PencilRuler} onClick={() => { selectCase(c.case_id); navigate('/workspace') }}>
                              Workspace{' '}<span className="sr-only">for {c.title}</span>
                            </Button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                <div className="flex flex-wrap items-center justify-between gap-3 text-sm text-muted">
                  <span>{cases.data.total} case{cases.data.total === 1 ? '' : 's'} · page {cases.data.page} of {totalPages}</span>
                  <div className="flex gap-2">
                    <Button size="sm" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>Previous</Button>
                    <Button size="sm" disabled={page >= totalPages} onClick={() => setPage((p) => p + 1)}>Next</Button>
                  </div>
                </div>
              </>
            ) : null}
          </CardBody>
        </Card>

        <Card aria-labelledby="activity-title">
          <CardHeader id="activity-title" title="Recent activity" description="From the audit log." />
          <CardBody>
            {s && s.recent_activity.length === 0 ? <p className="text-sm text-muted">Nothing has happened yet.</p> : null}
            {s && s.recent_activity.length > 0 ? (
              <ol className="flex flex-col gap-3">
                {s.recent_activity.map((a) => (
                  <li key={a.id} className="border-l-2 border-line-strong pl-3 text-sm">
                    <p className="text-ink">{a.summary}</p>
                    <p className="text-xs text-subtle">
                      <time dateTime={a.created_at}>{formatDateTime(a.created_at)}</time>
                      {s.scope === 'all' && a.username ? ` · ${a.username}` : ''}
                    </p>
                  </li>
                ))}
              </ol>
            ) : null}
            {stats.loading && !s ? <LoadingBlock label="Loading activity" /> : null}
          </CardBody>
        </Card>
      </div>
    </>
  )
}
