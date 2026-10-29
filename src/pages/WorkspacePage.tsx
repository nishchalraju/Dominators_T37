import { Download, Plus, Wand2 } from 'lucide-react'
import { useEffect, useMemo, useState, type FormEvent } from 'react'
import { ActiveCaseGate } from '@/components/ActiveCaseGate'
import { ApiErrorNotice } from '@/components/ApiErrorNotice'
import { AttributeEditor } from '@/components/AttributeEditor'
import { AuthImage } from '@/components/AuthImage'
import { CasePeople } from '@/components/CasePeople'
import { DescriptionForm } from '@/components/DescriptionForm'
import { EngineBadge } from '@/components/EngineBadge'
import { EngineChooser } from '@/components/EngineChooser'
import { LanguageSelect } from '@/components/LanguageSelect'
import { NotesPanel } from '@/components/NotesPanel'
import { RevisionResult } from '@/components/RevisionResult'
import { VersionCard } from '@/components/VersionCard'
import { VersionCompare } from '@/components/VersionCompare'
import { Button } from '@/components/ui/Button'
import { Card, CardBody, CardHeader } from '@/components/ui/Card'
import { EmptyState, ErrorState, LoadingBlock, Notice } from '@/components/ui/Feedback'
import { SelectField, TextAreaField } from '@/components/ui/FormControls'
import { Modal } from '@/components/ui/Modal'
import { PageHeader } from '@/components/ui/PageHeader'
import { useActiveCase } from '@/hooks/active-case-context'
import { useMeta } from '@/hooks/meta-context'
import { useToast } from '@/hooks/toast-context'
import { useAsync } from '@/hooks/useAsync'
import { useDocumentTitle } from '@/hooks/useDocumentTitle'
import { usePreferences } from '@/hooks/usePreferences'
import { api } from '@/services/api'
import type { Attributes, CaseDetail, EngineChoice, Language, SketchVersion } from '@/types/api'
import { saveBlob } from '@/utils/download'
import { errorMessage } from '@/utils/errors'
import { formatBytes, formatDateTime, LANGUAGE_NAMES } from '@/utils/format'

const SUGGESTIONS = ['Make the eyebrows thicker', 'Add glasses', 'Remove the beard', 'Make the hair longer', 'Make the nose broader', 'Make the face rounder', 'Make the skin darker', 'Make the skin lighter']

export function WorkspacePage() {
  useDocumentTitle('Sketch Workspace')
  return (
    <>
      <PageHeader
        title="Sketch Workspace"
        description="Generate a sketch, revise it with plain instructions, and compare versions. Every revision is saved as a new version; nothing is ever overwritten."
      />
      <ActiveCaseGate purpose="work on">{(c) => <Workspace key={c.case_id} detail={c} />}</ActiveCaseGate>
    </>
  )
}

function Workspace({ detail }: { detail: CaseDetail }) {
  const toast = useToast()
  const { refresh } = useActiveCase()
  const versions = useAsync((signal) => api.listVersions(detail.case_id, { signal }), [detail.case_id])
  const descriptions = useAsync((signal) => api.listDescriptions(detail.case_id, { signal }), [detail.case_id])
  const [compareIds, setCompareIds] = useState<number[]>([])
  const [showCompare, setShowCompare] = useState(false)
  const [selectingId, setSelectingId] = useState<number | null>(null)
  const [downloadingId, setDownloadingId] = useState<number | null>(null)
  const [addingDescription, setAddingDescription] = useState(false)
  const [lastCreatedId, setLastCreatedId] = useState<number | null>(null)

  const items = versions.data?.items ?? []
  const selected = items.find((v) => v.is_selected) ?? items[items.length - 1]
  const readOnly = detail.status === 'closed'
  const left = items.find((v) => v.id === compareIds[0])
  const right = items.find((v) => v.id === compareIds[1])

  function reloadAll() {
    versions.reload()
    refresh()
  }

  async function select(v: SketchVersion) {
    setSelectingId(v.id)
    try {
      await api.selectVersion(v.id)
      toast.success(`Version ${v.version_number} is now selected for editing.`)
      reloadAll()
    } catch (e) {
      toast.error(errorMessage(e))
    } finally {
      setSelectingId(null)
    }
  }

  async function download(v: SketchVersion) {
    setDownloadingId(v.id)
    try {
      const { blob, filename } = await api.imageBlob(v.download_url)
      saveBlob(blob, filename ?? `${detail.case_id}_v${v.version_number}.png`)
    } catch (e) {
      toast.error(errorMessage(e))
    } finally {
      setDownloadingId(null)
    }
  }

  function toggleCompare(id: number) {
    setShowCompare(false)
    setCompareIds((ids) => (ids.includes(id) ? ids.filter((x) => x !== id) : [...ids.slice(-1), id]))
  }

  return (
    <>
      <CasePeople people={detail} className="mb-5" />
      {readOnly ? (
        <Notice tone="info" title="This case is closed" className="mb-6">
          You can look at and download sketches, but nothing can be added. Reopen the case under Case Management to continue.
        </Notice>
      ) : null}

      <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_26rem]">
        <div className="flex min-w-0 flex-col gap-6">
          {versions.loading && !versions.data ? <LoadingBlock label="Loading sketches" /> : null}
          {versions.error ? <ErrorState message={errorMessage(versions.error)} onRetry={versions.reload} title="Could not load the sketches" /> : null}

          {versions.data && !selected ? (
            <Card>
              <EmptyState icon={Wand2} title="No sketch yet">
                Choose attributes in the “Generate a sketch” panel (or add a witness description first) and press Generate. The result appears here.
              </EmptyState>
            </Card>
          ) : null}

          {selected ? (
            <SelectedSketch
              key={selected.id}
              version={selected}
              readOnly={readOnly}
              highlight={selected.id === lastCreatedId}
              onDownload={() => download(selected)}
              downloading={downloadingId === selected.id}
              onCreated={(v) => {
                setLastCreatedId(v.id)
                reloadAll()
              }}
            />
          ) : null}

          {showCompare && left && right ? <VersionCompare left={left} right={right} onClose={() => setShowCompare(false)} /> : null}

          {items.length > 0 ? (
            <Card aria-labelledby="history-title">
              <CardHeader
                id="history-title"
                title={`Version history (${items.length})`}
                description="Tick two versions to compare them side by side. “Select for editing” chooses the version the next revision starts from and the one used in the report."
                actions={
                  <Button size="sm" variant="primary" disabled={compareIds.length !== 2} onClick={() => setShowCompare(true)}>
                    Compare selected ({compareIds.length}/2)
                  </Button>
                }
              />
              <CardBody>
                <ul className="grid gap-4 sm:grid-cols-2 2xl:grid-cols-3">
                  {[...items].reverse().map((v) => (
                    <VersionCard
                      key={v.id}
                      version={v}
                      compared={compareIds.includes(v.id)}
                      onToggleCompare={() => toggleCompare(v.id)}
                      onSelect={() => select(v)}
                      onDownload={() => download(v)}
                      selecting={selectingId === v.id}
                      downloading={downloadingId === v.id}
                      readOnly={readOnly}
                    />
                  ))}
                </ul>
              </CardBody>
            </Card>
          ) : null}
        </div>

        <aside className="flex min-w-0 flex-col gap-6" aria-label="Create and annotate">
          <GenerateCard
            detail={detail}
            readOnly={readOnly}
            selected={selected}
            descriptions={descriptions.data ?? []}
            onCreated={(v) => {
              setLastCreatedId(v.id)
              reloadAll()
            }}
          />
          <Card aria-labelledby="desc-title">
            <CardHeader
              id="desc-title"
              title={`Witness descriptions (${descriptions.data?.length ?? 0})`}
              actions={
                <Button size="sm" icon={Plus} onClick={() => setAddingDescription(true)} disabled={readOnly}>
                  Add
                </Button>
              }
            />
            <CardBody>
              {descriptions.loading && !descriptions.data ? <LoadingBlock label="Loading" /> : null}
              {descriptions.data && descriptions.data.length === 0 ? <p className="text-sm text-muted">No description saved yet. Add one to extract attributes from the witness’s words.</p> : null}
              <ul className="flex flex-col gap-2">
                {descriptions.data?.map((d) => (
                  <li key={d.id} className="rounded-lg border border-line bg-bg p-3 text-sm">
                    <p className="mb-1 font-medium text-ink">
                      {d.label} <span className="font-normal text-subtle">· {LANGUAGE_NAMES[d.language]}</span>
                    </p>
                    <p lang={d.language} className="witness-text line-clamp-3 text-muted">{d.original_text}</p>
                  </li>
                ))}
              </ul>
            </CardBody>
          </Card>
          <NotesPanel caseId={detail.case_id} readOnly={readOnly} versions={items} />
        </aside>
      </div>

      <Modal open={addingDescription} title="Add a witness description" onClose={() => setAddingDescription(false)} wide>
        <DescriptionForm
          caseId={detail.case_id}
          defaultLabel={(descriptions.data?.length ?? 0) === 0 && detail.witness_name ? detail.witness_name : `Witness ${(descriptions.data?.length ?? 0) + 1}`}
          onSaved={() => {
            setAddingDescription(false)
            descriptions.reload()
            refresh()
          }}
        />
      </Modal>
    </>
  )
}

// ---------------------------------------------------------------------------------------------------------------
function SelectedSketch({ version, readOnly, highlight, onDownload, downloading, onCreated }: {
  version: SketchVersion
  readOnly: boolean
  highlight: boolean
  onDownload: () => void
  downloading: boolean
  onCreated: (v: SketchVersion) => void
}) {
  const toast = useToast()
  const prefs = usePreferences()
  const { attributeLabel, valueLabel } = useMeta()
  const [instruction, setInstruction] = useState('')
  const [language, setLanguage] = useState<Language>(prefs.language)
  const [engine, setEngine] = useState<EngineChoice>(version.is_ai_generated ? 'ai' : 'schematic')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<unknown>(null)

  async function submit(event: FormEvent) {
    event.preventDefault()
    if (instruction.trim().length < 3) return
    setBusy(true)
    setError(null)
    try {
      const next = await api.reviseSketch(version.id, { instruction: instruction.trim(), language, engine })
      prefs.setLanguage(language)
      setInstruction('')
      toast.success(`Version ${next.version_number} created from version ${version.version_number}.`)
      onCreated(next)
    } catch (e) {
      setError(e)
    } finally {
      setBusy(false)
    }
  }

  const specified = Object.entries(version.attributes).filter(([, v]) => v)
  return (
    <Card aria-labelledby="selected-title" className={highlight ? 'border-accent/60' : ''}>
      <CardHeader
        id="selected-title"
        title={`Version ${version.version_number} — selected for editing`}
        description={`${version.engine_label}${version.model_name ? ` · ${version.model_name}` : ''}`}
        actions={
          <Button size="sm" icon={Download} onClick={onDownload} loading={downloading}>
            Download with caption
          </Button>
        }
      />
      <CardBody className="flex flex-col gap-6">
        <div className="grid gap-6 lg:grid-cols-[minmax(0,26rem)_1fr]">
          <figure>
            <AuthImage src={version.image_url} alt={`Sketch version ${version.version_number}`} className="aspect-square w-full rounded-lg border border-line bg-raised object-contain" />
            <figcaption className="mt-2 flex flex-wrap items-center gap-2 text-xs text-subtle">
              <EngineBadge isAi={version.is_ai_generated} />
              <span>{version.width}×{version.height}px · {formatBytes(version.file_size)}</span>
              <time dateTime={version.created_at}>{formatDateTime(version.created_at)}</time>
            </figcaption>
          </figure>
          <div className="flex min-w-0 flex-col gap-4 text-sm">
            <div>
              <h3 className="mb-1.5 font-semibold text-ink">Attributes drawn</h3>
              {specified.length === 0 ? (
                <p className="text-muted">None were specified.</p>
              ) : (
                <ul className="flex flex-wrap gap-2">
                  {specified.map(([k, v]) => (
                    <li key={k} className="rounded-full border border-line-strong bg-raised px-3 py-1 text-xs text-ink">
                      {attributeLabel(k)}: <span className="text-accent">{valueLabel(k, v)}</span>
                    </li>
                  ))}
                </ul>
              )}
            </div>
            {version.notes.length > 0 ? (
              <div>
                <h3 className="mb-1.5 font-semibold text-ink">About this image</h3>
                <ul className="list-disc space-y-1 pl-5 text-muted">{version.notes.map((n) => <li key={n}>{n}</li>)}</ul>
              </div>
            ) : null}
            {version.kind === 'revision' && version.revision_details ? (
              <div>
                <h3 className="mb-1.5 font-semibold text-ink">How this version was made</h3>
                <p className="witness-text mb-2 text-muted">Instruction: “{version.instruction}”</p>
                <RevisionResult details={version.revision_details} />
              </div>
            ) : null}
          </div>
        </div>

        {highlight ? (
          <Notice tone="ok" title={`Version ${version.version_number} was just created and is now selected`}>
            {version.parent_version_number ? `It was made from version ${version.parent_version_number}, which is unchanged. ` : ''}
            The “How this version was made” section above lists what was applied and what was not.
          </Notice>
        ) : null}

        {readOnly ? null : (
          <form onSubmit={submit} className="flex flex-col gap-4 border-t border-line pt-5" aria-labelledby="revise-title" noValidate>
            <div>
              <h3 id="revise-title" className="font-semibold text-ink">Revise version {version.version_number}</h3>
              <p className="text-sm text-muted">Describe the change in words. A new version is created; version {version.version_number} stays exactly as it is.</p>
            </div>
            <TextAreaField
              label="Instruction"
              lang={language}
              value={instruction}
              onChange={(e) => setInstruction(e.target.value)}
              maxLength={500}
              className="witness-text min-h-20"
              hint="English comparatives (“thicker”, “longer”, “broader”, “rounder”, “darker”, “lighter”) and plain values in English, Hindi or Kannada (for example “add glasses”, “make the skin brown”, “दाढ़ी हटाओ”, “ಕನ್ನಡಕ ಸೇರಿಸಿ”)."
            />
            <div className="flex flex-wrap gap-2" aria-label="Example instructions">
              {SUGGESTIONS.map((s) => (
                <button
                  key={s}
                  type="button"
                  onClick={() => { setInstruction(s); setLanguage('en') }}
                  className="rounded-full border border-line-strong px-3 py-1 text-xs text-muted hover:border-accent/60 hover:text-ink"
                >
                  {s}
                </button>
              ))}
            </div>
            <div className="grid gap-4 md:grid-cols-2">
              <LanguageSelect value={language} onChange={setLanguage} label="Language of the instruction" />
            </div>
            <EngineChooser value={engine} onChange={setEngine} disableSchematic={version.is_ai_generated} name="revise-engine" />
            {error ? <ApiErrorNotice error={error} /> : null}
            <div>
              <Button type="submit" variant="primary" icon={Wand2} loading={busy} disabled={instruction.trim().length < 3}>
                Create revision (new version)
              </Button>
            </div>
          </form>
        )}
      </CardBody>
    </Card>
  )
}

// ---------------------------------------------------------------------------------------------------------------
type Source = `d:${number}` | 'sketch' | 'blank'

function GenerateCard({ detail, readOnly, selected, descriptions, onCreated }: {
  detail: CaseDetail
  readOnly: boolean
  selected: SketchVersion | undefined
  descriptions: { id: number; label: string; language: Language; confirmed_attributes: Attributes; additional_details: string }[]
  onCreated: (v: SketchVersion) => void
}) {
  const toast = useToast()
  const prefs = usePreferences()
  const [source, setSource] = useState<Source>('blank')
  const [attributes, setAttributes] = useState<Attributes>({})
  const [details, setDetails] = useState('')
  const [engine, setEngine] = useState<EngineChoice>(prefs.engine)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<unknown>(null)

  const firstDescription = descriptions[0]
  useEffect(() => {
    // start from the first saved description once it is known (only while the form is still untouched)
    if (source === 'blank' && Object.keys(attributes).length === 0 && firstDescription) {
      setSource(`d:${firstDescription.id}`)
      setAttributes({ ...firstDescription.confirmed_attributes })
      setDetails(firstDescription.additional_details)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps -- only react to the description arriving
  }, [firstDescription?.id])

  const chosen = useMemo(() => Object.values(attributes).filter(Boolean).length, [attributes])
  const sourceDescription = source.startsWith('d:') ? descriptions.find((d) => d.id === Number(source.slice(2))) : undefined

  function changeSource(next: Source) {
    setSource(next)
    if (next === 'blank') {
      setAttributes({})
      setDetails('')
    } else if (next === 'sketch' && selected) {
      setAttributes({ ...selected.attributes })
      setDetails(selected.additional_details)
    } else if (next.startsWith('d:')) {
      const d = descriptions.find((x) => x.id === Number(next.slice(2)))
      if (d) {
        setAttributes({ ...d.confirmed_attributes })
        setDetails(d.additional_details)
      }
    }
  }

  async function generate() {
    setBusy(true)
    setError(null)
    try {
      const v = await api.generateSketch({ case_id: detail.case_id, description_id: sourceDescription?.id ?? null, attributes, additional_details: details, engine })
      prefs.setEngine(engine)
      toast.success(`Version ${v.version_number} created and selected.`)
      onCreated(v)
    } catch (e) {
      setError(e)
    } finally {
      setBusy(false)
    }
  }

  return (
    <Card aria-labelledby="gen-title">
      <CardHeader id="gen-title" title="Generate a sketch" description="Creates a new version from the attributes below. It does not replace earlier versions." />
      <CardBody className="flex flex-col gap-5">
        <SelectField label="Take the attributes from" value={source} onChange={(e) => changeSource(e.target.value as Source)} disabled={readOnly}>
          <option value="blank">Start blank</option>
          {selected ? <option value="sketch">The selected sketch (version {selected.version_number})</option> : null}
          {descriptions.map((d) => (
            <option key={d.id} value={`d:${d.id}`}>
              Reviewed attributes: {d.label} ({LANGUAGE_NAMES[d.language]})
            </option>
          ))}
        </SelectField>
        <AttributeEditor compact value={attributes} onChange={setAttributes} disabled={readOnly} additionalDetails={details} onAdditionalDetailsChange={setDetails} />
        <EngineChooser value={engine} onChange={setEngine} name="generate-engine" />
        {error ? <ApiErrorNotice error={error} /> : null}
        <div>
          <Button variant="primary" icon={Wand2} onClick={generate} loading={busy} disabled={readOnly || (chosen === 0 && !(engine === 'ai' && details.trim()))}>
            Generate new version
          </Button>
          {chosen === 0 ? <p className="mt-2 text-xs text-subtle">Choose at least one attribute.</p> : null}
        </div>
      </CardBody>
    </Card>
  )
}
