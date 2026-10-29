import { Database, ExternalLink, FlaskConical, RefreshCw } from 'lucide-react'
import { useState } from 'react'
import { Badge } from '@/components/ui/Badge'
import { Button } from '@/components/ui/Button'
import { Card, CardBody, CardHeader } from '@/components/ui/Card'
import { EmptyState, ErrorState, LoadingBlock, Notice } from '@/components/ui/Feedback'
import { CheckboxField, SelectField } from '@/components/ui/FormControls'
import { PageHeader } from '@/components/ui/PageHeader'
import { useAuth } from '@/hooks/auth-context'
import { useToast } from '@/hooks/toast-context'
import { useAsync } from '@/hooks/useAsync'
import { useDocumentTitle } from '@/hooks/useDocumentTitle'
import { api } from '@/services/api'
import type { DatasetStatus, EngineStatus, Evaluation, InspectResult } from '@/types/api'
import { errorMessage } from '@/utils/errors'
import { formatDateTime, formatPercent, LANGUAGE_NAMES, REVIEW_LABELS } from '@/utils/format'

// ---------------------------------------------------------------------------------------------------- engines
function EngineCard({ e }: { e: EngineStatus }) {
  return (
    <li className="rounded-xl border border-line bg-bg p-4">
      <div className="flex flex-wrap items-center gap-2">
        <h3 className="text-sm font-semibold text-ink">{e.label}</h3>
        <Badge tone={e.state === 'ready' ? 'ok' : 'danger'}>{e.state === 'ready' ? 'Ready' : 'Setup required'}</Badge>
        <Badge tone={e.is_ai ? 'warn' : 'accent'}>{e.is_ai ? 'AI model' : 'Not AI'}</Badge>
      </div>
      <p className="mt-2 text-sm text-muted">{e.detail}</p>
      <dl className="mt-3 grid gap-x-6 gap-y-1.5 text-sm sm:grid-cols-2">
        <div>
          <dt className="text-xs text-subtle uppercase">Models</dt>
          <dd className="break-words text-ink">{Object.entries(e.models).map(([k, v]) => `${k}: ${v}`).join(' · ') || '—'}</dd>
        </div>
        <div>
          <dt className="text-xs text-subtle uppercase">Confirmed working</dt>
          <dd className="text-ink">{e.verified ? `Yes, last success ${formatDateTime(e.last_success_at)}` : e.state === 'ready' ? 'Not yet (no request has succeeded since the server started)' : 'No'}</dd>
        </div>
        <div>
          <dt className="text-xs text-subtle uppercase">Last evaluation</dt>
          <dd className="text-ink">{e.last_evaluated_at ? formatDateTime(e.last_evaluated_at) : 'Never evaluated'}</dd>
        </div>
        {e.last_error ? (
          <div>
            <dt className="text-xs text-subtle uppercase">Last error</dt>
            <dd className="text-danger">{e.last_error} <span className="text-subtle">({formatDateTime(e.last_error_at)})</span></dd>
          </div>
        ) : null}
      </dl>
      {e.setup_steps.length > 0 ? (
        <details className="mt-3 text-sm">
          <summary className="cursor-pointer text-accent">How to set this up</summary>
          <ol className="mt-2 list-decimal space-y-1 pl-5 text-muted">{e.setup_steps.map((s) => <li key={s}>{s}</li>)}</ol>
        </details>
      ) : null}
      {e.licence_note ? <p className="mt-3 text-xs text-subtle">Licence note: {e.licence_note}</p> : null}
    </li>
  )
}

// ---------------------------------------------------------------------------------------------------- datasets
function DatasetCard({ d, isAdmin, onInspect, inspecting }: { d: DatasetStatus; isAdmin: boolean; onInspect: () => void; inspecting: boolean }) {
  return (
    <li className="rounded-xl border border-line bg-bg p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <h3 className="text-sm font-semibold text-ink">{d.name}</h3>
            <Badge tone={d.installed ? 'ok' : 'neutral'}>{d.installed ? 'Installed' : 'Not installed'}</Badge>
            <Badge>{d.kind === 'custom' ? 'Synthetic demo' : 'External · restricted access'}</Badge>
          </div>
          <p className="mt-2 max-w-3xl text-sm text-muted">{d.description}</p>
        </div>
        {isAdmin ? (
          <Button size="sm" icon={RefreshCw} onClick={onInspect} loading={inspecting}>
            Inspect{' '}<span className="sr-only">{d.name}</span>
          </Button>
        ) : null}
      </div>
      <dl className="mt-4 grid grid-cols-2 gap-3 text-sm sm:grid-cols-4">
        <div><dt className="text-xs text-subtle uppercase">Files / rows found</dt><dd className="text-xl font-semibold tabular-nums text-ink">{d.files_found ?? '—'}</dd></div>
        <div><dt className="text-xs text-subtle uppercase">Records stored</dt><dd className="text-xl font-semibold tabular-nums text-ink">{d.records}</dd></div>
        <div><dt className="text-xs text-subtle uppercase">Valid</dt><dd className="text-xl font-semibold tabular-nums text-ink">{d.valid_records}</dd></div>
        <div><dt className="text-xs text-subtle uppercase">Last inspected</dt><dd className="text-ink">{d.last_inspected_at ? formatDateTime(d.last_inspected_at) : 'Never'}</dd></div>
      </dl>
      {d.translation_review ? (
        <p className="mt-3 flex flex-wrap items-center gap-2 text-sm text-muted">
          Translation review:
          {Object.entries(d.translation_review).map(([k, n]) => (
            <Badge key={k} tone={k === 'reviewed' ? 'ok' : k === 'unreviewed' ? 'warn' : 'neutral'}>{k}: {n}</Badge>
          ))}
        </p>
      ) : null}
      {d.notes.map((n) => (
        <p key={n} className="mt-2 text-xs text-subtle">{n}</p>
      ))}
      <details className="mt-3 text-sm">
        <summary className="cursor-pointer text-accent">Access, licence and citation</summary>
        <dl className="mt-2 space-y-2 text-muted">
          <div><dt className="text-xs text-subtle uppercase">Where files go</dt><dd className="font-mono text-xs text-ink">{d.expected_path}</dd></div>
          <div><dt className="text-xs text-subtle uppercase">How to get it</dt><dd>{d.access}</dd></div>
          <div><dt className="text-xs text-subtle uppercase">Licence</dt><dd>{d.licence}</dd></div>
          <div><dt className="text-xs text-subtle uppercase">Please cite</dt><dd>{d.citation}</dd></div>
          {d.source_url ? (
            <div>
              <a href={d.source_url} target="_blank" rel="noopener noreferrer" className="inline-link inline-flex items-center gap-1 text-accent hover:text-accent-strong">
                Official source <ExternalLink className="size-3.5" aria-hidden="true" />{' '}<span className="sr-only">(opens in a new tab)</span>
              </a>
            </div>
          ) : null}
        </dl>
      </details>
    </li>
  )
}

function InspectionResult({ r }: { r: InspectResult }) {
  return (
    <div className="rounded-lg border border-line bg-bg p-3 text-sm">
      <p className="font-medium text-ink">
        {r.dataset_key}: {r.installed ? `${r.files_found} files/rows, ${r.valid} valid, ${r.invalid} problem${r.invalid === 1 ? '' : 's'}` : 'nothing installed (0 files)'}
        <span className="ml-2 text-xs font-normal text-subtle">{formatDateTime(r.inspected_at)}</span>
      </p>
      {r.notes.map((n) => <p key={n} className="text-xs text-muted">{n}</p>)}
      {r.problems.length > 0 ? (
        <ul className="mt-2 list-disc space-y-1 pl-5 text-xs text-danger">
          {r.problems.slice(0, 10).map((p) => <li key={p.record}><span className="font-mono">{p.record}</span>: {p.problems.join('; ')}</li>)}
          {r.problems.length > 10 ? <li>… and {r.problems.length - 10} more</li> : null}
        </ul>
      ) : null}
    </div>
  )
}

// ---------------------------------------------------------------------------------------------------- evaluation
function EvaluationView({ run }: { run: Evaluation }) {
  const m = run.metrics
  return (
    <div className="flex flex-col gap-5">
      <dl className="grid grid-cols-2 gap-3 text-sm md:grid-cols-4">
        <div><dt className="text-xs text-subtle uppercase">Run on</dt><dd className="text-ink">{formatDateTime(run.created_at)}</dd></div>
        <div><dt className="text-xs text-subtle uppercase">Examples (n)</dt><dd className="text-xl font-semibold tabular-nums text-ink">{run.n_examples}</dd></div>
        <div><dt className="text-xs text-subtle uppercase">Split</dt><dd className="text-ink">{run.split}{m.selection?.only_reviewed_translations ? ' · reviewed translations only' : ''}</dd></div>
        <div><dt className="text-xs text-subtle uppercase">Data version</dt><dd className="font-mono text-xs text-ink">{run.dataset_version}</dd></div>
        <div className="col-span-2 md:col-span-4"><dt className="text-xs text-subtle uppercase">Parser</dt><dd className="text-ink">{run.target_name} {run.target_version}</dd></div>
      </dl>
      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        {[
          ['Exact match', m.exact_match, 'every attribute of an example correct'],
          ['Micro precision', m.micro_precision, 'of the values it set, how many were right'],
          ['Micro recall', m.micro_recall, 'of the values it should set, how many it found'],
          ['Cross-language agreement', m.cross_language_agreement.agreement, `${m.cross_language_agreement.groups} faces described in several languages`],
        ].map(([label, value, hint]) => (
          <div key={label as string} className="rounded-lg border border-line bg-bg p-3">
            <p className="text-xs text-subtle uppercase">{label as string}</p>
            <p className="text-2xl font-semibold tabular-nums text-ink">{formatPercent(value as number | null)}</p>
            <p className="text-xs text-muted">{hint as string}</p>
          </div>
        ))}
      </div>

      <div className="overflow-x-auto rounded-lg border border-line">
        <table className="w-full min-w-[34rem] text-left text-sm">
          <caption className="sr-only">Results per language</caption>
          <thead className="bg-raised text-xs text-muted uppercase">
            <tr><th scope="col" className="px-3 py-2 font-medium">Language</th><th scope="col" className="px-3 py-2 text-right font-medium">n</th><th scope="col" className="px-3 py-2 text-right font-medium">Exact match</th><th scope="col" className="px-3 py-2 text-right font-medium">Attribute accuracy</th><th scope="col" className="px-3 py-2 font-medium">Word list</th><th scope="col" className="px-3 py-2 text-right font-medium">Human-reviewed rows</th></tr>
          </thead>
          <tbody className="divide-y divide-line">
            {m.by_language.map((l) => (
              <tr key={l.language}>
                <th scope="row" className="px-3 py-2 font-medium text-ink">{LANGUAGE_NAMES[l.language] ?? l.language}</th>
                <td className="px-3 py-2 text-right tabular-nums">{l.n}</td>
                <td className="px-3 py-2 text-right tabular-nums">{formatPercent(l.exact_match)}</td>
                <td className="px-3 py-2 text-right tabular-nums">{formatPercent(l.mean_attribute_accuracy)}</td>
                <td className="px-3 py-2"><Badge tone={l.lexicon_review_status === 'unreviewed' ? 'warn' : 'neutral'}>{REVIEW_LABELS[l.lexicon_review_status] ?? l.lexicon_review_status}</Badge></td>
                <td className="px-3 py-2 text-right tabular-nums">{l.translation_reviewed_n}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <details>
        <summary className="cursor-pointer text-sm text-accent">Per-attribute results</summary>
        <div className="mt-2 overflow-x-auto rounded-lg border border-line">
          <table className="w-full min-w-[34rem] text-left text-sm">
            <caption className="sr-only">Precision and recall for each attribute</caption>
            <thead className="bg-raised text-xs text-muted uppercase">
              <tr><th scope="col" className="px-3 py-2 font-medium">Attribute</th><th scope="col" className="px-3 py-2 text-right font-medium">Labelled</th><th scope="col" className="px-3 py-2 text-right font-medium">Precision</th><th scope="col" className="px-3 py-2 text-right font-medium">Recall</th><th scope="col" className="px-3 py-2 text-right font-medium">Accuracy</th></tr>
            </thead>
            <tbody className="divide-y divide-line">
              {m.per_attribute.map((a) => (
                <tr key={a.attribute}>
                  <th scope="row" className="px-3 py-2 font-medium text-ink">{a.label}</th>
                  <td className="px-3 py-2 text-right tabular-nums">{a.n_gold}</td>
                  <td className="px-3 py-2 text-right tabular-nums">{formatPercent(a.precision)}</td>
                  <td className="px-3 py-2 text-right tabular-nums">{formatPercent(a.recall)}</td>
                  <td className="px-3 py-2 text-right tabular-nums">{formatPercent(a.accuracy)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="mt-2 text-xs text-subtle">“—” means the figure is undefined for this run (for example no value was ever predicted), not zero.</p>
      </details>

      {m.failures_listed.length > 0 ? (
        <details>
          <summary className="cursor-pointer text-sm text-accent">Examples the parser got wrong ({m.failures_listed.length} listed)</summary>
          <ul className="mt-2 space-y-1 text-xs text-muted">
            {m.failures_listed.map((f) => (
              <li key={f.sample_id}><span className="font-mono text-ink">{f.sample_id}</span>: {f.wrong.map((w) => `${w.attribute} expected ${w.expected ?? 'nothing'}, got ${w.got ?? 'nothing'}`).join('; ')}</li>
            ))}
          </ul>
        </details>
      ) : null}

      <Notice tone="warn" title="Read these numbers with care">
        <ul className="list-disc space-y-1 pl-5">{m.caveats.map((c) => <li key={c}>{c}</li>)}</ul>
      </Notice>
    </div>
  )
}

// ---------------------------------------------------------------------------------------------------- page
export function DatasetsPage() {
  useDocumentTitle('Dataset and AI Evaluation')
  const { user } = useAuth()
  const toast = useToast()
  const isAdmin = user?.role === 'admin'
  const engines = useAsync((signal) => api.engines({ signal }), [])
  const datasets = useAsync((signal) => api.datasetsStatus({ signal }), [])
  const evaluations = useAsync((signal) => api.listEvaluations({ signal }), [])
  const [inspecting, setInspecting] = useState<string | 'all' | null>(null)
  const [results, setResults] = useState<InspectResult[]>([])
  const [split, setSplit] = useState<'dev' | 'test' | 'all'>('all')
  const [onlyReviewed, setOnlyReviewed] = useState(false)
  const [running, setRunning] = useState(false)
  const [runError, setRunError] = useState<string | null>(null)

  async function inspect(key?: string) {
    setInspecting(key ?? 'all')
    try {
      const res = await api.inspectDatasets(key)
      setResults(res.results)
      toast.success('Inspection finished.')
      datasets.reload()
    } catch (e) {
      toast.error(errorMessage(e))
    } finally {
      setInspecting(null)
    }
  }

  async function runEvaluation() {
    setRunning(true)
    setRunError(null)
    try {
      await api.runEvaluation({ split, only_reviewed_translations: onlyReviewed })
      toast.success('Evaluation finished and stored.')
      evaluations.reload()
    } catch (e) {
      setRunError(errorMessage(e))
    } finally {
      setRunning(false)
    }
  }

  const latest = evaluations.data?.[0]

  return (
    <>
      <PageHeader
        title="Dataset and AI Evaluation"
        description="What data is installed, which sketch engines can run, and how well the description parser performs. Everything here is counted or computed from real files and real runs; a dataset that is not installed shows zero."
      />
      <div className="flex flex-col gap-6">
        <Card aria-labelledby="engines-title" id="engines">
          <CardHeader id="engines-title" title="Sketch engines" description="Which engines can draw right now. AI engines need credentials on the server; they are never replaced silently by another engine." />
          <CardBody>
            {engines.loading && !engines.data ? <LoadingBlock label="Loading engine status" /> : null}
            {engines.error ? <ErrorState message={errorMessage(engines.error)} onRetry={engines.reload} /> : null}
            {engines.data ? <ul className="grid gap-4 lg:grid-cols-2">{engines.data.map((e) => <EngineCard key={e.engine} e={e} />)}</ul> : null}
            <Notice tone="info" className="mt-4">
              No quantitative evaluation of sketch quality exists for any engine: this project has no benchmark that pairs witness descriptions with ground-truth sketches, and none is claimed.
            </Notice>
          </CardBody>
        </Card>

        <Card aria-labelledby="datasets-title">
          <CardHeader
            id="datasets-title"
            title="Datasets"
            description="The published face-sketch collections (CUFS, CUFSF, UoM-SGFS) are not downloaded by this application. Obtain them under their own terms and place them in the folders shown."
            actions={isAdmin ? <Button size="sm" icon={RefreshCw} onClick={() => inspect()} loading={inspecting === 'all'}>Inspect all datasets</Button> : null}
          />
          <CardBody className="flex flex-col gap-4">
            {!isAdmin ? <Notice tone="info">Only the administrator can run inspections. The figures below come from the last inspection.</Notice> : null}
            {datasets.loading && !datasets.data ? <LoadingBlock label="Loading datasets" /> : null}
            {datasets.error ? <ErrorState message={errorMessage(datasets.error)} onRetry={datasets.reload} /> : null}
            {datasets.data ? (
              <>
                <p className="text-sm text-muted">
                  Total records stored: <strong className="text-ink tabular-nums">{datasets.data.totals.records ?? 0}</strong> · installed datasets:{' '}
                  <strong className="text-ink tabular-nums">{datasets.data.totals.installed_datasets ?? 0}</strong> of {datasets.data.datasets.length}
                </p>
                <ul className="flex flex-col gap-4">
                  {datasets.data.datasets.map((d) => (
                    <DatasetCard key={d.key} d={d} isAdmin={isAdmin} onInspect={() => inspect(d.key)} inspecting={inspecting === d.key} />
                  ))}
                </ul>
              </>
            ) : null}
            {results.length > 0 ? (
              <div className="flex flex-col gap-2" aria-live="polite">
                <h3 className="text-sm font-semibold text-ink">Result of the inspection you just ran</h3>
                {results.map((r) => <InspectionResult key={r.dataset_key} r={r} />)}
              </div>
            ) : null}
          </CardBody>
        </Card>

        <Card aria-labelledby="eval-title">
          <CardHeader
            id="eval-title"
            title="Description-parser evaluation"
            description="Runs the parser on the labelled examples of the custom dataset and compares its output with the labels. n is always shown."
          />
          <CardBody className="flex flex-col gap-6">
            {isAdmin ? (
              <div className="flex flex-wrap items-end gap-4 rounded-lg border border-line bg-bg p-4">
                <div className="w-44">
                  <SelectField label="Split" value={split} onChange={(e) => setSplit(e.target.value as 'dev' | 'test' | 'all')}>
                    <option value="all">All examples</option>
                    <option value="dev">Development split</option>
                    <option value="test">Test split</option>
                  </SelectField>
                </div>
                <CheckboxField label="Only human-reviewed translations" checked={onlyReviewed} onChange={(e) => setOnlyReviewed(e.target.checked)} />
                <Button variant="primary" icon={FlaskConical} onClick={runEvaluation} loading={running}>Run evaluation</Button>
                {runError ? <p role="alert" className="w-full text-sm text-danger">{runError}</p> : null}
              </div>
            ) : (
              <Notice tone="info">Only the administrator can run an evaluation. Stored runs are shown below.</Notice>
            )}

            {evaluations.loading && !evaluations.data ? <LoadingBlock label="Loading evaluations" /> : null}
            {evaluations.error ? <ErrorState message={errorMessage(evaluations.error)} onRetry={evaluations.reload} /> : null}
            {evaluations.data && !latest ? (
              <EmptyState icon={Database} title="No evaluation has been run yet (n = 0)">
                No accuracy numbers are shown because none have been measured. {isAdmin ? 'Press “Run evaluation” to measure the parser on the synthetic demo examples.' : 'Ask the administrator to run one.'}
              </EmptyState>
            ) : null}
            {latest ? <EvaluationView run={latest} /> : null}

            {evaluations.data && evaluations.data.length > 1 ? (
              <details>
                <summary className="cursor-pointer text-sm text-accent">Earlier runs ({evaluations.data.length - 1})</summary>
                <ul className="mt-2 space-y-1 text-sm text-muted">
                  {evaluations.data.slice(1).map((r) => (
                    <li key={r.id}>
                      {formatDateTime(r.created_at)} · split {r.split} · n = {r.n_examples} · exact match {formatPercent(r.metrics.exact_match)} · parser {r.target_version.split(' ')[0]}
                    </li>
                  ))}
                </ul>
              </details>
            ) : null}
          </CardBody>
        </Card>
      </div>
    </>
  )
}
