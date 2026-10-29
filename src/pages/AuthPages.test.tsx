import { screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'
import { ADMIN, CASE_SUMMARY, ENGINES_NO_AI, META } from '@/test/fixtures'
import { apiError, baseRoutes, json, mockFetch, renderApp } from '@/test/utils'
import { KEYS } from '@/services/storage'

const dashboardRoutes = {
  'GET /api/dashboard': {
    scope: 'own', total_cases: 1, status_counts: { in_progress: 1, under_review: 0, closed: 0 }, cases_with_selected_sketch: 0,
    witness_descriptions: 0, sketch_versions: 0, schematic_versions: 0, ai_versions: 0, notes: 0, recent_cases: [], recent_activity: [],
  },
  'GET /api/engines': ENGINES_NO_AI,
  'GET /api/cases': { items: [CASE_SUMMARY], total: 1, page: 1, page_size: 8 },
}

describe('route protection', () => {
  it('sends a signed-out visitor to the login page', async () => {
    mockFetch({ 'GET /api/meta/attributes': META })
    renderApp('/cases')
    expect(await screen.findByRole('heading', { name: 'Sign in' })).toBeInTheDocument()
    expect(screen.getByText(/does not identify people/)).toBeInTheDocument()
  })

  it('shows every section of the application to a signed-in user', async () => {
    mockFetch({ ...baseRoutes(), ...dashboardRoutes })
    renderApp('/', ADMIN)
    const nav = await screen.findByRole('navigation', { name: 'Main' })
    for (const label of ['Dashboard', 'New Investigation', 'Case Management', 'Sketch Workspace', 'Dataset and AI Evaluation', 'Reports', 'Settings']) {
      expect(within(nav).getByRole('link', { name: label })).toBeInTheDocument()
    }
    expect(within(nav).getByRole('link', { name: 'Dashboard' })).toHaveAttribute('aria-current', 'page')
  })

  it('shows a helpful page for unknown addresses', async () => {
    mockFetch({ ...baseRoutes(), ...dashboardRoutes })
    renderApp('/no/such/page', ADMIN)
    expect(await screen.findByText('This page does not exist')).toBeInTheDocument()
  })

  it('returns to the login page with a notice when the session expires', async () => {
    mockFetch({
      ...baseRoutes(),
      ...dashboardRoutes,
      'GET /api/dashboard': () => apiError(401, 'invalid_token', 'Your session is invalid or has expired. Please log in again.'),
    })
    renderApp('/', ADMIN)
    expect(await screen.findByText('Your session has expired. Please sign in again.')).toBeInTheDocument()
    expect(window.localStorage.getItem(KEYS.token)).toBeNull()
  })
})

describe('Login', () => {
  it('asks for both fields without calling the server', async () => {
    const user = userEvent.setup()
    const { calls } = mockFetch({ 'GET /api/meta/attributes': META })
    renderApp('/login')
    await user.click(await screen.findByRole('button', { name: 'Sign in' }))
    expect(await screen.findByText('Enter your username and password.')).toBeInTheDocument()
    expect(calls.some((c) => c.path === '/api/auth/login')).toBe(false)
  })

  it('shows the server’s message for wrong credentials and stays on the page', async () => {
    const user = userEvent.setup()
    mockFetch({ 'GET /api/meta/attributes': META, 'POST /api/auth/login': () => apiError(401, 'invalid_credentials', 'Incorrect username or password.') })
    renderApp('/login')
    await user.type(await screen.findByLabelText(/Username/), 'alice')
    await user.type(screen.getByLabelText(/Password/), 'wrong-password')
    await user.click(screen.getByRole('button', { name: 'Sign in' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('Incorrect username or password.')
    expect(screen.getByRole('heading', { name: 'Sign in' })).toBeInTheDocument()
  })

  it('signs in, remembers the token and opens the dashboard', async () => {
    const user = userEvent.setup()
    const { calls } = mockFetch({
      'GET /api/meta/attributes': META,
      'POST /api/auth/login': () => json({ access_token: 'tok-1', token_type: 'bearer', expires_in: 28800, user: ADMIN }),
      ...dashboardRoutes,
    })
    renderApp('/login')
    await user.type(await screen.findByLabelText(/Username/), ' Alice ')
    await user.type(screen.getByLabelText(/Password/), 'correct-horse-9')
    await user.click(screen.getByRole('button', { name: 'Sign in' }))
    expect(await screen.findByRole('heading', { name: 'Dashboard' })).toBeInTheDocument()
    expect(window.localStorage.getItem(KEYS.token)).toBe('tok-1')
    expect(calls.find((c) => c.path === '/api/auth/login')!.body).toEqual({ username: 'Alice', password: 'correct-horse-9' })
    expect(calls.find((c) => c.path === '/api/dashboard')!.headers.get('Authorization')).toBe('Bearer tok-1')
  })

  it('signing out forgets the token and the selected case', async () => {
    const user = userEvent.setup()
    window.localStorage.setItem(KEYS.activeCase, CASE_SUMMARY.case_id)
    mockFetch({ ...baseRoutes(), ...dashboardRoutes, 'GET /api/cases/:id': CASE_SUMMARY })
    renderApp('/', ADMIN)
    await user.click((await screen.findAllByRole('button', { name: 'Sign out' }))[0]!)
    expect(await screen.findByRole('heading', { name: 'Sign in' })).toBeInTheDocument()
    expect(window.localStorage.getItem(KEYS.token)).toBeNull()
    expect(window.localStorage.getItem(KEYS.activeCase)).toBeNull()
  })
})

describe('Register', () => {
  async function open() {
    const user = userEvent.setup()
    const mock = mockFetch({
      'GET /api/meta/attributes': META,
      'POST /api/auth/register': () => json({ access_token: 'tok-2', token_type: 'bearer', expires_in: 1, user: ADMIN }, 201),
      ...dashboardRoutes,
    })
    renderApp('/register')
    await screen.findByRole('heading', { name: 'Create an account' })
    return { user, ...mock }
  }

  it('shows the responsible-use statement and requires acceptance', async () => {
    const { user, calls } = await open()
    expect(screen.getByText('Every sketch needs human review.')).toBeInTheDocument()
    await user.type(screen.getByLabelText(/Username/), 'alice')
    await user.type(screen.getByLabelText(/^Password/), 'correct-horse-9')
    await user.type(screen.getByLabelText(/Repeat password/), 'correct-horse-9')
    await user.click(screen.getByRole('button', { name: 'Create account' }))
    expect(await screen.findByText(/must accept the responsible-use statement/)).toBeInTheDocument()
    expect(calls.some((c) => c.path === '/api/auth/register')).toBe(false)
  })

  it('checks username, password length and confirmation before calling the server', async () => {
    const { user, calls } = await open()
    await user.type(screen.getByLabelText(/Username/), 'a!')
    await user.type(screen.getByLabelText(/^Password/), 'short')
    await user.type(screen.getByLabelText(/Repeat password/), 'different')
    await user.click(screen.getByRole('checkbox'))
    await user.click(screen.getByRole('button', { name: 'Create account' }))
    expect(await screen.findByText(/3-32 characters/)).toBeInTheDocument()
    expect(screen.getByText('Use at least 10 characters.', { selector: 'p' })).toBeInTheDocument()
    expect(screen.getByText('The two passwords do not match.')).toBeInTheDocument()
    expect(calls.some((c) => c.path === '/api/auth/register')).toBe(false)
  })

  it('registers with the acknowledgement and opens the dashboard', async () => {
    const { user, calls } = await open()
    await user.type(screen.getByLabelText(/Username/), 'alice')
    await user.type(screen.getByLabelText(/^Password/), 'correct-horse-9')
    await user.type(screen.getByLabelText(/Repeat password/), 'correct-horse-9')
    await user.click(screen.getByRole('checkbox'))
    await user.click(screen.getByRole('button', { name: 'Create account' }))
    await waitFor(() => expect(calls.some((c) => c.path === '/api/auth/register')).toBe(true))
    expect(calls.find((c) => c.path === '/api/auth/register')!.body).toMatchObject({ username: 'alice', acknowledge_responsible_use: true })
    expect(await screen.findByRole('heading', { name: 'Dashboard' })).toBeInTheDocument()
  })

  it('shows a taken username', async () => {
    const { user } = await open()
    mockFetch({ 'GET /api/meta/attributes': META, 'POST /api/auth/register': () => apiError(409, 'username_taken', 'That username is already taken.') })
    await user.type(screen.getByLabelText(/Username/), 'alice')
    await user.type(screen.getByLabelText(/^Password/), 'correct-horse-9')
    await user.type(screen.getByLabelText(/Repeat password/), 'correct-horse-9')
    await user.click(screen.getByRole('checkbox'))
    await user.click(screen.getByRole('button', { name: 'Create account' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('That username is already taken.')
  })
})
