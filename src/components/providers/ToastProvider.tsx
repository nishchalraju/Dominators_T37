import { CircleAlert, CircleCheck, Info, X } from 'lucide-react'
import { useCallback, useMemo, useRef, useState, type ReactNode } from 'react'
import { ToastContext, type Toaster } from '@/hooks/toast-context'

type Kind = 'success' | 'error' | 'info'
interface Toast {
  id: number
  kind: Kind
  message: string
}

const STYLES: Record<Kind, string> = {
  success: 'border-ok/40 text-ok',
  error: 'border-danger/50 text-danger',
  info: 'border-accent/40 text-accent',
}
const ICONS = { success: CircleCheck, error: CircleAlert, info: Info }

/** Short confirmations and errors. Announced to screen readers; errors stay a little longer. */
export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([])
  const nextId = useRef(1)

  const dismiss = useCallback((id: number) => setToasts((all) => all.filter((t) => t.id !== id)), [])
  const push = useCallback(
    (kind: Kind, message: string) => {
      const id = nextId.current++
      setToasts((all) => [...all.slice(-1), { id, kind, message }])
      setTimeout(() => dismiss(id), kind === 'error' ? 9000 : 4000)
    },
    [dismiss],
  )
  const toaster = useMemo<Toaster>(
    () => ({ success: (m) => push('success', m), error: (m) => push('error', m), info: (m) => push('info', m) }),
    [push],
  )

  return (
    <ToastContext value={toaster}>
      {children}
      <div className="pointer-events-none fixed right-4 bottom-4 z-50 flex w-[min(24rem,calc(100vw-2rem))] flex-col gap-2" aria-live="polite" aria-atomic="false">
        {toasts.map((t) => {
          const Icon = ICONS[t.kind]
          return (
            <div
              key={t.id}
              role={t.kind === 'error' ? 'alert' : 'status'}
              className={`pointer-events-auto flex items-start gap-3 rounded-lg border bg-raised p-3 text-sm shadow-lg ${STYLES[t.kind]}`}
            >
              <Icon className="mt-0.5 size-4 shrink-0" aria-hidden="true" />
              <p className="min-w-0 flex-1 text-ink">{t.message}</p>
              <button type="button" onClick={() => dismiss(t.id)} className="rounded p-0.5 text-muted hover:text-ink" aria-label="Dismiss message">
                <X className="size-4" aria-hidden="true" />
              </button>
            </div>
          )
        })}
      </div>
    </ToastContext>
  )
}
