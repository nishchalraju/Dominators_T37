import { CircleAlert, CircleCheck, FileDown } from 'lucide-react'
import { useState } from 'react'
import { Link } from 'react-router-dom'
import { ActiveCaseGate } from '@/components/ActiveCaseGate'
import { AuthImage } from '@/components/AuthImage'
import { CasePeople } from '@/components/CasePeople'
import { DisclaimerBanner } from '@/components/DisclaimerBanner'
import { EngineBadge } from '@/components/EngineBadge'
import { StatusBadge } from '@/components/StatusBadge'
import { Button } from '@/components/ui/Button'
import { Card, CardBody, CardHeader } from '@/components/ui/Card'
import { LoadingBlock, Notice } from '@/components/ui/Feedback'
import { PageHeader } from '@/components/ui/PageHeader'
import { useToast } from '@/hooks/toast-context'
import { useAsync } from '@/hooks/useAsync'
import { useDocumentTitle } from '@/hooks/useDocumentTitle'
import { api } from '@/services/api'
import type { CaseDetail } from '@/types/api'
import { saveBlob } from '@/utils/download'
import { errorMessage } from '@/utils/errors'
import { formatDateTime } from '@/utils/format'

function Check({ ok, children }: { ok: boolean; children: React.ReactNode }) {
  const Icon = ok ? CircleCheck : CircleAlert
  return (
    <li className="flex items-start gap-2 text-sm">
      <Icon className={`mt-0.5 size-4 shrink-0 ${ok ? 'text-ok' : 'text-warn'}`} aria-hidden="true" />
      <span className="text-muted">
        <span className="sr-only">{ok ? 'Ready: ' : 'Missing: '}</span>
        {children}
      </span>
    </li>
  )
}

function ReportPanel({ detail }: { detail: CaseDetail }) {
  const toast = useToast()
  const versions = useAsync((signal) => api.listVersions(detail.case_id, { signal }), [detail.case_id, detail.sketch_count])
  const [busy, setBusy] = useState(false)
  const selected = versions.data?.items.find((v) => v.is_selected)

  async function download() {
    setBusy(true)
    try {
      const { blob, filename } = await api.downloadReport(detail.case_id)
      saveBlob(blob, filename ?? `SketchAssist_${detail.case_id}_report.pdf`)
      toast.success('The report was generated and downloaded.')
    } catch (e) {
      toast.error(errorMessage(e))
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="grid gap-6 xl:grid-cols-[1fr_24rem]">
      <div className="flex flex-col gap-6">
        <Card aria-labelledby="ready-title">
          <CardHeader
            id="ready-title"
            title={detail.title}
            description={
              <span className="flex flex-wrap items-center gap-2">
                <span className="font-mono text-accent">{detail.case_id}</span> <StatusBadge status={detail.status} /> · last updated {formatDateTime(detail.updated_at)}
              </span>
            }
          />
          <CardBody className="flex flex-col gap-5">
            <CasePeople people={detail} />
            <div>
              <h3 className="mb-2 text-sm font-semibold text-ink">What the report will contain</h3>
              <ul className="flex flex-col gap-2">
                <Check ok={!!detail.investigator_name && !!detail.witness_name}>
                  Case ID, title, status, incident date, investigator and witness names, your reference, owner and dates
                  {!detail.investigator_name || !detail.witness_name ? ' (a name is not recorded; the report will say so. Add it on the case page)' : ''}
                </Check>
                <Check ok={detail.description_count > 0}>
                  Witness description text exactly as entered, with the reviewed attributes — {detail.description_count} saved
                  {detail.description_count === 0 ? ' (the report will say none was saved)' : ''}
                </Check>
                <Check ok={!!selected}>
                  Selected sketch with a caption stating whether it is AI-generated
                  {selected ? ` — version ${selected.version_number}` : ' (none selected yet; the report will say so)'}
                </Check>
                <Check ok={detail.sketch_count > 0}>Version history with every instruction and attribute change — {detail.sketch_count} version{detail.sketch_count === 1 ? '' : 's'}</Check>
                <Check ok={detail.note_count > 0}>Investigator notes — {detail.note_count} recorded</Check>
                <Check ok>Methods, limitations and the statement “preliminary investigative aid requiring human review”</Check>
                <Check ok>Generation timestamp and who generated it</Check>
              </ul>
            </div>
            {detail.description_count === 0 || !selected ? (
              <Notice tone="warn">
                The report can be generated now, but it will be incomplete. Add what is missing in the <Link to="/workspace" className="inline-link text-accent hover:text-accent-strong">Sketch Workspace</Link>.
              </Notice>
            ) : null}
            <div>
              <Button variant="primary" icon={FileDown} onClick={download} loading={busy}>
                Download PDF report
              </Button>
            </div>
          </CardBody>
        </Card>
        <DisclaimerBanner />
      </div>

      <Card aria-labelledby="preview-title">
        <CardHeader id="preview-title" title="Sketch that will be included" />
        <CardBody>
          {versions.loading && !versions.data ? <LoadingBlock label="Loading" /> : null}
          {versions.data && !selected ? <p className="text-sm text-muted">No sketch is selected for this case.</p> : null}
          {selected ? (
            <figure className="flex flex-col gap-3">
              <AuthImage src={selected.image_url} alt={`Selected sketch, version ${selected.version_number}`} className="aspect-square w-full rounded-lg border border-line bg-raised object-contain" />
              <figcaption className="flex flex-wrap items-center gap-2 text-sm text-muted">
                <strong className="text-ink">Version {selected.version_number}</strong> <EngineBadge isAi={selected.is_ai_generated} />
                <span className="w-full text-xs text-subtle">{selected.engine_label} · {formatDateTime(selected.created_at)}</span>
              </figcaption>
            </figure>
          ) : null}
        </CardBody>
      </Card>
    </div>
  )
}

export function ReportsPage() {
  useDocumentTitle('Reports')
  return (
    <>
      <PageHeader title="Reports" description="Create a PDF case report for the selected case. It is a preliminary investigative aid and must be reviewed by a person." />
      <ActiveCaseGate purpose="prepare a report for">{(c) => <ReportPanel key={c.case_id} detail={c} />}</ActiveCaseGate>
    </>
  )
}
