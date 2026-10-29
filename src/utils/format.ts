import type { CaseStatus } from '@/types/api'

const dateTime = new Intl.DateTimeFormat(undefined, { dateStyle: 'medium', timeStyle: 'short' })
const dateOnly = new Intl.DateTimeFormat(undefined, { dateStyle: 'medium' })

export function formatDateTime(iso: string | null | undefined): string {
  if (!iso) return '—'
  const d = new Date(iso)
  return Number.isNaN(d.getTime()) ? '—' : dateTime.format(d)
}

/** Calendar dates (YYYY-MM-DD) have no time zone: format them without shifting the day. */
export function formatDate(iso: string | null | undefined): string {
  if (!iso) return '—'
  const match = /^(\d{4})-(\d{2})-(\d{2})/.exec(iso)
  const d = match ? new Date(Number(match[1]), Number(match[2]) - 1, Number(match[3])) : new Date(iso)
  return Number.isNaN(d.getTime()) ? '—' : dateOnly.format(d)
}

export function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

/** 0.9333 -> "93.3%"; null (undefined metric) -> "—". Never turns a missing number into 0. */
export function formatPercent(value: number | null | undefined, digits = 1): string {
  return value === null || value === undefined ? '—' : `${(value * 100).toFixed(digits)}%`
}

export const STATUS_LABELS: Record<CaseStatus, string> = {
  in_progress: 'In progress',
  under_review: 'Under review',
  closed: 'Closed',
}

export function todayIso(): string {
  const d = new Date()
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
}

export const LANGUAGE_NAMES: Record<string, string> = { en: 'English', kn: 'Kannada', hi: 'Hindi' }

export const REVIEW_LABELS: Record<string, string> = {
  developer_authored: 'written by the developer',
  unreviewed: 'NOT reviewed by a native speaker',
  reviewed: 'reviewed',
}
