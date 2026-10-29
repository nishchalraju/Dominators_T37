import { NotebookPen } from 'lucide-react'
import { useState, type FormEvent } from 'react'
import { useAsync } from '@/hooks/useAsync'
import { useToast } from '@/hooks/toast-context'
import { api } from '@/services/api'
import type { SketchVersion } from '@/types/api'
import { errorMessage } from '@/utils/errors'
import { formatDateTime } from '@/utils/format'
import { Button } from './ui/Button'
import { Card, CardBody, CardHeader } from './ui/Card'
import { EmptyState, ErrorState, LoadingBlock, Notice } from './ui/Feedback'
import { SelectField, TextAreaField } from './ui/FormControls'

interface Props {
  caseId: string
  readOnly?: boolean
  versions?: SketchVersion[]
  onChanged?: () => void
}

/** Notes are append-only (they cannot be edited or deleted) so they work as an audit trail. */
export function NotesPanel({ caseId, readOnly = false, versions = [], onChanged }: Props) {
  const toast = useToast()
  const { data, error, loading, reload } = useAsync((signal) => api.listNotes(caseId, { signal }), [caseId])
  const [body, setBody] = useState('')
  const [versionId, setVersionId] = useState('')
  const [saving, setSaving] = useState(false)
  const [formError, setFormError] = useState<string | null>(null)

  async function submit(event: FormEvent) {
    event.preventDefault()
    if (!body.trim()) return
    setSaving(true)
    setFormError(null)
    try {
      await api.addNote(caseId, { body: body.trim(), sketch_version_id: versionId ? Number(versionId) : null })
      setBody('')
      setVersionId('')
      toast.success('Note added.')
      reload()
      onChanged?.()
    } catch (e) {
      setFormError(errorMessage(e))
    } finally {
      setSaving(false)
    }
  }

  return (
    <Card aria-labelledby="notes-title">
      <CardHeader id="notes-title" title="Investigator notes" description="Append-only: notes cannot be edited or deleted." />
      <CardBody className="flex flex-col gap-4">
        {loading && !data ? <LoadingBlock label="Loading notes" /> : null}
        {error ? <ErrorState message={errorMessage(error)} onRetry={reload} /> : null}
        {data && data.length === 0 ? <EmptyState icon={NotebookPen} title="No notes yet">Record observations, doubts or decisions here.</EmptyState> : null}
        {data && data.length > 0 ? (
          <ol className="flex flex-col gap-3">
            {data.map((n) => (
              <li key={n.id} className="rounded-lg border border-line bg-bg p-3 text-sm">
                <p className="witness-text whitespace-pre-wrap text-ink">{n.body}</p>
                <p className="mt-1.5 text-xs text-subtle">
                  {n.author_username ?? 'unknown'} · <time dateTime={n.created_at}>{formatDateTime(n.created_at)}</time>
                  {n.sketch_version_id ? ` · about version ${versions.find((v) => v.id === n.sketch_version_id)?.version_number ?? n.sketch_version_id}` : ''}
                </p>
              </li>
            ))}
          </ol>
        ) : null}

        {readOnly ? (
          <Notice tone="info">This case is closed. Reopen it to add notes.</Notice>
        ) : (
          <form onSubmit={submit} className="flex flex-col gap-3 border-t border-line pt-4">
            {formError ? <Notice tone="danger">{formError}</Notice> : null}
            <TextAreaField label="New note" value={body} onChange={(e) => setBody(e.target.value)} maxLength={2000} className="min-h-20" />
            {versions.length > 0 ? (
              <SelectField label="About a sketch version (optional)" value={versionId} onChange={(e) => setVersionId(e.target.value)}>
                <option value="">No specific version</option>
                {versions.map((v) => (
                  <option key={v.id} value={v.id}>
                    Version {v.version_number}
                  </option>
                ))}
              </SelectField>
            ) : null}
            <div>
              <Button type="submit" variant="primary" loading={saving} disabled={!body.trim()}>
                Add note
              </Button>
            </div>
          </form>
        )}
      </CardBody>
    </Card>
  )
}
