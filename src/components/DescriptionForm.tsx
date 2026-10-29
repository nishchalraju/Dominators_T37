import { ScanFace } from 'lucide-react'
import { useState } from 'react'
import { useMeta } from '@/hooks/meta-context'
import { useToast } from '@/hooks/toast-context'
import { api } from '@/services/api'
import type { Attributes, Description, Language, ParseResponse } from '@/types/api'
import { errorMessage, fieldErrors } from '@/utils/errors'
import { AttributeEditor } from './AttributeEditor'
import { LanguageSelect } from './LanguageSelect'
import { ParseResultPanel } from './ParseResultPanel'
import { Button } from './ui/Button'
import { Notice } from './ui/Feedback'
import { TextAreaField, TextField } from './ui/FormControls'

const MAX_TEXT = 4000

interface Props {
  caseId: string
  defaultLanguage?: Language
  defaultLabel?: string
  onSaved: (description: Description) => void
  onSkip?: () => void
  skipLabel?: string
}

/**
 * Witness description -> candidate attributes -> investigator review -> saved.
 * The original wording is saved exactly as typed; the reviewed attributes are stored separately.
 */
export function DescriptionForm({ caseId, defaultLanguage = 'en', defaultLabel = 'Witness 1', onSaved, onSkip, skipLabel = 'Skip: I will choose the attributes by hand' }: Props) {
  const toast = useToast()
  const { meta } = useMeta()
  const [language, setLanguage] = useState<Language>(defaultLanguage)
  const [label, setLabel] = useState(defaultLabel)
  const [text, setText] = useState('')
  const [parsed, setParsed] = useState<ParseResponse | null>(null)
  const [attributes, setAttributes] = useState<Attributes>({})
  const [details, setDetails] = useState('')
  const [parsing, setParsing] = useState(false)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [fieldError, setFieldError] = useState<Record<string, string>>({})

  const tooShort = text.trim().length < 3

  async function read() {
    setError(null)
    setParsing(true)
    try {
      const result = await api.parseDescription({ text, language })
      setParsed(result)
      setAttributes({ ...result.attributes })
    } catch (e) {
      setError(errorMessage(e))
      setFieldError(fieldErrors(e))
    } finally {
      setParsing(false)
    }
  }

  async function save() {
    setError(null)
    setSaving(true)
    try {
      const saved = await api.saveDescription(caseId, {
        label: label.trim() || defaultLabel,
        language,
        original_text: text,
        confirmed_attributes: attributes,
        additional_details: details,
      })
      toast.success('Witness description saved with your reviewed attributes.')
      onSaved(saved)
    } catch (e) {
      setError(errorMessage(e))
      setFieldError(fieldErrors(e))
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="flex flex-col gap-5">
      <div className="grid gap-4 sm:grid-cols-2">
        <LanguageSelect value={language} onChange={(l) => { setLanguage(l); setParsed(null) }} hint="Choose the language the witness used." />
        <TextField label="Who gave this description" value={label} onChange={(e) => setLabel(e.target.value)} maxLength={60} hint="Starts with the case’s witness name. Change it if someone else gave this description, for example “Witness 2”." error={fieldError.label} />
      </div>
      <div>
        <TextAreaField
          label="What the witness said"
          lang={language}
          value={text}
          onChange={(e) => {
            setText(e.target.value)
            if (parsed) setParsed(null)
          }}
          maxLength={MAX_TEXT}
          rows={6}
          className="witness-text min-h-36"
          placeholder={language === 'kn' ? 'ಉದಾ: ಅವನಿಗೆ ದುಂಡನೆಯ ಮುಖ, ದಪ್ಪ ಹುಬ್ಬುಗಳು ಮತ್ತು ಗಡ್ಡ ಇತ್ತು.' : language === 'hi' ? 'उदा: उसका चेहरा गोल था, भौंहें मोटी थीं और दाढ़ी थी।' : 'e.g. A man about 35 with a round face, thick eyebrows and a short beard.'}
          hint={`Your exact wording is saved unchanged. ${text.length} / ${MAX_TEXT} characters.`}
          error={fieldError.original_text ?? fieldError.text}
        />
      </div>

      {error ? <Notice tone="danger">{error}</Notice> : null}

      <div className="flex flex-wrap gap-3">
        <Button variant="primary" icon={ScanFace} onClick={read} loading={parsing} disabled={tooShort}>
          Read description
        </Button>
        {onSkip && !parsed ? (
          <Button variant="ghost" onClick={onSkip}>
            {skipLabel}
          </Button>
        ) : null}
      </div>
      {tooShort ? <p className="-mt-3 text-xs text-subtle">Type at least a few words to enable reading.</p> : null}

      {parsed ? (
        <div className="flex flex-col gap-6 border-t border-line pt-5">
          <ParseResultPanel result={parsed} />
          <div>
            <h3 className="mb-1 text-sm font-semibold text-ink">Review and correct the attributes</h3>
            <p className="mb-4 text-sm text-muted">
              These are estimates. Change any value you disagree with, or choose “Not specified”. Vocabulary version {meta?.vocabulary_version ?? '—'}.
            </p>
            <AttributeEditor value={attributes} onChange={setAttributes} baseline={parsed.attributes} additionalDetails={details} onAdditionalDetailsChange={setDetails} />
          </div>
          <div className="flex flex-wrap gap-3">
            <Button variant="primary" onClick={save} loading={saving}>
              Save description to the case
            </Button>
          </div>
        </div>
      ) : null}
    </div>
  )
}
