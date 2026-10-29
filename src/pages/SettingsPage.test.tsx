import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'
import { KEYS } from '@/services/storage'
import { ADMIN, INVESTIGATOR } from '@/test/fixtures'
import { baseRoutes, mockFetch, renderApp } from '@/test/utils'

describe('Settings', () => {
  it('shows the account, the responsible-use statement and the unreviewed word lists', async () => {
    mockFetch(baseRoutes(ADMIN))
    renderApp('/settings', ADMIN)
    expect(await screen.findByText('alice')).toBeInTheDocument()
    expect(screen.getAllByText('Administrator').length).toBeGreaterThan(0) // sidebar and account card
    expect(screen.getByText('Every sketch needs human review.')).toBeInTheDocument()
    expect(screen.getByText('Hindi: NOT reviewed by a native speaker')).toBeInTheDocument()
    expect(screen.getByText(/a rule-based parser, not a trained model/)).toBeInTheDocument()
    expect(screen.getByText(/never asks for your camera, microphone or location/)).toBeInTheDocument()
    expect(screen.getByText(/Face recognition, matching and suspect search are not part of this system/)).toBeInTheDocument()
  })

  it('describes an ordinary user as an investigator', async () => {
    mockFetch(baseRoutes(INVESTIGATOR))
    renderApp('/settings', INVESTIGATOR)
    expect(await screen.findByText('Investigator', { selector: 'span' })).toBeInTheDocument()
  })

  it('remembers the default engine and language in this browser only', async () => {
    const user = userEvent.setup()
    mockFetch(baseRoutes(ADMIN))
    renderApp('/settings', ADMIN)
    await user.selectOptions(await screen.findByRole('combobox', { name: /Default language/ }), 'kn')
    await user.selectOptions(screen.getByRole('combobox', { name: 'Default sketch engine' }), 'ai')
    expect(window.localStorage.getItem(KEYS.language)).toBe('kn')
    expect(window.localStorage.getItem(KEYS.engine)).toBe('ai')
  })
})
