import { Archive, FileText, Pencil, PencilRuler, RotateCcw, Trash2 } from 'lucide-react'
import { useState, type FormEvent } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { NotesPanel } from '@/components/NotesPanel'
import { StatusBadge } from '@/components/StatusBadge'
import { Button } from '@/components/ui/Button'
import { Card, CardBody, CardHeader } from '@/components/ui/Card'
import { EmptyState, ErrorState, LoadingBlock, Notice } from '@/components/ui/Feedback'
import { TextAreaField, TextField } from '@/components/ui/FormControls'
import { ConfirmDialog, Modal } from '@/components/ui/Modal'
import { Badge } from '@/components/ui/Badge'
import { useActiveCase } from '@/hooks/active-case-context'
import { useMeta } from '@/hooks/meta-context'
import { useToast } from '@/hooks/toast-context'
import { useAsync } from '@/hooks/useAsync'
import { useDocumentTitle } from '@/hooks/useDocumentTitle'
import { api } from '@/services/api'
import type { CaseDetail, CaseStatus } from '@/types/api'
import { ApiError, errorMessage, fieldErrors } from '@/utils/errors'
import { formatDate, formatDateTime, LANGUAGE_NAMES, todayIso } from '@/utils/format'

function EditCaseModal({ detail, open, onClose, onSaved }: { detail: CaseDetail; open: boolean; onClose: () => void; onSaved: () => void }) {
  const toast = useToast()
  const [form, setForm] = useState({
    title: detail.title,
    incident_date: detail.incident_date,
    investigator_ref: detail.investigator_ref,
    investigator_name: detail.investigator_name,
    witness_name: detail.witness_name,
    incident_description: detail.incident_description,
  })
  const [errors, setErrors] = useState<Record<string, string>>({})
  const [formError, setFormError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const set = (key: keyof typeof form) => (e: { target: { value: string } }) => setForm((f) => ({ ...f, [key]: e.target.value }))

  async function submit(event: FormEvent) {
    event.preventDefault()
    setBusy(true)
    setErrors({})
    setFormError(null)
    try {
      // A case from before names were recorded may still have them empty; leaving them empty must not block other edits.
      const { investigator_name, witness_name, ...rest } = form
      await api.updateCase(detail.case_id, {
        ...rest,
        ...(investigator_name.trim() ? { investigator_name: investigator_name.trim() } : {}),
        ...(witness_name.trim() ? { witness_name: witness_name.trim() } : {}),
      })
      toast.success('Case details saved.')
      onSaved()
      onClose()
    } catch (e) {
      const fields = fieldErrors(e)
      if (Object.keys(fields).length) setErrors(fields)
      else setFormError(errorMessage(e))
    } finally {
      setBusy(false)
    }
  }

  return (
    <Modal open={open} title="Edit case details" onClose={onClose} wide>
      <form id="edit-case" onSubmit={submit} className="grid gap-4" noValidate>
        {formError ? <Notice tone="danger">{formError}</Notice> : null}
        <TextField label="Case title" required value={form.title} onChange={set('title')} error={errors.title} maxLength={200} data-autofocus />
        <div className="grid gap-4 sm:grid-cols-2">
          <TextField label="Incident date" type="date" required max={todayIso()} value={form.incident_date} onChange={set('incident_date')} error={errors.incident_date} />
          <TextField label="Investigator reference" required value={form.investigator_ref} onChange={set('investigator_ref')} error={errors.investigator_ref} maxLength={64} />
        </div>
        <div className="grid gap-4 sm:grid-cols-2">
          <TextField label="Investigator name" required={!!detail.investigator_name} value={form.investigator_name} onChange={set('investigator_name')} error={errors.investigator_name} maxLength={120} autoComplete="off" hint={detail.investigator_name ? undefined : 'Not recorded yet. Add it so it appears in the report.'} />
          <TextField label="Witness name" required={!!detail.witness_name} value={form.witness_name} onChange={set('witness_name')} error={errors.witness_name} maxLength={120} autoComplete="off" hint={detail.witness_name ? 'Use a code such as W-01 if the name must be withheld.' : 'Not recorded yet. Add it so it appears in the report.'} />
        </div>
        <TextAreaField label="Incident description" value={form.incident_description} onChange={set('incident_description')} error={errors.incident_description} maxLength={5000} />
        <div className="flex justify-end gap-2">
          <Button onClick={onClose}>Cancel</Button>
          <Button type="submit" variant="primary" loading={busy}>Save changes</Button>
        </div>
      </form>
    </Modal>
  )
}

export function CaseDetailPage() {
  const { caseId = '' } = useParams()
  const navigate = useNavigate()
  const toast = useToast()
  const { activeCaseId, selectCase, clearCase, refresh } = useActiveCase()
  const { attributeLabel, valueLabel } = useMeta()
  const { data: detail, error, loading, reload } = useAsync((signal) => api.getCase(caseId, { signal }), [caseId])
  const descriptions = useAsync((signal) => api.listDescriptions(caseId, { signal }), [caseId])
  const versions = useAsync((signal) => api.listVersions(caseId, { signal }), [caseId])
  const [editing, setEditing] = useState(false)
  const [deleting, setDeleting] = useState(false)
  const [busy, setBusy] = useState<string | null>(null)
  useDocumentTitle(detail ? detail.title : 'Case')

  async function setStatus(status: CaseStatus, message: string) {
    setBusy(status)
    try {
      await api.updateCase(caseId, { status })
      toast.success(message)
      reload()
      refresh()
    } catch (e) {
      toast.error(errorMessage(e))
    } finally {
      setBusy(null)
    }
  }

  async function remove() {
    setBusy('delete')
    try {
      await api.deleteCase(caseId)
      if (activeCaseId === caseId) clearCase()
      toast.success(`Case ${caseId} was deleted.`)
      navigate('/cases', { replace: true })
    } catch (e) {
      toast.error(errorMessage(e))
      setBusy(null)
      setDeleting(false)
    }
  }

  if (loading && !detail) return <LoadingBlock label="Loading the case" />
  if (error || !detail) {
    const notFound = error instanceof ApiError && error.status === 404
    return (
      <ErrorState
        title={notFound ? 'Case not found' : 'Could not load the case'}
        message={notFound ? 'This case does not exist, or it belongs to another investigator.' : errorMessage(error)}
        onRetry={notFound ? undefined : reload}
      />
    )
  }
  const closed = detail.status === 'closed'

  return (
    <>
      <div className="mb-6 flex flex-wrap items-start justify-between gap-4">
        <div className="min-w-0">
          <p className="mb-1 text-sm">
            <Link to="/cases" className="inline-link text-muted hover:text-ink">Case Management</Link> <span className="text-subtle">/</span>{' '}
            <span className="font-mono text-accent">{detail.case_id}</span>
          </p>
          <h1 className="text-2xl font-semibold tracking-tight text-ink">{detail.title}</h1>
          <div className="mt-2 flex flex-wrap items-center gap-2">
            <StatusBadge status={detail.status} />
            {activeCaseId === detail.case_id ? <Badge tone="accent">Active case</Badge> : null}
          </div>
        </div>
        <div className="flex flex-wrap gap-2">
          {activeCaseId !== detail.case_id ? <Button onClick={() => selectCase(detail.case_id)}>Set as active case</Button> : null}
          <Button icon={PencilRuler} onClick={() => { selectCase(detail.case_id); navigate('/workspace') }}>Open workspace</Button>
          <Button icon={FileText} onClick={() => { selectCase(detail.case_id); navigate('/reports') }}>Report</Button>
        </div>
      </div>

      {closed ? (
        <Notice tone="info" title="This case is closed" className="mb-6">
          It is read-only: descriptions, sketches and notes cannot be added. Reopen it to continue the investigation.
        </Notice>
      ) : null}

      <div className="grid gap-6 xl:grid-cols-[1fr_26rem]">
        <div className="flex flex-col gap-6">
          <Card aria-labelledby="overview-title">
            <CardHeader
              id="overview-title"
              title="Details"
              actions={
                <>
                  <Button size="sm" icon={Pencil} onClick={() => setEditing(true)} disabled={closed}>Edit</Button>
                  <Button size="sm" variant="danger" icon={Trash2} onClick={() => setDeleting(true)}>Delete</Button>
                </>
              }
            />
            <CardBody>
              {!closed && (!detail.investigator_name || !detail.witness_name) ? (
                <Notice tone="info" className="mb-4">
                  The {[!detail.investigator_name && 'investigator', !detail.witness_name && 'witness'].filter(Boolean).join(' and ')} name
                  {!detail.investigator_name && !detail.witness_name ? 's were' : ' was'} not recorded for this case. Use Edit to add {!detail.investigator_name && !detail.witness_name ? 'them' : 'it'}; they appear in the report.
                </Notice>
              ) : null}
              <dl className="grid gap-x-8 gap-y-3 text-sm sm:grid-cols-2">
                <div><dt className="text-xs text-subtle uppercase">Case ID</dt><dd className="font-mono text-ink">{detail.case_id}</dd></div>
                <div><dt className="text-xs text-subtle uppercase">Investigator name</dt><dd className="text-ink">{detail.investigator_name || <span className="text-muted">Not recorded</span>}</dd></div>
                <div><dt className="text-xs text-subtle uppercase">Witness name</dt><dd className="text-ink">{detail.witness_name || <span className="text-muted">Not recorded</span>}</dd></div>
                <div><dt className="text-xs text-subtle uppercase">Investigator reference</dt><dd className="text-ink">{detail.investigator_ref}</dd></div>
                <div><dt className="text-xs text-subtle uppercase">Incident date</dt><dd className="text-ink">{formatDate(detail.incident_date)}</dd></div>
                <div><dt className="text-xs text-subtle uppercase">Account that owns the case</dt><dd className="text-ink">{detail.owner_username ?? '—'}</dd></div>
                <div><dt className="text-xs text-subtle uppercase">Created</dt><dd className="text-ink">{formatDateTime(detail.created_at)}</dd></div>
                <div><dt className="text-xs text-subtle uppercase">Last updated</dt><dd className="text-ink">{formatDateTime(detail.updated_at)}</dd></div>
                <div className="sm:col-span-2">
                  <dt className="text-xs text-subtle uppercase">Incident description</dt>
                  <dd className="witness-text whitespace-pre-wrap text-ink">{detail.incident_description || <span className="text-muted">None entered.</span>}</dd>
                </div>
              </dl>
              <div className="mt-5 flex flex-wrap gap-2 border-t border-line pt-4">
                <span className="mr-2 self-center text-sm text-muted">Status:</span>
                {closed ? (
                  <Button icon={RotateCcw} variant="primary" loading={busy === 'in_progress'} onClick={() => setStatus('in_progress', 'Case reopened.')}>Reopen case</Button>
                ) : (
                  <>
                    {detail.status !== 'in_progress' ? <Button loading={busy === 'in_progress'} onClick={() => setStatus('in_progress', 'Case moved back to in progress.')}>Back to in progress</Button> : null}
                    {detail.status !== 'under_review' ? <Button loading={busy === 'under_review'} onClick={() => setStatus('under_review', 'Case moved to review.')}>Move to review</Button> : null}
                    <Button icon={Archive} loading={busy === 'closed'} onClick={() => setStatus('closed', 'Case closed.')}>Close case</Button>
                  </>
                )}
              </div>
            </CardBody>
          </Card>

          <Card aria-labelledby="desc-title">
            <CardHeader id="desc-title" title={`Witness descriptions (${detail.description_count})`} description="Original wording is preserved exactly; attributes are the reviewed estimates." />
            <CardBody className="flex flex-col gap-4">
              {descriptions.loading && !descriptions.data ? <LoadingBlock label="Loading descriptions" /> : null}
              {descriptions.error ? <ErrorState message={errorMessage(descriptions.error)} onRetry={descriptions.reload} /> : null}
              {descriptions.data && descriptions.data.length === 0 ? (
                <EmptyState icon={FileText} title="No description saved yet">
                  Add one in the <Link to="/workspace" onClick={() => selectCase(detail.case_id)} className="inline-link text-accent hover:text-accent-strong">Sketch Workspace</Link>.
                </EmptyState>
              ) : null}
              {descriptions.data?.map((d) => (
                <article key={d.id} className="rounded-lg border border-line bg-bg p-4">
                  <header className="mb-2 flex flex-wrap items-center gap-2 text-sm">
                    <h3 className="font-semibold text-ink">{d.label}</h3>
                    <Badge>{LANGUAGE_NAMES[d.language]}</Badge>
                    {d.review_status === 'edited_by_investigator' ? <Badge tone="accent">edited by investigator</Badge> : null}
                    <time className="text-xs text-subtle" dateTime={d.created_at}>{formatDateTime(d.created_at)}</time>
                  </header>
                  <p lang={d.language} className="witness-text whitespace-pre-wrap text-sm text-ink">{d.original_text}</p>
                  <ul className="mt-3 flex flex-wrap gap-2">
                    {Object.entries(d.confirmed_attributes).filter(([, v]) => v).map(([k, v]) => (
                      <li key={k} className="rounded-full border border-line-strong bg-raised px-3 py-1 text-xs text-ink">
                        {attributeLabel(k)}: <span className="text-accent">{valueLabel(k, v)}</span>
                      </li>
                    ))}
                  </ul>
                  {d.unrecognized.length > 0 ? <p className="mt-2 text-xs text-subtle">{d.unrecognized.length} phrase{d.unrecognized.length === 1 ? ' was' : 's were'} not converted into attributes.</p> : null}
                </article>
              ))}
            </CardBody>
          </Card>

          <Card aria-labelledby="sk-title">
            <CardHeader id="sk-title" title={`Sketch versions (${detail.sketch_count})`} actions={<Button size="sm" icon={PencilRuler} onClick={() => { selectCase(detail.case_id); navigate('/workspace') }}>Open workspace</Button>} />
            <CardBody>
              {versions.data && versions.data.items.length === 0 ? <p className="text-sm text-muted">No sketch has been created yet.</p> : null}
              <ul className="flex flex-col gap-1.5 text-sm">
                {versions.data?.items.map((v) => (
                  <li key={v.id} className="flex flex-wrap items-center gap-2 text-muted">
                    <strong className="text-ink">Version {v.version_number}</strong>
                    <Badge tone={v.is_ai_generated ? 'warn' : 'accent'}>{v.is_ai_generated ? 'AI-generated' : 'Schematic · not AI'}</Badge>
                    {v.is_selected ? <Badge tone="ok">selected</Badge> : null}
                    <span className="text-xs text-subtle">{formatDateTime(v.created_at)}</span>
                  </li>
                ))}
              </ul>
            </CardBody>
          </Card>
        </div>

        <div>
          <NotesPanel caseId={detail.case_id} readOnly={closed} versions={versions.data?.items} onChanged={() => { reload(); refresh() }} />
        </div>
      </div>

      {editing ? <EditCaseModal detail={detail} open onClose={() => setEditing(false)} onSaved={() => { reload(); refresh() }} /> : null}
      <ConfirmDialog open={deleting} title="Delete this case?" confirmLabel="Delete case permanently" danger loading={busy === 'delete'} onConfirm={remove} onCancel={() => setDeleting(false)}>
        This removes case <strong className="font-mono text-ink">{detail.case_id}</strong> with all its witness descriptions, notes and {detail.sketch_count} sketch version{detail.sketch_count === 1 ? '' : 's'}, including the stored image files.
        The deletion is recorded in the activity log. This cannot be undone.
      </ConfirmDialog>
    </>
  )
}
