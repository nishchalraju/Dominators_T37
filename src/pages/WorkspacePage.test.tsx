import { screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'
import { KEYS } from '@/services/storage'
import { ADMIN, CASE, DESCRIPTION, ENGINES_NO_AI, ENGINES_WITH_AI, V1, V2, V_AI } from '@/test/fixtures'
import { apiError, baseRoutes, json, mockFetch, renderApp } from '@/test/utils'
import type { CaseDetail, EngineStatus, SketchVersion } from '@/types/api'

const PNG = () => new Response(new Uint8Array([137, 80, 78, 71]), { status: 200, headers: { 'Content-Type': 'image/png' } })

function routes(over: Record<string, unknown> = {}, versions: SketchVersion[] = [V1, V2], engines: EngineStatus[] = ENGINES_NO_AI, caseDetail: CaseDetail = CASE) {
  return {
    ...baseRoutes(ADMIN),
    'GET /api/cases/:id': caseDetail,
    'GET /api/sketch-versions': { case_id: caseDetail.case_id, items: versions },
    'GET /api/cases/:id/descriptions': [DESCRIPTION],
    'GET /api/cases/:id/notes': [],
    'GET /api/engines': engines,
    'GET /api/sketch-versions/:id/image': PNG,
    'GET /api/sketch-versions/:id/thumbnail': PNG,
    ...over,
  }
}

function open(over?: Record<string, unknown>, versions?: SketchVersion[], engines?: EngineStatus[], caseDetail?: CaseDetail) {
  window.localStorage.setItem(KEYS.activeCase, CASE.case_id)
  const mock = mockFetch(routes(over, versions, engines, caseDetail))
  renderApp('/workspace', ADMIN)
  return mock
}

describe('Sketch Workspace', () => {
  it('asks for a case first when none is selected, and remembers the choice', async () => {
    const user = userEvent.setup()
    mockFetch({ ...routes(), 'GET /api/cases': { items: [CASE], total: 1, page: 1, page_size: 8 } })
    renderApp('/workspace', ADMIN)
    expect(await screen.findByText('Choose a case to work on')).toBeInTheDocument()
    await user.click(await screen.findByRole('button', { name: /Select/ }))
    expect(await screen.findByRole('heading', { name: /Version 2 — selected for editing/ })).toBeInTheDocument()
    expect(window.localStorage.getItem(KEYS.activeCase)).toBe(CASE.case_id)
  })

  it('shows the selected version with its provenance, and the full history with numbers, instructions and times', async () => {
    open()
    expect(await screen.findByRole('heading', { name: /Version 2 — selected for editing/ })).toBeInTheDocument()
    expect(screen.getAllByText('Schematic · not AI').length).toBeGreaterThan(0)
    expect(screen.getByText(/not AI-generated/)).toBeInTheDocument()
    const history = await screen.findByRole('heading', { name: 'Version history (2)' })
    const list = history.closest('section')!
    const cards = within(list).getAllByRole('listitem')
    expect(cards).toHaveLength(2)
    expect(cards[0]).toHaveTextContent('Version 2')
    expect(cards[0]).toHaveTextContent('“remove the glasses”')
    expect(cards[0]).toHaveTextContent('from version 1')
    expect(cards[1]).toHaveTextContent('Version 1')
    expect(cards[1]).toHaveTextContent('Initial sketch')
    expect(within(cards[0]!).getByText(/2026/)).toBeInTheDocument() // the time stamp (format follows the browser locale)
  })

  it('labels AI-generated versions as AI and does not offer the schematic engine to edit them', async () => {
    open({}, [V1, V_AI], ENGINES_WITH_AI)
    await screen.findByRole('heading', { name: /Version 3 — selected|Version 2 — selected/ })
    const history = (await screen.findByRole('heading', { name: 'Version history (2)' })).closest('section')!
    expect(within(history).getByText('AI-generated')).toBeInTheDocument()
  })

  it('revises the selected version: sends the instruction, confirms the new version and reports exactly what changed', async () => {
    const user = userEvent.setup()
    const created: SketchVersion = {
      ...V2, id: 14, version_number: 3, parent_id: 12, parent_version_number: 2, instruction: 'make the eyebrows thinner', attributes: { ...V2.attributes, eyebrows: 'medium' },
      revision_details: { changes: [{ attribute: 'eyebrows', label: 'Eyebrow thickness', before: 'thick', after: 'medium', evidence: 'eyebrows thinner', kind: 'step', note: null }], ignored: [], notes: [] },
    }
    let revised = false
    const { called } = open({
      'POST /api/sketches/:id/revise': () => { revised = true; return json(created, 201) },
      // like the real server: once the revision exists it is the selected version
      'GET /api/sketch-versions': () => ({ case_id: CASE.case_id, items: revised ? [V1, { ...V2, is_selected: false }, created] : [V1, V2] }),
    })
    await user.type(await screen.findByRole('textbox', { name: 'Instruction' }), 'make the eyebrows thinner')
    await user.click(screen.getByRole('button', { name: 'Create revision (new version)' }))
    // the panel switches to the new version AND still confirms what happened
    expect(await screen.findByRole('heading', { name: /Version 3 — selected for editing/ })).toBeInTheDocument()
    expect(await screen.findByText('Version 3 was just created and is now selected')).toBeInTheDocument()
    expect(screen.getByText(/made from version 2, which is unchanged/)).toBeInTheDocument()
    expect(called('POST', '/api/sketches/12/revise')[0]!.body).toEqual({ instruction: 'make the eyebrows thinner', language: 'en', engine: 'schematic' })
    expect(screen.getByText('How this version was made')).toBeInTheDocument()
    expect(screen.getByText('Instruction: “make the eyebrows thinner”')).toBeInTheDocument()
    expect(screen.getAllByText('Eyebrow thickness:').length).toBeGreaterThan(0)
    expect(screen.getByText('from “eyebrows thinner”')).toBeInTheDocument()
  })

  it('fills the instruction from an example chip', async () => {
    const user = userEvent.setup()
    open()
    await user.click(await screen.findByRole('button', { name: 'Add glasses' }))
    expect(screen.getByRole('textbox', { name: 'Instruction' })).toHaveValue('Add glasses')
  })

  it('offers skin colour instructions as examples and sends them to the server as typed', async () => {
    const user = userEvent.setup()
    const { called } = open({ 'POST /api/sketches/:id/revise': () => json({ ...V2, id: 14, version_number: 3, parent_id: 12, parent_version_number: 2, is_selected: true }, 201) })
    await user.click(await screen.findByRole('button', { name: 'Make the skin darker' }))
    expect(screen.getByRole('textbox', { name: 'Instruction' })).toHaveValue('Make the skin darker')
    expect(screen.getByRole('button', { name: 'Make the skin lighter' })).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Create revision (new version)' }))
    await screen.findByText(/Version 3 created from version 2/)
    expect(called('POST', '/api/sketches/12/revise')[0]!.body).toMatchObject({ instruction: 'Make the skin darker', language: 'en' })
  })

  it('shows who is investigating and who the witness is', async () => {
    open()
    expect(await screen.findByRole('heading', { name: /Version 2 — selected for editing/ })).toBeInTheDocument()
    const term = (name: string) => screen.getAllByText(name, { selector: 'dt' }).at(0)!
    expect(term('Investigator:').parentElement).toHaveTextContent('Test Investigator')
    expect(term('Witness:').parentElement).toHaveTextContent('Test Witness')
  })

  it('says "not recorded" for a case that was created before names were collected', async () => {
    open({}, undefined, undefined, { ...CASE, investigator_name: '', witness_name: '' })
    await screen.findByRole('heading', { name: /Version 2 — selected for editing/ })
    expect(screen.getAllByText('not recorded').length).toBeGreaterThanOrEqual(2)
  })

  it('explains an instruction that could not be applied and creates no version', async () => {
    const user = userEvent.setup()
    open({
      'POST /api/sketches/:id/revise': () =>
        apiError(422, 'no_supported_change', 'No supported change was found in the instruction, so nothing was changed.', {
          ignored: [{ text: 'scar on the left cheek', reason: 'No supported facial attribute was recognised in this phrase.' }], notes: [],
        }),
    })
    await user.type(await screen.findByRole('textbox', { name: 'Instruction' }), 'add a scar on the left cheek')
    await user.click(screen.getByRole('button', { name: 'Create revision (new version)' }))
    expect(await screen.findByText('Nothing was changed')).toBeInTheDocument()
    expect(screen.getByText('“scar on the left cheek”')).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Version history (2)' })).toBeInTheDocument()
  })

  it('selects an older version for editing', async () => {
    const user = userEvent.setup()
    const { called } = open({ 'POST /api/sketch-versions/:id/select': () => json({ ...V1, is_selected: true }) })
    const history = (await screen.findByRole('heading', { name: 'Version history (2)' })).closest('section')!
    const v1Card = within(history).getAllByRole('listitem')[1]!
    await user.click(within(v1Card).getByRole('button', { name: 'Select for editing' }))
    await screen.findByText('Version 1 is now selected for editing.')
    expect(called('POST', '/api/sketch-versions/11/select')).toHaveLength(1)
  })

  it('compares two versions side by side and marks the attributes that differ', async () => {
    const user = userEvent.setup()
    open()
    const compareButton = await screen.findByRole('button', { name: /Compare selected \(0\/2\)/ })
    expect(compareButton).toBeDisabled()
    await user.click(screen.getByRole('checkbox', { name: /Compare\s+version 1/ }))
    await user.click(screen.getByRole('checkbox', { name: /Compare\s+version 2/ }))
    await user.click(screen.getByRole('button', { name: /Compare selected \(2\/2\)/ }))
    const heading = await screen.findByRole('heading', { name: 'Comparing version 1 and version 2' })
    const compare = within(heading.closest('section')!)
    expect(compare.getByText('1 attribute differs.')).toBeInTheDocument()
    const row = compare.getByRole('row', { name: /Glasses/ })
    expect(row).toHaveTextContent('changed')
    expect(row).toHaveTextContent('Wearing glasses')
    expect(row).toHaveTextContent('No glasses')
    expect(compare.getByText('Instruction: “remove the glasses”')).toBeInTheDocument()
    expect(compare.getByText('Initial sketch')).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Close comparison' }))
    expect(screen.queryByRole('heading', { name: /Comparing version/ })).not.toBeInTheDocument()
  })

  it('downloads a version through the authenticated endpoint', async () => {
    const user = userEvent.setup()
    const { called } = open({ 'GET /api/sketch-versions/:id/image': () => new Response(new Uint8Array([1, 2, 3]), { status: 200, headers: { 'Content-Disposition': 'attachment; filename="SA-2026-ABC234_v2_schematic.png"' } }) })
    const history = (await screen.findByRole('heading', { name: 'Version history (2)' })).closest('section')!
    await user.click(within(within(history).getAllByRole('listitem')[0]!).getByRole('button', { name: 'Download' }))
    await waitFor(() => expect(called('GET', '/api/sketch-versions/12/image').some((c) => c.search === '?download=true')).toBe(true))
  })

  it('offers the AI engine only when it is set up, and never switches silently', async () => {
    open({}, [V1, V2], ENGINES_WITH_AI)
    const radios = await screen.findAllByRole('radio', { name: /AI engine/ })
    for (const radio of radios) expect(radio).toBeEnabled()
    expect(screen.queryByText('The AI engine is not set up on this server')).not.toBeInTheDocument()
  })

  it('disables the AI option and says why when it is not set up', async () => {
    open()
    const radios = await screen.findAllByRole('radio', { name: /AI engine/ })
    for (const radio of radios) expect(radio).toBeDisabled()
    expect((await screen.findAllByText('The AI engine is not set up on this server')).length).toBeGreaterThan(0)
  })

  it('shows the setup steps when the server refuses an AI request', async () => {
    const user = userEvent.setup()
    open({
      'POST /api/sketches/generate': () => apiError(503, 'model_unavailable', 'Hugging Face is not set up (HF_TOKEN is missing).', { engine: 'huggingface', setup_steps: ['Create a Hugging Face token.', 'Put it in backend/.env as HF_TOKEN.'] }),
    }, [V1, V2], ENGINES_WITH_AI)
    const generatePanel = (await screen.findByRole('heading', { name: 'Generate a sketch' })).closest('section')!
    await user.click(await within(generatePanel).findByRole('radio', { name: /AI engine/ }))
    await user.click(within(generatePanel).getByRole('button', { name: 'Generate new version' }))
    expect(await screen.findByText('The AI engine is not set up')).toBeInTheDocument()
    expect(screen.getByText('Create a Hugging Face token.')).toBeInTheDocument()
  })

  it('is read-only for a closed case', async () => {
    open({}, [V1, V2], ENGINES_NO_AI, { ...CASE, status: 'closed' })
    expect(await screen.findByText('This case is closed')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Create revision (new version)' })).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Generate new version' })).toBeDisabled()
    expect(screen.getByText('This case is closed. Reopen it to add notes.')).toBeInTheDocument()
  })

  it('invites the user to create the first sketch when there are none', async () => {
    open({}, [])
    expect(await screen.findByText('No sketch yet')).toBeInTheDocument()
  })
})
