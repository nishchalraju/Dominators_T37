import { RotateCcw } from 'lucide-react'
import { useId } from 'react'
import { useMeta } from '@/hooks/meta-context'
import type { Attributes } from '@/types/api'
import { Badge } from './ui/Badge'
import { Button } from './ui/Button'
import { TextAreaField } from './ui/FormControls'

interface Props {
  value: Attributes
  onChange: (next: Attributes) => void
  /** The parser's values: anything that differs is marked "edited" and can be reset. */
  baseline?: Attributes
  disabled?: boolean
  additionalDetails?: string
  onAdditionalDetailsChange?: (value: string) => void
  /** Use two columns regardless of screen width (for narrow side panels). */
  compact?: boolean
}

/** One drop-down per attribute, built from the backend vocabulary. "Not specified" is always allowed. */
export function AttributeEditor({ value, onChange, baseline, disabled, additionalDetails, onAdditionalDetailsChange, compact = false }: Props) {
  const { meta } = useMeta()
  const prefix = useId()
  if (!meta) return null

  const edited = (key: string) => baseline !== undefined && (value[key] ?? null) !== (baseline[key] ?? null)
  const anyEdited = meta.attributes.some((a) => edited(a.key))

  return (
    <div>
      <div className={`grid gap-4 ${compact ? 'grid-cols-2' : 'sm:grid-cols-2 xl:grid-cols-3'}`}>
        {meta.attributes.map((attr) => {
          const id = `${prefix}-${attr.key}`
          const isEdited = edited(attr.key)
          const hasChips = attr.values.some((v) => v.swatch)
          const chip = attr.values.find((v) => v.value === value[attr.key])?.swatch
          return (
            <div key={attr.key} className="flex flex-col gap-1.5">
              <label htmlFor={id} className="flex items-center justify-between gap-2 text-sm font-medium text-ink">
                <span>{attr.label}</span>
                {isEdited ? <Badge tone="accent">edited</Badge> : null}
              </label>
              <div className="flex items-center gap-2">
                {hasChips ? (
                  // Decorative: the chosen option's text already says the value. It shows the colour that will be drawn.
                  <span
                    aria-hidden="true"
                    data-swatch={chip ?? ''}
                    title={chip ? 'The colour that will be drawn.' : 'Not specified: drawn in a neutral pencil tone.'}
                    className={`size-6 shrink-0 rounded-full border ${chip ? 'border-line-strong' : 'border-dashed border-subtle'}`}
                    style={chip ? { backgroundColor: chip } : undefined}
                  />
                ) : null}
                <select
                  id={id}
                  disabled={disabled}
                  value={value[attr.key] ?? ''}
                  title={attr.values.find((v) => v.value === value[attr.key])?.label ?? 'Not specified'}
                  onChange={(e) => onChange({ ...value, [attr.key]: e.target.value || null })}
                  className={`h-10 w-full min-w-0 rounded-lg border bg-bg px-3 text-sm text-ink focus:border-accent disabled:opacity-60 ${isEdited ? 'border-accent/60' : 'border-line-strong'}`}
                >
                  <option value="">Not specified</option>
                  {attr.values.map((v) => (
                    <option key={v.value} value={v.value}>
                      {v.label}
                    </option>
                  ))}
                </select>
              </div>
            </div>
          )
        })}
      </div>
      {baseline !== undefined ? (
        <div className="mt-3 flex items-center gap-3">
          <Button size="sm" icon={RotateCcw} disabled={disabled || !anyEdited} onClick={() => onChange({ ...baseline })}>
            Reset to parsed values
          </Button>
          <p className="text-xs text-subtle">{anyEdited ? 'You changed some values by hand.' : 'These are the parser’s values, unchanged.'}</p>
        </div>
      ) : null}
      {onAdditionalDetailsChange ? (
        <div className="mt-4">
          <TextAreaField
            label="Other features (free text, optional)"
            hint={`Only AI engines use this text; the schematic engine ignores it. Up to ${meta.max_additional_details} characters.`}
            maxLength={meta.max_additional_details}
            value={additionalDetails ?? ''}
            disabled={disabled}
            onChange={(e) => onAdditionalDetailsChange(e.target.value)}
            className="min-h-20"
          />
        </div>
      ) : null}
    </div>
  )
}
