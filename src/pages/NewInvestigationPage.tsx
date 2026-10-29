import { Check } from 'lucide-react'
import { useState, type FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { AttributeEditor } from '@/components/AttributeEditor'
import { DescriptionForm } from '@/components/DescriptionForm'
import { EngineChooser } from '@/components/EngineChooser'
import { Button } from '@/components/ui/Button'
import { Card, CardBody, CardHeader } from '@/components/ui/Card'
import { Notice } from '@/components/ui/Feedback'
import { TextAreaField, TextField } from '@/components/ui/FormControls'
import { PageHeader } from '@/components/ui/PageHeader'
import { useActiveCase } from '@/hooks/active-case-context'
import { useAuth } from '@/hooks/auth-context'
import { useMeta } from '@/hooks/meta-context'
import { useToast } from '@/hooks/toast-context'
import { useDocumentTitle } from '@/hooks/useDocumentTitle'
import { usePreferences } from '@/hooks/usePreferences'
import { api } from '@/services/api'
import type { Attributes, CaseDetail, Description, EngineChoice } from '@/types/api'
import { ApiError, errorMessage, fieldErrors } from '@/utils/errors'
import { todayIso } from '@/utils/format'
import { suggestedInvestigatorName } from '@/utils/names'

const STEPS = ['Case details', 'Witness description', 'First sketch'] as const

function Stepper({ step }: { step: number }) {
  return (
    <ol className="mb-6 flex flex-wrap gap-x-6 gap-y-2" aria-label="Progress">
      {STEPS.map((label, i) => {
        const state = i < step ? 'done' : i === step ? 'current' : 'todo'
        return (
          <li key={label} aria-current={state === 'current' ? 'step' : undefined} className="flex items-center gap-2 text-sm">
            <span
              className={`grid size-6 place-items-center rounded-full border text-xs font-semibold ${
                state === 'done' ? 'border-ok bg-ok/15 text-ok' : state === 'current' ? 'border-accent bg-accent/15 text-accent' : 'border-line-strong text-subtle'
              }`}
            >
              {state === 'done' ? <Check className="size-3.5" aria-hidden="true" /> : i + 1}
            </span>
            <span className={state === 'todo' ? 'text-subtle' : 'text-ink'}>{label}</span>
            {state === 'done' ? <span className="sr-only">(completed)</span> : null}
          </li>
        )
      })}
    </ol>
  )
}

function CaseStep({ onCreated }: { onCreated: (c: CaseDetail) => void }) {
  const toast = useToast()
  const { selectCase } = useActiveCase()
  const { user } = useAuth()
  const [form, setForm] = useState({
    title: '',
    incident_date: todayIso(),
    investigator_ref: '',
    investigator_name: suggestedInvestigatorName(user), // pre-filled from the account; the investigator can change it
    witness_name: '',
    incident_description: '',
  })
  const [errors, setErrors] = useState<Record<string, string>>({})
  const [formError, setFormError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const set = (key: keyof typeof form) => (e: { target: { value: string } }) => setForm((f) => ({ ...f, [key]: e.target.value }))

  async function submit(event: FormEvent) {
    event.preventDefault()
    const next: Record<string, string> = {}
    if (form.title.trim().length < 3) next.title = 'Enter a title of at least 3 characters.'
    if (!form.incident_date) next.incident_date = 'Choose the incident date.'
    else if (form.incident_date > todayIso()) next.incident_date = 'The incident date cannot be in the future.'
    if (!form.investigator_ref.trim()) next.investigator_ref = 'Enter your reference or badge number.'
    if (form.investigator_name.trim().length < 2) next.investigator_name = 'Enter the name of the investigator in charge (at least 2 characters).'
    if (form.witness_name.trim().length < 2) next.witness_name = 'Enter the witness’s name, or a code such as W-01 if the name must be withheld.'
    setErrors(next)
    setFormError(null)
    if (Object.keys(next).length) return
    setBusy(true)
    try {
      const created = await api.createCase({
        ...form,
        title: form.title.trim(),
        investigator_ref: form.investigator_ref.trim(),
        investigator_name: form.investigator_name.trim(),
        witness_name: form.witness_name.trim(),
      })
      selectCase(created.case_id)
      toast.success(`Case ${created.case_id} created and selected.`)
      onCreated(created)
    } catch (e) {
      const fields = fieldErrors(e)
      if (Object.keys(fields).length) setErrors(fields)
      else setFormError(errorMessage(e))
    } finally {
      setBusy(false)
    }
  }

  return (
    <Card aria-labelledby="step1">
      <CardHeader id="step1" title="1. Case details" description="A unique case ID is generated for you when the case is created." />
      <CardBody>
        <form onSubmit={submit} className="grid max-w-3xl gap-4" noValidate>
          {formError ? <Notice tone="danger">{formError}</Notice> : null}
          <TextField label="Case title" required value={form.title} onChange={set('title')} error={errors.title} maxLength={200} placeholder="e.g. Market Street incident" />
          <div className="grid gap-4 sm:grid-cols-2">
            <TextField label="Incident date" type="date" required value={form.incident_date} max={todayIso()} onChange={set('incident_date')} error={errors.incident_date} />
            <TextField label="Investigator reference" required value={form.investigator_ref} onChange={set('investigator_ref')} error={errors.investigator_ref} maxLength={64} hint="Your badge or file reference." />
          </div>
          <div className="grid gap-4 sm:grid-cols-2">
            <TextField label="Investigator name" required value={form.investigator_name} onChange={set('investigator_name')} error={errors.investigator_name} maxLength={120} autoComplete="off" hint="Who is investigating. Filled in from your account; change it if someone else is in charge." />
            <TextField label="Witness name" required value={form.witness_name} onChange={set('witness_name')} error={errors.witness_name} maxLength={120} autoComplete="off" hint="Who is giving the description. Use a code such as W-01 if the name must be withheld." />
          </div>
          <p className="-mt-2 text-xs text-subtle">Names are personal data. Enter only what your organisation allows. They are shown on the case, found by the search boxes and printed in the PDF report.</p>
          <TextAreaField label="Incident description" value={form.incident_description} onChange={set('incident_description')} error={errors.incident_description} maxLength={5000} hint="Optional. Describe the incident, not the people involved." />
          <div>
            <Button type="submit" variant="primary" loading={busy}>
              Create case and continue
            </Button>
          </div>
        </form>
      </CardBody>
    </Card>
  )
}

function GenerateStep({ created, description, onBack }: { created: CaseDetail; description: Description | null; onBack: () => void }) {
  const navigate = useNavigate()
  const toast = useToast()
  const { refresh } = useActiveCase()
  const prefs = usePreferences()
  const { valueLabel, attributeLabel } = useMeta()
  const [attributes, setAttributes] = useState<Attributes>(description?.confirmed_attributes ?? {})
  const [engine, setEngine] = useState<EngineChoice>(prefs.engine)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<ApiError | Error | null>(null)
  const chosen = Object.entries(attributes).filter(([, v]) => v)

  async function generate() {
    setBusy(true)
    setError(null)
    try {
      await api.generateSketch({ case_id: created.case_id, description_id: description?.id ?? null, attributes, engine })
      prefs.setEngine(engine)
      refresh()
      toast.success('First sketch created. You can now compare and revise it.')
      navigate('/workspace')
    } catch (e) {
      setError(e instanceof Error ? e : new Error(String(e)))
    } finally {
      setBusy(false)
    }
  }

  const steps = error instanceof ApiError && Array.isArray(error.extra.setup_steps) ? (error.extra.setup_steps as string[]) : []

  return (
    <Card aria-labelledby="step3">
      <CardHeader id="step3" title="3. First sketch" description="Choose how the first picture is made. You can revise it as often as you like; every revision is kept as a new version." />
      <CardBody className="flex flex-col gap-6">
        {description ? (
          <div>
            <h3 className="mb-2 text-sm font-semibold text-ink">Attributes that will be drawn</h3>
            {chosen.length === 0 ? (
              <p className="text-sm text-muted">No attribute is specified. Go back and review the description, or choose attributes below.</p>
            ) : (
              <ul className="flex flex-wrap gap-2">
                {chosen.map(([k, v]) => (
                  <li key={k} className="rounded-full border border-line-strong bg-raised px-3 py-1 text-xs text-ink">
                    {attributeLabel(k)}: <span className="text-accent">{valueLabel(k, v)}</span>
                  </li>
                ))}
              </ul>
            )}
          </div>
        ) : (
          <div>
            <h3 className="mb-1 text-sm font-semibold text-ink">Choose the attributes by hand</h3>
            <p className="mb-4 text-sm text-muted">You skipped the description, so pick at least one attribute to draw.</p>
            <AttributeEditor value={attributes} onChange={setAttributes} />
          </div>
        )}

        <EngineChooser value={engine} onChange={setEngine} />

        {error ? (
          <Notice tone="danger" title={error instanceof ApiError && error.code === 'model_unavailable' ? 'The AI engine is not set up' : 'The sketch could not be created'}>
            {error.message}
            {steps.length > 0 ? (
              <ol className="mt-2 list-decimal space-y-1 pl-5">
                {steps.map((s) => (
                  <li key={s}>{s}</li>
                ))}
              </ol>
            ) : null}
            {engine === 'ai' ? (
              <div className="mt-3">
                <Button size="sm" onClick={() => setEngine('schematic')}>
                  Switch to the schematic engine myself
                </Button>
              </div>
            ) : null}
          </Notice>
        ) : null}

        <div className="flex flex-wrap gap-3">
          <Button onClick={onBack}>Back</Button>
          <Button variant="primary" onClick={generate} loading={busy} disabled={chosen.length === 0 && engine === 'schematic'}>
            Generate first sketch
          </Button>
          <Button variant="ghost" onClick={() => navigate('/workspace')}>
            Skip to the workspace
          </Button>
        </div>
      </CardBody>
    </Card>
  )
}

export function NewInvestigationPage() {
  useDocumentTitle('New investigation')
  const prefs = usePreferences()
  const [step, setStep] = useState(0)
  const [created, setCreated] = useState<CaseDetail | null>(null)
  const [description, setDescription] = useState<Description | null>(null)

  return (
    <>
      <PageHeader title="New Investigation" description="Open a case, record what the witness said, review the extracted attributes and create the first sketch." />
      <Stepper step={step} />
      {step === 0 ? (
        <CaseStep
          onCreated={(c) => {
            setCreated(c)
            setStep(1)
          }}
        />
      ) : null}
      {step === 1 && created ? (
        <Card aria-labelledby="step2">
          <CardHeader id="step2" title="2. Witness description" description={`Case ${created.case_id}. English, Kannada or Hindi. Nothing here identifies anyone; it only turns words into editable attributes.`} />
          <CardBody>
            <DescriptionForm
              caseId={created.case_id}
              defaultLabel={created.witness_name || 'Witness 1'}
              defaultLanguage={prefs.language}
              onSaved={(d) => {
                prefs.setLanguage(d.language)
                setDescription(d)
                setStep(2)
              }}
              onSkip={() => setStep(2)}
            />
          </CardBody>
        </Card>
      ) : null}
      {step === 2 && created ? <GenerateStep created={created} description={description} onBack={() => setStep(1)} /> : null}
    </>
  )
}
