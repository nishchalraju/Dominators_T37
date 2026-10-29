import type { ReactNode } from 'react'

export type Tone = 'neutral' | 'accent' | 'ok' | 'warn' | 'danger'

const TONES: Record<Tone, string> = {
  neutral: 'border-line-strong bg-raised text-muted',
  accent: 'border-accent/40 bg-accent/10 text-accent',
  ok: 'border-ok/40 bg-ok/10 text-ok',
  warn: 'border-warn/50 bg-warn/10 text-warn',
  danger: 'border-danger/50 bg-danger/10 text-danger',
}

export function Badge({ tone = 'neutral', children, className = '' }: { tone?: Tone; children: ReactNode; className?: string }) {
  return (
    <span className={`inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-xs font-medium whitespace-nowrap ${TONES[tone]} ${className}`}>{children}</span>
  )
}
