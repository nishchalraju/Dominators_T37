import { screen, within } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { META } from '@/test/fixtures'
import { mockFetch, renderWithProviders } from '@/test/utils'
import type { ParseResponse } from '@/types/api'
import { ParseResultPanel } from './ParseResultPanel'

const RESULT: ParseResponse = {
  attributes: { eyebrows: 'thick', hair_length: null },
  details: [
    { attribute: 'eyebrows', value: 'thick', evidence: 'भौंहें मोटी', language: 'hi', match_type: 'exact', note: null },
    { attribute: 'apparent_gender', value: 'male', evidence: 'He', language: 'en', match_type: 'pronoun', note: "Inferred only from the pronoun 'He'." },
    { attribute: 'age_description', value: 'adult', evidence: '35 years', language: 'number', match_type: 'number', note: null },
  ],
  unrecognized: [{ text: 'scar on her left cheek', reason: 'No supported facial attribute was recognised in this phrase.' }],
  conflicts: [{ attribute: 'hair_length', values: ['short', 'long'], evidence: ['short at the sides', 'long on top'] }],
  warnings: ['The Hindi word list is an unreviewed draft (no native-speaker review yet).'],
  declared_language: 'hi',
  detected_scripts: ['Devanagari'],
  parser_name: 'rule_based_multilingual',
  parser_version: '1.1.0',
  lexicon_status: { en: 'developer_authored', hi: 'unreviewed', kn: 'unreviewed' },
  notice: 'These values are editable estimates read from the witness wording.',
}

describe('ParseResultPanel', () => {
  async function show(result = RESULT) {
    mockFetch({ 'GET /api/meta/attributes': META })
    renderWithProviders(<ParseResultPanel result={result} />)
    await screen.findByText('Understood')
  }

  it('shows each estimate next to the witness’s own words', async () => {
    await show()
    const row = screen.getByRole('row', { name: /Eyebrow thickness/ })
    expect(within(row).getByText('Thick')).toBeInTheDocument()
    expect(within(row).getByText('“भौंहें मोटी”')).toBeInTheDocument()
    expect(within(row).getByText(/Hindi word list/)).toBeInTheDocument()
  })

  it('labels weak evidence honestly (pronoun only, stated age)', async () => {
    await show()
    expect(screen.getByText(/pronoun only/)).toBeInTheDocument()
    expect(screen.getByText("Inferred only from the pronoun 'He'.")).toBeInTheDocument()
    expect(screen.getByText(/stated age/)).toBeInTheDocument()
  })

  it('lists phrases that were NOT converted instead of hiding them', async () => {
    await show()
    expect(screen.getByRole('heading', { name: /Not converted/ })).toBeInTheDocument()
    expect(screen.getByText('“scar on her left cheek”')).toBeInTheDocument()
  })

  it('shows conflicting statements and leaves the decision to the investigator', async () => {
    await show()
    expect(screen.getByText(/Conflicting statements/)).toBeInTheDocument()
    expect(screen.getByText(/Short vs Long/)).toBeInTheDocument()
  })

  it('warns that the Hindi and Kannada word lists are unreviewed', async () => {
    await show()
    expect(screen.getByText(/unreviewed draft/)).toBeInTheDocument()
    expect(screen.getByText('Hindi: NOT reviewed by a native speaker')).toBeInTheDocument()
    expect(screen.getByText('Kannada: NOT reviewed by a native speaker')).toBeInTheDocument()
    expect(screen.getByText('English: written by the developer')).toBeInTheDocument()
  })

  it('says so when nothing was understood', async () => {
    await show({ ...RESULT, details: [], conflicts: [], unrecognized: [] })
    expect(screen.getByText(/Nothing could be turned into an attribute/)).toBeInTheDocument()
    expect(screen.getByText(/Every part of the text was either understood or ignorable/)).toBeInTheDocument()
  })
})
