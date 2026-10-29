import type { CaseStatus } from '@/types/api'
import { STATUS_LABELS } from '@/utils/format'
import { Badge, type Tone } from './ui/Badge'

const TONES: Record<CaseStatus, Tone> = { in_progress: 'accent', under_review: 'warn', closed: 'neutral' }

export function StatusBadge({ status }: { status: CaseStatus }) {
  return <Badge tone={TONES[status]}>{STATUS_LABELS[status]}</Badge>
}
