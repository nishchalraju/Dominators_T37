import { screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'
import { ADMIN, DATASETS_EMPTY, ENGINES_NO_AI, ENGINES_WITH_AI, EVALUATION, INVESTIGATOR } from '@/test/fixtures'
import { apiError, baseRoutes, json, mockFetch, renderApp } from '@/test/utils'
import type { User } from '@/types/api'

function open(user: User = ADMIN, over: Record<string, unknown> = {}) {
  const mock = mockFetch({
    ...baseRoutes(user),
    'GET /api/engines': ENGINES_NO_AI,
    'GET /api/datasets/status': { datasets: DATASETS_EMPTY, totals: { records: 0, installed_datasets: 1 } },
    'GET /api/evaluations': [],
    ...over,
  })
  renderApp('/datasets', user)
  return mock
}

describe('Dataset and AI Evaluation: nothing is invented', () => {
  it('shows zero for datasets that are not installed, with their licence and access instructions', async () => {
    open()
    await screen.findByRole('heading', { name: 'Datasets' })
    const cufs = (await screen.findByRole('heading', { name: 'CUHK Face Sketch Database (CUFS)' })).closest('li')!
    expect(within(cufs).getByText('Not installed')).toBeInTheDocument()
    expect(within(cufs).getByText('External · restricted access')).toBeInTheDocument()
    expect(within(cufs).getByText('Files / rows found').nextElementSibling).toHaveTextContent('—') // never inspected: no number at all
    expect(within(cufs).getByText('Records stored').nextElementSibling).toHaveTextContent('0')
    expect(within(cufs).getByText(/never downloads restricted datasets/)).toBeInTheDocument()
    expect(within(cufs).getByText('Access, licence and citation')).toBeInTheDocument()
    const link = within(cufs).getByRole('link', { name: /Official source/ })
    expect(link).toHaveAttribute('href', 'https://example.org/cufs')
    expect(link).toHaveAttribute('rel', 'noopener noreferrer')
    expect(screen.getByText(/Total records stored:/).textContent).toContain('0')
  })

  it('marks the custom dataset as a synthetic demo', async () => {
    open()
    const custom = (await screen.findByRole('heading', { name: /Custom attribute dataset/ })).closest('li')!
    expect(within(custom).getByText('Installed')).toBeInTheDocument()
    expect(within(custom).getByText('Synthetic demo')).toBeInTheDocument()
  })

  it('shows every AI engine as "setup required" and "never evaluated", and the schematic engine as not AI', async () => {
    open()
    const section = (await screen.findByRole('heading', { name: 'Sketch engines' })).closest('section')!
    const card = async (name: RegExp) => (await within(section).findByRole('heading', { name })).closest('li') as HTMLElement
    const schematic = await card(/Schematic composite/)
    const hf = await card(/Hugging Face/)
    for (const name of [/OpenAI/, /Local diffusers/]) expect(within(await card(name)).getByText('Setup required')).toBeInTheDocument()
    expect(within(schematic).getByText('Ready')).toBeInTheDocument()
    expect(within(schematic).getByText('Not AI')).toBeInTheDocument()
    expect(within(hf).getByText('Setup required')).toBeInTheDocument()
    expect(within(hf).getByText('AI model')).toBeInTheDocument()
    expect(within(hf).getByText('Never evaluated')).toBeInTheDocument()
    expect(within(hf).getByText(/No token is configured/)).toBeInTheDocument()
    expect(within(hf).getByText('How to set this up')).toBeInTheDocument()
    expect(screen.getByText(/No quantitative evaluation of sketch quality exists/)).toBeInTheDocument()
  })

  it('does not claim a configured engine works until a request has succeeded', async () => {
    open(ADMIN, { 'GET /api/engines': ENGINES_WITH_AI })
    const hf = (await screen.findByRole('heading', { name: /Hugging Face/ })).closest('li')!
    expect(within(hf).getByText('Ready')).toBeInTheDocument()
    expect(within(hf).getByText(/Not yet \(no request has succeeded/)).toBeInTheDocument()
  })

  it('says n = 0 and shows no accuracy numbers before any evaluation was run', async () => {
    open()
    expect(await screen.findByText('No evaluation has been run yet (n = 0)')).toBeInTheDocument()
    expect(screen.queryByText('Exact match')).not.toBeInTheDocument()
    expect(screen.queryByText(/%/)).not.toBeInTheDocument()
  })
})

describe('Dataset and AI Evaluation: administrator actions', () => {
  it('runs an evaluation and shows n, per-language results, the word-list review status and the caveats', async () => {
    const user = userEvent.setup()
    let stored = false
    const { called } = open(ADMIN, {
      'POST /api/evaluations': () => { stored = true; return json(EVALUATION, 201) },
      'GET /api/evaluations': () => (stored ? [EVALUATION] : []),
    })
    await user.selectOptions(await screen.findByRole('combobox', { name: 'Split' }), 'dev')
    await user.click(screen.getByRole('checkbox', { name: 'Only human-reviewed translations' }))
    await user.click(screen.getByRole('button', { name: 'Run evaluation' }))
    expect(await screen.findByText('Examples (n)')).toBeInTheDocument()
    expect(called('POST', '/api/evaluations')[0]!.body).toEqual({ evaluation_type: 'description_parser', split: 'dev', only_reviewed_translations: true })
    const view = screen.getByText('Examples (n)').closest('div')!.parentElement!
    expect(within(view).getByText('72')).toBeInTheDocument()
    expect(screen.getByText('95.8%')).toBeInTheDocument() // exact match from the stored run
    const languages = screen.getByRole('table', { name: 'Results per language' })
    expect(within(languages).getByRole('row', { name: /Hindi/ })).toHaveTextContent('NOT reviewed by a native speaker')
    expect(within(languages).getByRole('row', { name: /English/ })).toHaveTextContent('24')
    expect(screen.getByText('Read these numbers with care')).toBeInTheDocument()
    expect(screen.getByText(/written by the same developer/)).toBeInTheDocument()
  })

  it('shows an undefined metric as a dash, not as 0%', async () => {
    open(ADMIN, { 'GET /api/evaluations': [EVALUATION] })
    const user = userEvent.setup()
    await user.click(await screen.findByText('Per-attribute results'))
    const row = screen.getByRole('row', { name: /Glasses/ })
    expect(row).toHaveTextContent('100.0%') // precision
    expect(row).toHaveTextContent('—') // recall was undefined
  })

  it('inspects datasets and reports what was really found', async () => {
    const user = userEvent.setup()
    const { called } = open(ADMIN, {
      'POST /api/datasets/inspect': () => json({ results: [{ dataset_key: 'cufs', installed: false, files_found: 0, valid: 0, invalid: 0, truncated: false, summary: {}, problems: [], notes: ['The folder is empty or missing: nothing is installed.'], inspected_at: '2026-10-22T11:00:00Z' }] }),
    })
    await user.click(await screen.findByRole('button', { name: 'Inspect all datasets' }))
    expect(await screen.findByText('Result of the inspection you just ran')).toBeInTheDocument()
    expect(screen.getByText(/cufs: nothing installed \(0 files\)/)).toBeInTheDocument()
    expect(called('POST', '/api/datasets/inspect')[0]!.body).toEqual({})
  })

  it('shows an evaluation error from the server', async () => {
    const user = userEvent.setup()
    open(ADMIN, { 'POST /api/evaluations': () => apiError(422, 'dataset_invalid', 'The custom dataset file is missing or invalid.') })
    await user.click(await screen.findByRole('button', { name: 'Run evaluation' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('The custom dataset file is missing or invalid.')
  })

  it('hides the admin buttons from an ordinary investigator', async () => {
    open(INVESTIGATOR, { 'GET /api/evaluations': [EVALUATION] })
    expect(await screen.findByText(/Only the administrator can run inspections/)).toBeInTheDocument()
    expect(screen.getByText(/Only the administrator can run an evaluation/)).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Run evaluation' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Inspect all datasets' })).not.toBeInTheDocument()
    expect(await screen.findByText('Examples (n)')).toBeInTheDocument() // but they can read the stored results
  })
})
