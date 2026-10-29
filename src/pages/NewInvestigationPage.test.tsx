import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'
import { ADMIN, ATTRS, CASE, DESCRIPTION, ENGINES_NO_AI, V1 } from '@/test/fixtures'
import { apiError, baseRoutes, json, mockFetch, renderApp } from '@/test/utils'
import type { ParseResponse } from '@/types/api'

const PARSED: ParseResponse = {
  attributes: { ...ATTRS },
  details: [{ attribute: 'eyebrows', value: 'thick', evidence: 'thick eyebrows', language: 'en', match_type: 'exact', note: null }],
  unrecognized: [{ text: 'scar on his cheek', reason: 'No supported facial attribute was recognised in this phrase.' }],
  conflicts: [], warnings: [], declared_language: 'en', detected_scripts: ['Latin'], parser_name: 'rule_based_multilingual', parser_version: '1.1.0',
  lexicon_status: { en: 'developer_authored', hi: 'unreviewed', kn: 'unreviewed' }, notice: 'These values are editable estimates.',
}
const TEXT = 'A man with a round face and thick eyebrows. He wears glasses and has a scar on his cheek.'

/** Fill the case form the way an investigator would (the investigator's own name is pre-filled from the account). */
async function fillCase(user: ReturnType<typeof userEvent.setup>, witness = 'Ravi Kumar') {
  await user.type(await screen.findByLabelText(/Case title/), 'Market incident')
  await user.type(screen.getByLabelText(/Investigator reference/), 'T-100')
  await user.type(screen.getByLabelText(/Witness name/), witness)
}

function routes() {
  return {
    ...baseRoutes(ADMIN),
    'POST /api/cases': () => json(CASE, 201),
    'GET /api/cases/:id': CASE,
    'POST /api/descriptions/parse': PARSED,
    'POST /api/cases/:id/descriptions': () => json(DESCRIPTION, 201),
    'GET /api/engines': ENGINES_NO_AI,
    'POST /api/sketches/generate': () => json(V1, 201),
    'GET /api/sketch-versions': { case_id: CASE.case_id, items: [V1] },
    'GET /api/cases/:id/descriptions': [DESCRIPTION],
    'GET /api/cases/:id/notes': [],
  }
}

describe('New Investigation', () => {
  it('validates the case form before calling the server', async () => {
    const user = userEvent.setup()
    const { calls } = mockFetch(routes())
    renderApp('/investigations/new', ADMIN)
    await user.click(await screen.findByRole('button', { name: 'Create case and continue' }))
    expect(await screen.findByText('Enter a title of at least 3 characters.')).toBeInTheDocument()
    expect(screen.getByText('Enter your reference or badge number.')).toBeInTheDocument()
    expect(screen.getByText('Enter the witness’s name, or a code such as W-01 if the name must be withheld.')).toBeInTheDocument()
    expect(screen.queryByText(/name of the investigator in charge/)).not.toBeInTheDocument() // pre-filled from the account
    expect(calls.some((c) => c.method === 'POST' && c.path === '/api/cases')).toBe(false)
  })

  it('pre-fills the investigator name from the signed-in account, lets it be changed, and asks for the witness name', async () => {
    const user = userEvent.setup()
    mockFetch(routes())
    renderApp('/investigations/new', ADMIN)
    const investigator = await screen.findByLabelText(/Investigator name/)
    expect(investigator).toHaveValue('Alice') // ADMIN.display_name
    expect(screen.getByLabelText(/Witness name/)).toHaveValue('')
    expect(screen.getByText(/Names are personal data/)).toBeInTheDocument()
    await user.clear(investigator)
    await user.click(screen.getByRole('button', { name: 'Create case and continue' }))
    expect(await screen.findByText('Enter the name of the investigator in charge (at least 2 characters).')).toBeInTheDocument()
  })

  it('suggests the user name when the account has no display name, and nothing for a name made only of digits', async () => {
    const withUser = (username: string) => ({ ...ADMIN, display_name: null, username }) // /api/auth/me answers with this user
    const bob = withUser('bob_second')
    mockFetch({ ...routes(), ...baseRoutes(bob) })
    const { unmount } = renderApp('/investigations/new', bob)
    expect(await screen.findByLabelText(/Investigator name/)).toHaveValue('bob_second')
    unmount()
    const digits = withUser('12345')
    mockFetch({ ...routes(), ...baseRoutes(digits) })
    renderApp('/investigations/new', digits)
    expect(await screen.findByLabelText(/Investigator name/)).toHaveValue('')
  })

  it('does not accept a one-letter witness name', async () => {
    const user = userEvent.setup()
    const { calls } = mockFetch(routes())
    renderApp('/investigations/new', ADMIN)
    await fillCase(user, 'R')
    await user.click(screen.getByRole('button', { name: 'Create case and continue' }))
    expect(await screen.findByText(/Enter the witness’s name/)).toBeInTheDocument()
    expect(calls.some((c) => c.method === 'POST' && c.path === '/api/cases')).toBe(false)
  })

  it('refuses a future incident date', async () => {
    const user = userEvent.setup()
    mockFetch(routes())
    renderApp('/investigations/new', ADMIN)
    await fillCase(user)
    const date = screen.getByLabelText(/Incident date/)
    await user.clear(date)
    await user.type(date, '2999-01-01')
    await user.click(screen.getByRole('button', { name: 'Create case and continue' }))
    expect(await screen.findByText('The incident date cannot be in the future.')).toBeInTheDocument()
  })

  it('shows server-side field errors next to the fields', async () => {
    const user = userEvent.setup()
    mockFetch({ ...routes(), 'POST /api/cases': () => json({ detail: 'Some fields are missing or invalid.', code: 'validation_error', fields: { investigator_ref: 'Use only letters, digits, spaces and - _ . / in the reference.' } }, 422) })
    renderApp('/investigations/new', ADMIN)
    await fillCase(user)
    await user.clear(screen.getByLabelText(/Investigator reference/))
    await user.type(screen.getByLabelText(/Investigator reference/), '<script>')
    await user.click(screen.getByRole('button', { name: 'Create case and continue' }))
    expect(await screen.findByText(/Use only letters, digits/)).toBeInTheDocument()
  })

  it('walks from the case, through the witness description, to the first sketch', async () => {
    const user = userEvent.setup()
    const { calls, called } = mockFetch({ ...routes(), 'GET /api/cases': { items: [], total: 0, page: 1, page_size: 8 } })
    renderApp('/investigations/new', ADMIN)

    // step 1: case details
    await user.type(await screen.findByLabelText(/Case title/), '  Market incident  ')
    await user.type(screen.getByLabelText(/Investigator reference/), 'T-100')
    await user.type(screen.getByLabelText(/Witness name/), '  Ravi Kumar ')
    await user.click(screen.getByRole('button', { name: 'Create case and continue' }))
    expect(calls.find((c) => c.method === 'POST' && c.path === '/api/cases')!.body).toMatchObject({
      title: 'Market incident', investigator_ref: 'T-100', investigator_name: 'Alice', witness_name: 'Ravi Kumar',
    })

    // step 2: the description is read, shown with evidence, reviewed, then saved with the ORIGINAL wording
    expect(await screen.findByRole('heading', { name: '2. Witness description' })).toBeInTheDocument()
    expect(screen.getByLabelText('Who gave this description')).toHaveValue(CASE.witness_name) // starts with the case's witness name
    const read = screen.getByRole('button', { name: 'Read description' })
    expect(read).toBeDisabled()
    await user.type(screen.getByLabelText(/What the witness said/), TEXT)
    await user.click(read)
    expect(await screen.findByText('“thick eyebrows”')).toBeInTheDocument()
    expect(screen.getByText('“scar on his cheek”')).toBeInTheDocument()
    await user.selectOptions(screen.getByRole('combobox', { name: /Eyebrow thickness/ }), 'medium')
    expect(screen.getByText('edited')).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Save description to the case' }))
    const saved = calls.find((c) => c.method === 'POST' && /\/descriptions$/.test(c.path))!.body as Record<string, unknown>
    await screen.findByRole('heading', { name: '3. First sketch' })
    expect(saved.original_text).toBe(TEXT)
    expect(saved.label).toBe(CASE.witness_name) // so the report names who said it
    expect((saved.confirmed_attributes as Record<string, string>).eyebrows).toBe('medium')

    // step 3: schematic engine (AI is not set up) -> generate -> workspace
    expect(await screen.findByRole('radio', { name: /AI engine/ })).toBeDisabled() // engine status loads asynchronously
    expect(await screen.findByText('The AI engine is not set up on this server')).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Generate first sketch' }))
    expect(await screen.findByRole('heading', { name: 'Sketch Workspace' })).toBeInTheDocument()
    expect(called('POST', '/api/sketches/generate')[0]!.body).toMatchObject({ case_id: CASE.case_id, description_id: DESCRIPTION.id, engine: 'schematic' })
  })

  it('lets the user skip the description and choose attributes by hand', async () => {
    const user = userEvent.setup()
    const { called } = mockFetch(routes())
    renderApp('/investigations/new', ADMIN)
    await fillCase(user)
    await user.click(screen.getByRole('button', { name: 'Create case and continue' }))
    await user.click(await screen.findByRole('button', { name: /Skip: I will choose the attributes by hand/ }))
    expect(await screen.findByText(/pick at least one attribute/)).toBeInTheDocument()
    const generate = screen.getByRole('button', { name: 'Generate first sketch' })
    expect(generate).toBeDisabled() // nothing chosen yet
    await user.selectOptions(screen.getByRole('combobox', { name: 'Face shape' }), 'square')
    expect(generate).toBeEnabled()
    await user.click(generate)
    await screen.findByRole('heading', { name: 'Sketch Workspace' })
    expect(called('POST', '/api/sketches/generate')[0]!.body).toMatchObject({ attributes: { face_shape: 'square' }, description_id: null })
  })

  it('shows why generation failed instead of pretending it worked', async () => {
    const user = userEvent.setup()
    mockFetch({ ...routes(), 'POST /api/sketches/generate': () => apiError(422, 'no_attributes', 'Choose at least one attribute before generating a sketch.') })
    renderApp('/investigations/new', ADMIN)
    await fillCase(user)
    await user.click(screen.getByRole('button', { name: 'Create case and continue' }))
    await user.click(await screen.findByRole('button', { name: /Skip: I will choose/ }))
    await user.selectOptions(await screen.findByRole('combobox', { name: 'Face shape' }), 'square')
    await user.click(screen.getByRole('button', { name: 'Generate first sketch' }))
    expect(await screen.findByText('Choose at least one attribute before generating a sketch.')).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: '3. First sketch' })).toBeInTheDocument()
  })
})
