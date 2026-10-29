import { useMeta } from '@/hooks/meta-context'
import type { Language } from '@/types/api'
import { SelectField } from './ui/FormControls'

interface Props {
  value: Language
  onChange: (value: Language) => void
  label?: string
  hint?: string
}

const FALLBACK = [
  { code: 'en', label: 'English', native_label: 'English' },
  { code: 'kn', label: 'Kannada', native_label: 'ಕನ್ನಡ' },
  { code: 'hi', label: 'Hindi', native_label: 'हिन्दी' },
]

export function LanguageSelect({ value, onChange, label = 'Language of the text', hint }: Props) {
  const { meta } = useMeta()
  const languages = meta?.languages ?? FALLBACK
  return (
    <SelectField label={label} hint={hint} value={value} onChange={(e) => onChange(e.target.value as Language)}>
      {languages.map((l) => (
        <option key={l.code} value={l.code}>
          {l.label} ({l.native_label})
        </option>
      ))}
    </SelectField>
  )
}
