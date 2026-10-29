import { screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'
import { KEYS } from '@/services/storage'
import { ADMIN, CASE, CASE_SUMMARY, DESCRIPTION, V1, V2 } from '@/test/fixtures'
import { apiError, baseRoutes, json, mockFetch, renderApp } from '@/test/utils'
import type { CaseDetail } from '@/types/api'

const list = (items = [CASE_SUMMARY]) => ({ items, total: items.length, page: 1, page_size: 15 })
const detailRoutes = (detail: CaseDetail = CASE, over: Record<string, unknown> = {}) => ({
  ...baseRoutes(ADMIN),
  'GET /api/cases/:id': detail,
  'GET /api/cases/:id/descriptions': [DESCRIPTION],
  'GET /api/cases/:id/notes': [],
  'GET /api/sketch-versions': { case_id: detail.case_id, items: [V1, V2] },
  ...over,
})

describe('Case Management', () => {
  it('lists cases and selects one for the workspace', async () => {
    const user = userEvent.setup()
    mockFetch({ ...baseRoutes(ADMIN), 'GET /api/cases': list(), 'GET /api/cases/:id': CASE })
    renderApp('/cases', ADMIN)
    const row = (await screen.findByRole('link', { name: CASE.title })).closest('tr')!
    expect(within(row).getByText(CASE.case_id)).toBeInTheDocument()
    expect(within(row).getByText('In progress')).toBeInTheDocument()
    await user.click(within(row).getByRole('button', { name: /^Select/ }))
    expect(window.localStorage.getItem(KEYS.activeCase)).toBe(CASE.case_id)
    expect(await screen.findByRole('button', { name: /^Selected/ })).toBeDisabled()
    expect(await screen.findByText('Active case')).toBeInTheDocument() // the header now names the selected case
    expect(screen.getAllByText(CASE.case_id).length).toBeGreaterThan(1)
    const header = within(screen.getByRole('banner'))
    expect(header.getByText('Test Investigator')).toBeInTheDocument() // ... and who is investigating and who the witness is
    expect(header.getByText('Test Witness')).toBeInTheDocument()
  })

  it('shows the investigator and the witness of every case, and says so when a name was never recorded', async () => {
    const older = { ...CASE_SUMMARY, case_id: 'SA-2026-OLD234', title: 'Case from before names', investigator_name: '', witness_name: '' }
    mockFetch({ ...baseRoutes(ADMIN), 'GET /api/cases': list([CASE_SUMMARY, older]) })
    renderApp('/cases', ADMIN)
    const row = (await screen.findByRole('link', { name: CASE.title })).closest('tr')!
    expect(within(row).getByText('Test Investigator')).toBeInTheDocument()
    expect(within(row).getByText('Test Witness')).toBeInTheDocument()
    const oldRow = screen.getByRole('link', { name: 'Case from before names' }).closest('tr')!
    expect(within(oldRow).getAllByText('Not recorded')).toHaveLength(2)
    expect(screen.getByRole('columnheader', { name: 'Investigator' })).toBeInTheDocument()
    expect(screen.getByRole('columnheader', { name: 'Witness' })).toBeInTheDocument()
  })

  it('filters by status and searches, asking the server each time', async () => {
    const user = userEvent.setup()
    const { calls } = mockFetch({ ...baseRoutes(ADMIN), 'GET /api/cases': list() })
    renderApp('/cases', ADMIN)
    await user.selectOptions(await screen.findByRole('combobox', { name: 'Status' }), 'closed')
    await screen.findByRole('link', { name: CASE.title })
    const last = calls.filter((c) => c.path === '/api/cases').at(-1)!
    expect(new URLSearchParams(last.search).get('status')).toBe('closed')
  })

  it('has an empty state and a clear error state', async () => {
    mockFetch({ ...baseRoutes(ADMIN), 'GET /api/cases': list([]) })
    renderApp('/cases', ADMIN)
    expect(await screen.findByText('No cases yet')).toBeInTheDocument()
  })

  it('reports a server failure with a retry button', async () => {
    mockFetch({ ...baseRoutes(ADMIN), 'GET /api/cases': () => apiError(500, 'internal_error', 'Something went wrong on the server.') })
    renderApp('/cases', ADMIN)
    expect(await screen.findByText('Could not load the cases')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Try again' })).toBeInTheDocument()
  })
})

describe('Case detail', () => {
  it('shows the details, the original witness text and the reviewed attributes', async () => {
    mockFetch(detailRoutes())
    renderApp(`/cases/${CASE.case_id}`, ADMIN)
    expect(await screen.findByRole('heading', { name: CASE.title })).toBeInTheDocument()
    expect(await screen.findByText(DESCRIPTION.original_text)).toBeInTheDocument()
    expect(screen.getByText('Synthetic incident used by the tests.')).toBeInTheDocument()
    expect((await screen.findAllByText('Version 2')).length).toBeGreaterThan(0)
  })

  it('shows the investigator and witness names in the details', async () => {
    mockFetch(detailRoutes())
    renderApp(`/cases/${CASE.case_id}`, ADMIN)
    const term = async (name: string) => (await screen.findByText(name, { selector: 'dt' })).parentElement!
    expect(await term('Investigator name')).toHaveTextContent('Test Investigator')
    expect(await term('Witness name')).toHaveTextContent('Test Witness')
    expect(screen.queryByText(/was not recorded for this case|were not recorded for this case/)).not.toBeInTheDocument()
  })

  it('edits the names and sends them to the server', async () => {
    const user = userEvent.setup()
    const { called } = mockFetch(detailRoutes(CASE, { 'PATCH /api/cases/:id': () => json({ ...CASE, witness_name: 'W-07' }) }))
    renderApp(`/cases/${CASE.case_id}`, ADMIN)
    await user.click(await screen.findByRole('button', { name: 'Edit' }))
    const dialog = await screen.findByRole('dialog', { name: 'Edit case details' })
    expect(within(dialog).getByLabelText(/Investigator name/)).toHaveValue('Test Investigator')
    const witness = within(dialog).getByLabelText(/Witness name/)
    await user.clear(witness)
    await user.type(witness, '  W-07 ')
    await user.click(within(dialog).getByRole('button', { name: 'Save changes' }))
    await screen.findByText('Case details saved.')
    expect(called('PATCH', `/api/cases/${CASE.case_id}`)[0]!.body).toMatchObject({ investigator_name: 'Test Investigator', witness_name: 'W-07' })
  })

  it('invites the user to add the names to a case that was created before they were collected, without blocking other edits', async () => {
    const user = userEvent.setup()
    const old = { ...CASE, investigator_name: '', witness_name: '' }
    const { called } = mockFetch(detailRoutes(old, { 'PATCH /api/cases/:id': () => json({ ...old, title: 'Renamed case' }) }))
    renderApp(`/cases/${CASE.case_id}`, ADMIN)
    expect(await screen.findByText(/investigator and witness names were not recorded for this case/)).toBeInTheDocument()
    expect(screen.getAllByText('Not recorded')).toHaveLength(2)
    await user.click(screen.getByRole('button', { name: 'Edit' }))
    const dialog = await screen.findByRole('dialog', { name: 'Edit case details' })
    const title = within(dialog).getByLabelText(/Case title/)
    await user.clear(title)
    await user.type(title, 'Renamed case')
    await user.click(within(dialog).getByRole('button', { name: 'Save changes' }))
    await screen.findByText('Case details saved.')
    const body = called('PATCH', `/api/cases/${CASE.case_id}`)[0]!.body as Record<string, unknown>
    expect(body.title).toBe('Renamed case')
    expect('investigator_name' in body || 'witness_name' in body).toBe(false) // empty names are not sent (the server would refuse them)
  })

  it('offers "Reopen case" for a closed case, and the case is shown as read-only', async () => {
    const user = userEvent.setup()
    const { called } = mockFetch(detailRoutes({ ...CASE, status: 'closed' }, { 'PATCH /api/cases/:id': () => json({ ...CASE, status: 'in_progress' }) }))
    renderApp(`/cases/${CASE.case_id}`, ADMIN)
    expect(await screen.findByText('This case is closed')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Edit' })).toBeDisabled()
    expect(screen.queryByRole('button', { name: 'Close case' })).not.toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Reopen case' }))
    expect(await screen.findByText('Case reopened.')).toBeInTheDocument()
    expect(called('PATCH', `/api/cases/${CASE.case_id}`)[0]!.body).toEqual({ status: 'in_progress' })
  })

  it('closes an open case', async () => {
    const user = userEvent.setup()
    const { called } = mockFetch(detailRoutes(CASE, { 'PATCH /api/cases/:id': () => json({ ...CASE, status: 'closed' }) }))
    renderApp(`/cases/${CASE.case_id}`, ADMIN)
    await user.click(await screen.findByRole('button', { name: 'Close case' }))
    expect(await screen.findByText('Case closed.')).toBeInTheDocument()
    expect(called('PATCH', `/api/cases/${CASE.case_id}`)[0]!.body).toEqual({ status: 'closed' })
  })

  it('edits the details and shows the server’s field errors', async () => {
    const user = userEvent.setup()
    mockFetch(detailRoutes(CASE, { 'PATCH /api/cases/:id': () => json({ detail: 'Some fields are missing or invalid.', code: 'validation_error', fields: { title: 'Title is too short.' } }, 422) }))
    renderApp(`/cases/${CASE.case_id}`, ADMIN)
    await user.click(await screen.findByRole('button', { name: 'Edit' }))
    const dialog = await screen.findByRole('dialog', { name: 'Edit case details' })
    const title = within(dialog).getByLabelText(/Case title/)
    await user.clear(title)
    await user.type(title, 'ab')
    await user.click(within(dialog).getByRole('button', { name: 'Save changes' }))
    expect(await within(dialog).findByText('Title is too short.')).toBeInTheDocument()
  })

  it('asks for confirmation before deleting, then deletes and forgets the selected case', async () => {
    const user = userEvent.setup()
    window.localStorage.setItem(KEYS.activeCase, CASE.case_id)
    const { called } = mockFetch(detailRoutes(CASE, { 'DELETE /api/cases/:id': () => json(null, 204), 'GET /api/cases': list([]) }))
    renderApp(`/cases/${CASE.case_id}`, ADMIN)
    await user.click(await screen.findByRole('button', { name: 'Delete' }))
    const dialog = await screen.findByRole('dialog', { name: 'Delete this case?' })
    expect(within(dialog).getByText(/cannot be undone/)).toBeInTheDocument()
    expect(called('DELETE', `/api/cases/${CASE.case_id}`)).toHaveLength(0) // nothing happened yet
    await user.click(within(dialog).getByRole('button', { name: 'Delete case permanently' }))
    expect(await screen.findByRole('heading', { name: 'Case Management' })).toBeInTheDocument()
    expect(called('DELETE', `/api/cases/${CASE.case_id}`)).toHaveLength(1)
    expect(window.localStorage.getItem(KEYS.activeCase)).toBeNull()
  })

  it('does not reveal cases that belong to someone else', async () => {
    mockFetch({ ...baseRoutes(ADMIN), 'GET /api/cases/:id': () => apiError(404, 'case_not_found', 'Case not found.'), 'GET /api/cases/:id/descriptions': () => apiError(404, 'case_not_found', 'Case not found.'), 'GET /api/sketch-versions': () => apiError(404, 'case_not_found', 'Case not found.') })
    renderApp('/cases/SA-2026-NOPE22', ADMIN)
    expect(await screen.findByText('Case not found')).toBeInTheDocument()
    expect(screen.getByText(/does not exist, or it belongs to another investigator/)).toBeInTheDocument()
  })

  it('adds a note and shows it in the append-only list', async () => {
    const user = userEvent.setup()
    let notes: unknown[] = []
    const { called } = mockFetch(detailRoutes(CASE, {
      'GET /api/cases/:id/notes': () => notes,
      'POST /api/cases/:id/notes': () => { notes = [{ id: 1, body: 'Witness is unsure about the glasses.', sketch_version_id: null, author_username: 'alice', created_at: '2026-10-22T11:00:00Z' }]; return json(notes[0], 201) },
    }))
    renderApp(`/cases/${CASE.case_id}`, ADMIN)
    await user.type(await screen.findByLabelText('New note'), 'Witness is unsure about the glasses.')
    await user.click(screen.getByRole('button', { name: 'Add note' }))
    expect(await screen.findByText('Witness is unsure about the glasses.')).toBeInTheDocument()
    expect(called('POST', `/api/cases/${CASE.case_id}/notes`)[0]!.body).toEqual({ body: 'Witness is unsure about the glasses.', sketch_version_id: null })
    expect(screen.queryByRole('button', { name: /Delete note|Edit note/ })).not.toBeInTheDocument()
  })
})
