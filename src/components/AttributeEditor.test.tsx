import { screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { useState } from 'react'
import { describe, expect, it, vi } from 'vitest'
import { META } from '@/test/fixtures'
import { mockFetch, renderWithProviders } from '@/test/utils'
import type { Attributes } from '@/types/api'
import { AttributeEditor } from './AttributeEditor'

function Harness({ initial, baseline }: { initial: Attributes; baseline?: Attributes }) {
  const [value, setValue] = useState(initial)
  return <AttributeEditor value={value} onChange={setValue} baseline={baseline} additionalDetails="" onAdditionalDetailsChange={() => undefined} />
}

describe('AttributeEditor', () => {
  it('offers exactly the backend vocabulary, plus "Not specified"', async () => {
    mockFetch({ 'GET /api/meta/attributes': META })
    renderWithProviders(<Harness initial={{}} />)
    const face = await screen.findByRole('combobox', { name: 'Face shape' })
    const options = within(face).getAllByRole('option').map((o) => o.textContent)
    expect(options).toEqual(['Not specified', 'Oval', 'Round', 'Square'])
    expect(screen.getAllByRole('combobox')).toHaveLength(META.attributes.length)
  })

  it('shows the current values and lets the user change one', async () => {
    const user = userEvent.setup()
    mockFetch({ 'GET /api/meta/attributes': META })
    renderWithProviders(<Harness initial={{ eyebrows: 'thin' }} />)
    const brows = await screen.findByRole('combobox', { name: 'Eyebrow thickness' })
    expect(brows).toHaveValue('thin')
    await user.selectOptions(brows, 'thick')
    expect(brows).toHaveValue('thick')
    await user.selectOptions(brows, '')
    expect(brows).toHaveValue('')
  })

  it('marks values that differ from the parser output as edited and can reset them', async () => {
    const user = userEvent.setup()
    mockFetch({ 'GET /api/meta/attributes': META })
    renderWithProviders(<Harness initial={{ face_shape: 'round' }} baseline={{ face_shape: 'round' }} />)
    const face = await screen.findByRole('combobox', { name: /Face shape/ })
    expect(screen.queryByText('edited')).not.toBeInTheDocument()
    const reset = screen.getByRole('button', { name: 'Reset to parsed values' })
    expect(reset).toBeDisabled()

    await user.selectOptions(face, 'square')
    expect(screen.getByText('edited')).toBeInTheDocument()
    expect(reset).toBeEnabled()

    await user.click(reset)
    expect(face).toHaveValue('round')
    expect(screen.queryByText('edited')).not.toBeInTheDocument()
  })

  it('offers the skin colours white, brown and black with a chip showing the colour that will be drawn', async () => {
    const user = userEvent.setup()
    mockFetch({ 'GET /api/meta/attributes': META })
    const { container } = renderWithProviders(<Harness initial={{}} />)
    const skin = await screen.findByRole('combobox', { name: 'Skin colour' })
    expect(within(skin).getAllByRole('option').map((o) => o.textContent)).toEqual(['Not specified', 'White / fair', 'Brown / wheatish', 'Black / dark'])
    const chip = () => container.querySelector('[data-swatch]') as HTMLElement
    expect(chip().dataset.swatch).toBe('') // nothing chosen: a neutral dashed circle, not a colour
    await user.selectOptions(skin, 'brown')
    expect(chip().dataset.swatch).toBe('#B9825A')
    expect(chip().style.backgroundColor).not.toBe('')
    await user.selectOptions(skin, 'black')
    expect(chip().dataset.swatch).toBe('#704C3A')
    expect(chip()).toHaveAttribute('aria-hidden', 'true') // decorative: the selected option already says the value
    expect(container.querySelectorAll('[data-swatch]')).toHaveLength(1) // only attributes with colours get a chip
  })

  it('explains that the free-text field is only used by AI engines', async () => {
    mockFetch({ 'GET /api/meta/attributes': META })
    renderWithProviders(<Harness initial={{}} />)
    expect(await screen.findByText(/Only AI engines use this text/)).toBeInTheDocument()
    expect(vi.isMockFunction(fetch)).toBe(true)
  })
})
