import { useId, type InputHTMLAttributes, type ReactNode, type SelectHTMLAttributes, type TextareaHTMLAttributes } from 'react'

const CONTROL =
  'w-full rounded-lg border bg-bg px-3 text-sm text-ink placeholder:text-subtle transition-colors focus:border-accent disabled:cursor-not-allowed disabled:opacity-60'

interface FieldProps {
  label: ReactNode
  hint?: ReactNode
  error?: string
  required?: boolean
}

function Wrapper({ id, label, hint, error, required, children }: FieldProps & { id: string; children: ReactNode }) {
  return (
    <div className="flex flex-col gap-1.5">
      <label htmlFor={id} className="text-sm font-medium text-ink">
        {label}
        {required ? (
          <span className="ml-1 text-danger" aria-hidden="true">
            *
          </span>
        ) : null}
      </label>
      {children}
      {hint && !error ? (
        <p id={`${id}-hint`} className="text-xs text-subtle">
          {hint}
        </p>
      ) : null}
      {error ? (
        <p id={`${id}-error`} role="alert" className="text-xs text-danger">
          {error}
        </p>
      ) : null}
    </div>
  )
}

function describedBy(id: string, hint: ReactNode, error?: string): string | undefined {
  if (error) return `${id}-error`
  return hint ? `${id}-hint` : undefined
}

export function TextField({ label, hint, error, required, className = '', ...rest }: FieldProps & InputHTMLAttributes<HTMLInputElement>) {
  const id = useId()
  return (
    <Wrapper id={id} label={label} hint={hint} error={error} required={required}>
      <input
        id={id}
        required={required}
        aria-invalid={error ? true : undefined}
        aria-describedby={describedBy(id, hint, error)}
        className={`${CONTROL} h-10 ${error ? 'border-danger' : 'border-line-strong'} ${className}`}
        {...rest}
      />
    </Wrapper>
  )
}

export function TextAreaField({ label, hint, error, required, className = '', ...rest }: FieldProps & TextareaHTMLAttributes<HTMLTextAreaElement>) {
  const id = useId()
  return (
    <Wrapper id={id} label={label} hint={hint} error={error} required={required}>
      <textarea
        id={id}
        required={required}
        aria-invalid={error ? true : undefined}
        aria-describedby={describedBy(id, hint, error)}
        className={`${CONTROL} min-h-24 py-2 ${error ? 'border-danger' : 'border-line-strong'} ${className}`}
        {...rest}
      />
    </Wrapper>
  )
}

export function SelectField({ label, hint, error, required, className = '', children, ...rest }: FieldProps & SelectHTMLAttributes<HTMLSelectElement>) {
  const id = useId()
  return (
    <Wrapper id={id} label={label} hint={hint} error={error} required={required}>
      <select
        id={id}
        required={required}
        aria-invalid={error ? true : undefined}
        aria-describedby={describedBy(id, hint, error)}
        className={`${CONTROL} h-10 ${error ? 'border-danger' : 'border-line-strong'} ${className}`}
        {...rest}
      >
        {children}
      </select>
    </Wrapper>
  )
}

export function CheckboxField({ label, error, className = '', ...rest }: { label: ReactNode; error?: string } & InputHTMLAttributes<HTMLInputElement>) {
  const id = useId()
  return (
    <div className="flex flex-col gap-1">
      <label htmlFor={id} className="flex cursor-pointer items-start gap-3 text-sm text-ink">
        <input id={id} type="checkbox" aria-invalid={error ? true : undefined} className={`mt-0.5 size-4 shrink-0 accent-cyan-400 ${className}`} {...rest} />
        <span>{label}</span>
      </label>
      {error ? (
        <p role="alert" className="text-xs text-danger">
          {error}
        </p>
      ) : null}
    </div>
  )
}
