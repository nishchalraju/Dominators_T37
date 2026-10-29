import { LoaderCircle } from 'lucide-react'
import type { ButtonHTMLAttributes, ComponentType, ReactNode } from 'react'

type Variant = 'primary' | 'secondary' | 'ghost' | 'danger'
type Size = 'sm' | 'md'

const VARIANTS: Record<Variant, string> = {
  primary: 'bg-accent text-accent-ink hover:bg-accent-strong font-semibold disabled:hover:bg-accent',
  secondary: 'border border-line-strong bg-raised text-ink hover:border-accent/60 hover:bg-line',
  ghost: 'text-muted hover:bg-raised hover:text-ink',
  danger: 'border border-danger/50 bg-danger/10 text-danger hover:bg-danger/20',
}
const SIZES: Record<Size, string> = { sm: 'h-8 px-3 text-sm gap-1.5', md: 'h-10 px-4 text-sm gap-2' }

interface Props extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant
  size?: Size
  loading?: boolean
  icon?: ComponentType<{ className?: string; 'aria-hidden'?: boolean | 'true' }>
  children?: ReactNode
}

export function Button({ variant = 'secondary', size = 'md', loading = false, icon: Icon, children, className = '', disabled, type = 'button', ...rest }: Props) {
  return (
    <button
      type={type}
      disabled={disabled || loading}
      aria-busy={loading || undefined}
      className={`inline-flex shrink-0 items-center justify-center rounded-lg whitespace-nowrap transition-colors disabled:cursor-not-allowed disabled:opacity-50 ${VARIANTS[variant]} ${SIZES[size]} ${className}`}
      {...rest}
    >
      {loading ? <LoaderCircle className="size-4 animate-spin" aria-hidden="true" /> : Icon ? <Icon className="size-4" aria-hidden="true" /> : null}
      {children}
    </button>
  )
}
