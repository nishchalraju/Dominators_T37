import { screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'
import { ADMIN, CASE_SUMMARY, ENGINES_NO_AI, ENGINES_WITH_AI } from '@/test/fixtures'
import { apiError, baseRoutes, mockFetch, renderApp } from '@/test/utils'

const STATS = {
  scope: 'own', total_cases: 7, status_counts: { in_progress: 4, under_review: 2, closed: 1 }, cases_with_selected_sketch: 3,
  witness_descriptions: 9, sketch_versions: 12, schematic_versions: 10, ai_versions: 2, notes: 5, recent_cases: [],
  recent_activity: [{ id: 1, action: 'case_created', summary: 'Opened case SA-2026-ABC234', case_ref: 'SA-2026-ABC234', username: 'alice', created_at: '2026-10-22T10:00:00Z' }],
}
const page = (items = [CASE_SUMMARY]) => ({ items, total: items.length, page: 1, page_size: 8 })

describe('Dashboard', () => {
  it('shows the numbers the server counted, with no invented figures', async () => {
    mockFetch({ ...baseRoutes(), 'GET /api/dashboard': STATS, 'GET /api/engines': ENGINES_WITH_AI, 'GET /api/cases': page() })
    renderApp('/', ADMIN)
    const stats = await screen.findByRole('region', { name: 'Statistics' })
    const card = (label: string) => within(stats).getByText(label).parentElement!
    expect(card('Cases')).toHaveTextContent('7')
    expect(card('In progress')).toHaveTextContent('4')
    expect(card('Under review')).toHaveTextContent('2')
    expect(card('Closed')).toHaveTextContent('1')
    expect(card('Sketch versions')).toHaveTextContent('12')
    expect(card('Sketch versions')).toHaveTextContent('10 schematic (not AI) · 2 AI-generated')
    expect(card('Witness descriptions')).toHaveTextContent('9')
    expect(card('Investigator notes')).toHaveTextContent('5')
    expect(screen.getByText('Opened case SA-2026-ABC234')).toBeInTheDocument()
  })

  it('lists cases and searches on the server after a short pause', async () => {
    const user = userEvent.setup()
    const { calls } = mockFetch({ ...baseRoutes(), 'GET /api/dashboard': STATS, 'GET /api/engines': ENGINES_NO_AI, 'GET /api/cases': page() })
    renderApp('/', ADMIN)
    expect(await screen.findByRole('link', { name: CASE_SUMMARY.title })).toBeInTheDocument()
    expect(screen.getByText(CASE_SUMMARY.case_id)).toBeInTheDocument()
    const row = screen.getByRole('link', { name: CASE_SUMMARY.title }).closest('tr')!
    expect(within(row).getByText('Test Investigator')).toBeInTheDocument() // who is investigating ...
    expect(within(row).getByText('Test Witness')).toBeInTheDocument() // ... and the witness
    expect(screen.getByText(/Search by case ID, title, investigator or witness name/)).toBeInTheDocument()
    await user.type(screen.getByRole('searchbox', { name: 'Search' }), 'market')
    await screen.findByRole('link', { name: CASE_SUMMARY.title })
    await new Promise((r) => setTimeout(r, 450))
    const searches = calls.filter((c) => c.path === '/api/cases').map((c) => new URLSearchParams(c.search).get('q'))
    expect(searches.at(-1)).toBe('market')
    expect(searches.filter((q) => q && q !== 'market')).toEqual([]) // typing does not fire one request per letter
  })

  it('has a friendly empty state for a new installation', async () => {
    mockFetch({
      ...baseRoutes(),
      'GET /api/dashboard': { ...STATS, total_cases: 0, status_counts: { in_progress: 0, under_review: 0, closed: 0 }, sketch_versions: 0, recent_activity: [] },
      'GET /api/engines': ENGINES_NO_AI,
      'GET /api/cases': page([]),
    })
    renderApp('/', ADMIN)
    expect(await screen.findByText('No cases yet')).toBeInTheDocument()
    expect(screen.getByText('Nothing has happened yet.')).toBeInTheDocument()
  })

  it('tells the user when no AI engine is set up', async () => {
    mockFetch({ ...baseRoutes(), 'GET /api/dashboard': STATS, 'GET /api/engines': ENGINES_NO_AI, 'GET /api/cases': page() })
    renderApp('/', ADMIN)
    expect(await screen.findByText('AI engines are not set up')).toBeInTheDocument()
  })

  it('shows an error with a retry button when the statistics cannot be loaded', async () => {
    const user = userEvent.setup()
    let attempts = 0
    mockFetch({
      ...baseRoutes(),
      'GET /api/dashboard': () => (++attempts === 1 ? apiError(500, 'internal_error', 'Something went wrong on the server.') : STATS),
      'GET /api/engines': ENGINES_NO_AI,
      'GET /api/cases': page(),
    })
    renderApp('/', ADMIN)
    expect(await screen.findByText('Could not load the statistics')).toBeInTheDocument()
    await user.click(screen.getAllByRole('button', { name: 'Try again' })[0]!)
    expect(await screen.findByRole('region', { name: 'Statistics' })).toBeInTheDocument()
  })
})
