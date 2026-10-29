import AxeBuilder from '@axe-core/playwright'
import { expect, test, type Page } from '@playwright/test'

// Automated accessibility scan (axe-core, WCAG 2.0 / 2.1 level A and AA) of every page and the main states, in a real browser.
// Automated tools find roughly a third of accessibility problems: this is evidence, not a certificate. Manual
// screen-reader testing has NOT been done (see docs/STATUS.md).
const RUN = Date.now().toString(36)
const PASSWORD = 'correct-horse-9'
const HINDI = 'वह आदमी लगभग 35 साल का था। उसका रंग गोरा था, चेहरा गोल, भौंहें मोटी, नाक पतली और छोटे घुंघराले बाल थे। दाढ़ी थी और चश्मा पहना था।'

test.describe.configure({ mode: 'serial' })
let page: Page

test.beforeAll(async ({ browser }) => {
  page = await (await browser.newContext({ viewport: { width: 1440, height: 900 } })).newPage()
})
test.afterAll(async () => page.context().close())

async function scan(label: string) {
  await page.waitForFunction(() => document.querySelectorAll('[role=status]:not([aria-live])').length === 0, null, { timeout: 8000 }).catch(() => undefined)
  const result = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa']).analyze()
  const serious = result.violations.filter((v) => v.impact === 'serious' || v.impact === 'critical')
  const summary = serious.map((v) => `${v.id} (${v.impact}): ${v.help} -> ${v.nodes.slice(0, 3).map((n) => n.target.join(' ')).join(' | ')}`)
  expect(summary, `${label}: serious or critical accessibility violations`).toEqual([])
  const minor = result.violations.filter((v) => v.impact !== 'serious' && v.impact !== 'critical')
  expect(minor.map((v) => `${v.id}: ${v.help}`), `${label}: moderate / minor accessibility violations`).toEqual([])
}

test('login and registration pages', async () => {
  await page.goto('/login')
  await expect(page.getByRole('heading', { name: 'Sign in' })).toBeVisible()
  await scan('login')
  await page.getByRole('button', { name: 'Sign in' }).click() // error state
  await expect(page.getByText('Enter your username and password.')).toBeVisible()
  await scan('login with error')
  await page.getByRole('link', { name: 'Create one' }).click()
  await page.getByRole('button', { name: 'Create account' }).click()
  await expect(page.getByText(/must accept the responsible-use statement/)).toBeVisible()
  await scan('register with errors')
  await page.getByLabel('Username').fill(`a11y_${RUN}`)
  await page.getByLabel(/^Password/).fill(PASSWORD)
  await page.getByLabel('Repeat password').fill(PASSWORD)
  await page.getByRole('checkbox').check()
  await page.getByRole('button', { name: 'Create account' }).click()
  await expect(page.getByRole('heading', { name: 'Dashboard' })).toBeVisible()
})

test('dashboard (empty)', async () => {
  await expect(page.getByText('No cases yet').first()).toBeVisible()
  await scan('dashboard empty')
})

test('new investigation: every step', async () => {
  await page.getByRole('link', { name: 'New investigation' }).first().click()
  await page.getByRole('button', { name: 'Create case and continue' }).click() // validation errors
  await expect(page.getByText('Enter a title of at least 3 characters.')).toBeVisible()
  await scan('new investigation with errors')
  await page.getByLabel(/Case title/).fill('Accessibility scan case')
  await page.getByLabel(/Investigator reference/).fill('A11Y-1')
  await page.getByLabel(/Witness name/).fill('Test Witness')
  await page.getByRole('button', { name: 'Create case and continue' }).click()
  await expect(page.getByRole('heading', { name: '2. Witness description' })).toBeVisible()
  await scan('witness description step')
  await page.getByLabel('Language of the text').selectOption('hi')
  await page.getByLabel('What the witness said').fill(HINDI)
  await page.getByRole('button', { name: 'Read description' }).click()
  await expect(page.getByRole('heading', { name: 'Review and correct the attributes' })).toBeVisible()
  await scan('parse result with evidence table and editor')
  await page.getByRole('button', { name: 'Save description to the case' }).click()
  await expect(page.getByRole('heading', { name: '3. First sketch' })).toBeVisible()
  await scan('first sketch step (AI engine disabled)')
  await page.getByRole('button', { name: 'Generate first sketch' }).click()
  await expect(page.getByRole('heading', { name: /Version 1 — selected/ })).toBeVisible()
})

test('sketch workspace with revision, rejected instruction and comparison', async () => {
  await page.getByLabel('Language of the instruction').selectOption('en')
  await page.getByRole('textbox', { name: 'Instruction' }).fill('remove the glasses and make the eyebrows thinner')
  await page.getByRole('button', { name: 'Create revision (new version)' }).click()
  await expect(page.getByRole('heading', { name: /Version 2 — selected/ })).toBeVisible()
  await page.waitForTimeout(800)
  await scan('workspace with two versions')
  await page.getByRole('textbox', { name: 'Instruction' }).fill('add a scar on the left cheek')
  await page.getByRole('button', { name: 'Create revision (new version)' }).click()
  await expect(page.getByText('Nothing was changed', { exact: true })).toBeVisible()
  await scan('workspace with rejected instruction')
  await page.getByRole('checkbox', { name: /Compare\s+version 1/ }).check()
  await page.getByRole('checkbox', { name: /Compare\s+version 2/ }).check()
  await page.getByRole('button', { name: /Compare selected/ }).click()
  await expect(page.getByRole('heading', { name: /Comparing version/ })).toBeVisible()
  await scan('version comparison')
})

test('case management, case detail and the edit dialog', async () => {
  await page.getByRole('link', { name: 'Case Management' }).first().click()
  await expect(page.getByRole('heading', { name: 'Case Management' })).toBeVisible()
  await scan('case list')
  await page.getByRole('link', { name: 'Accessibility scan case' }).click()
  await expect(page.getByRole('heading', { name: 'Accessibility scan case' })).toBeVisible()
  await scan('case detail')
  await page.getByRole('button', { name: 'Edit' }).click()
  await expect(page.getByRole('dialog', { name: 'Edit case details' })).toBeVisible()
  await scan('edit dialog')
  await page.keyboard.press('Escape')
  await page.getByRole('button', { name: 'Delete' }).click()
  await expect(page.getByRole('dialog', { name: 'Delete this case?' })).toBeVisible()
  await scan('delete confirmation dialog')
  await page.keyboard.press('Escape')
})

test('datasets, reports and settings', async () => {
  await page.getByRole('link', { name: 'Dataset and AI Evaluation' }).first().click()
  await expect(page.getByRole('heading', { name: 'Dataset and AI Evaluation' })).toBeVisible()
  await expect(page.getByText('No evaluation has been run yet (n = 0)')).toBeVisible()
  await scan('datasets (no evaluation yet)')
  await page.getByRole('link', { name: 'Reports' }).first().click()
  await expect(page.getByRole('heading', { name: 'Reports' })).toBeVisible()
  await expect(page.getByText(/What the report will contain/)).toBeVisible()
  await scan('reports')
  await page.getByRole('link', { name: 'Settings' }).first().click()
  await expect(page.getByRole('heading', { name: 'Settings' })).toBeVisible()
  await scan('settings')
})

test('administrator: evaluation results view', async () => {
  const admin = await page.getByText('Administrator').first().isVisible()
  test.skip(!admin, 'needs a fresh database so this user is the administrator')
  await page.getByRole('link', { name: 'Dataset and AI Evaluation' }).first().click()
  await page.getByRole('button', { name: 'Inspect all datasets' }).click()
  await expect(page.getByText('Result of the inspection you just ran')).toBeVisible()
  await page.getByRole('button', { name: 'Run evaluation' }).click()
  await expect(page.getByText('Examples (n)')).toBeVisible()
  await scan('datasets with inspection result and evaluation')
})

test('phone layout with the menu open', async () => {
  await page.setViewportSize({ width: 390, height: 844 })
  await page.goto('/')
  await expect(page.getByRole('heading', { name: 'Dashboard' })).toBeVisible()
  await scan('dashboard on a phone')
  await page.getByRole('button', { name: 'Open menu' }).click()
  await scan('mobile menu open')
})
