import { CircleAlert, CircleCheck, Info, LoaderCircle, TriangleAlert } from 'lucide-react'
import type { ComponentType, ReactNode } from 'react'
import { Button } from './Button'

export function Spinner({ label = 'Loading' }: { label?: string }) {
  return (
    <span role="status" className="inline-flex items-center gap-2 text-sm text-muted">
      <LoaderCircle className="size-4 animate-spin" aria-hidden="true" />
      <span>{label}…</span>
    </span>
  )
}

export function LoadingBlock({ label = 'Loading' }: { label?: string }) {
  return (
    <div className="flex items-center justify-center py-12">
      <Spinner label={label} />
    </div>
  )
}

export function Skeleton({ className = '' }: { className?: string }) {
  return <div aria-hidden="true" className={`rounded-md bg-raised ${className}`} />
}

interface EmptyProps {
  icon?: ComponentType<{ className?: string; 'aria-hidden'?: boolean | 'true' }>
  title: string
  children?: ReactNode
  action?: ReactNode
}

export function EmptyState({ icon: Icon = Info, title, children, action }: EmptyProps) {
  return (
    <div className="flex flex-col items-center gap-3 px-6 py-12 text-center">
      <span className="rounded-full border border-line-strong bg-raised p-3 text-accent">
        <Icon className="size-5" aria-hidden="true" />
      </span>
      <h3 className="text-base font-semibold text-ink">{title}</h3>
      {children ? <div className="max-w-md text-sm text-muted">{children}</div> : null}
      {action}
    </div>
  )
}

export function ErrorState({ message, onRetry, title = 'Something went wrong' }: { message: string; onRetry?: () => void; title?: string }) {
  return (
    <div role="alert" className="flex flex-col items-center gap-3 px-6 py-10 text-center">
      <span className="rounded-full border border-danger/40 bg-danger/10 p-3 text-danger">
        <CircleAlert className="size-5" aria-hidden="true" />
      </span>
      <h3 className="text-base font-semibold text-ink">{title}</h3>
      <p className="max-w-md text-sm text-muted">{message}</p>
      {onRetry ? (
        <Button onClick={onRetry} size="sm">
          Try again
        </Button>
      ) : null}
    </div>
  )
}

type NoticeTone = 'info' | 'warn' | 'danger' | 'ok'
const NOTICE: Record<NoticeTone, { box: string; icon: ComponentType<{ className?: string; 'aria-hidden'?: boolean | 'true' }> }> = {
  info: { box: 'border-accent/30 bg-accent/5 text-ink', icon: Info },
  warn: { box: 'border-warn/40 bg-warn/5 text-ink', icon: TriangleAlert },
  danger: { box: 'border-danger/40 bg-danger/5 text-ink', icon: CircleAlert },
  ok: { box: 'border-ok/40 bg-ok/5 text-ink', icon: CircleCheck },
}
const NOTICE_ICON_COLOR: Record<NoticeTone, string> = { info: 'text-accent', warn: 'text-warn', danger: 'text-danger', ok: 'text-ok' }

export function Notice({ tone = 'info', title, children, className = '' }: { tone?: NoticeTone; title?: string; children: ReactNode; className?: string }) {
  const { box, icon: Icon } = NOTICE[tone]
  return (
    <div role={tone === 'danger' ? 'alert' : 'note'} className={`flex gap-3 rounded-lg border p-3 text-sm ${box} ${className}`}>
      <Icon className={`mt-0.5 size-4 shrink-0 ${NOTICE_ICON_COLOR[tone]}`} aria-hidden="true" />
      <div className="min-w-0 flex-1">
        {title ? <p className="font-semibold">{title}</p> : null}
        <div className={title ? 'mt-0.5 text-muted' : 'text-muted'}>{children}</div>
      </div>
    </div>
  )
}
