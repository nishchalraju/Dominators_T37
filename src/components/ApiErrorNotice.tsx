import { ApiError } from '@/utils/errors'
import { Notice } from './ui/Feedback'

const TITLES: Record<string, string> = {
  model_unavailable: 'The AI engine is not set up',
  no_supported_change: 'Nothing was changed',
  no_attributes: 'Nothing to draw yet',
  engine_mismatch: 'That engine cannot edit this sketch',
  case_closed: 'The case is closed',
  rate_limited: 'Slow down a little',
  model_request_failed: 'The AI engine could not do that',
  model_output_invalid: 'The AI engine returned an unusable image',
}

const strings = (value: unknown): string[] => (Array.isArray(value) ? value.filter((x): x is string => typeof x === 'string') : [])

/** Explains a failed request in plain words, including setup steps or the parts of an instruction that were ignored. */
export function ApiErrorNotice({ error, className = '' }: { error: unknown; className?: string }) {
  const err = error instanceof ApiError ? error : null
  const message = error instanceof Error ? error.message : 'Something went wrong.'
  const steps = strings(err?.extra.setup_steps)
  const notes = strings(err?.extra.notes)
  const ignored = Array.isArray(err?.extra.ignored) ? (err?.extra.ignored as { text: string; reason: string }[]) : []
  return (
    <Notice tone={err?.code === 'no_supported_change' ? 'warn' : 'danger'} title={(err && TITLES[err.code]) ?? 'That did not work'} className={className}>
      <p>{message}</p>
      {notes.length > 0 ? <ul className="mt-2 list-disc space-y-1 pl-5">{notes.map((n) => <li key={n}>{n}</li>)}</ul> : null}
      {ignored.length > 0 ? (
        <div className="mt-2">
          <p className="font-medium text-ink">Not understood:</p>
          <ul className="list-disc space-y-1 pl-5">
            {ignored.map((i) => (
              <li key={i.text}>
                <span className="witness-text text-ink">“{i.text}”</span> — {i.reason}
              </li>
            ))}
          </ul>
        </div>
      ) : null}
      {steps.length > 0 ? (
        <div className="mt-2">
          <p className="font-medium text-ink">To set it up:</p>
          <ol className="list-decimal space-y-1 pl-5">{steps.map((s) => <li key={s}>{s}</li>)}</ol>
        </div>
      ) : null}
    </Notice>
  )
}
