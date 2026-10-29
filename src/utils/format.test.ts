import { describe, expect, it } from 'vitest'
import { formatBytes, formatDate, formatDateTime, formatPercent, todayIso } from './format'

describe('formatPercent', () => {
  it('formats a ratio as a percentage', () => {
    expect(formatPercent(0.9583)).toBe('95.8%')
    expect(formatPercent(1, 0)).toBe('100%')
  })

  it('shows a dash for an undefined metric, never 0%', () => {
    expect(formatPercent(null)).toBe('—')
    expect(formatPercent(undefined)).toBe('—')
    expect(formatPercent(0)).toBe('0.0%') // a real zero is still shown as a number
  })
})

describe('dates', () => {
  it('does not shift a calendar date across the day boundary', () => {
    expect(formatDate('2026-10-20')).toContain('20')
    expect(formatDate('2026-01-01')).toContain('1')
    expect(formatDate('2026-01-01')).toContain('2026')
  })

  it('returns a dash for missing or invalid values', () => {
    expect(formatDate(null)).toBe('—')
    expect(formatDateTime(undefined)).toBe('—')
    expect(formatDateTime('not a date')).toBe('—')
  })

  it('todayIso is YYYY-MM-DD', () => {
    expect(todayIso()).toMatch(/^\d{4}-\d{2}-\d{2}$/)
  })
})

it('formatBytes picks a sensible unit', () => {
  expect(formatBytes(512)).toBe('512 B')
  expect(formatBytes(2048)).toBe('2 KB')
  expect(formatBytes(5 * 1024 * 1024)).toBe('5.0 MB')
})
