import { expect, test, type Browser, type Page } from '@playwright/test'

// One investigator's complete journey through the real application. All data here is synthetic.
const RUN = Date.now().toString(36)
const USERNAME = `e2e_${RUN}`
const PASSWORD = 'correct-horse-9'
const HINDI = 'वह आदमी लगभग 35 साल का था। उसका रंग गोरा था, चेहरा गोल, भौंहें मोटी, नाक पतली और छोटे घुंघराले बाल थे। दाढ़ी थी और चश्मा पहना था। गाल पर निशान था।'
const TITLE = `E2E market incident ${RUN}`
const INVESTIGATOR = 'Inspector E2E'
const WITNESS = 'ರವಿ ಕುಮಾರ್' // a Kannada name: names in any script must work end to end
// The colour chips of the skin colours (the same values the server paints and the editor shows).
const WHITE = '#f5d9c4'
const BROWN = '#b9825a'
const BLACK = '#704c3a'

test.describe.configure({ mode: 'serial' })

let page: Page
let isAdmin = false
let caseId = ''

test.beforeAll(async ({ browser }: { browser: Browser }) => {
  page = await (await browser.newContext({ viewport: { width: 1440, height: 900 } })).newPage()
})
test.afterAll(async () => page.context().close())

/** Pixels of the large sketch currently shown, so two versions can be compared byte for byte. */
async function selectedSketchPixels(): Promise<Buffer> {
  const img = page.getByRole('img', { name: /^Sketch version \d+$/ }).first()
  await expect(img).toBeVisible()
  return img.screenshot()
}

/** The most common colours of the large sketch shown, as '#rrggbb', read from its real pixels inside the browser. */
async function topColours(count = 6): Promise<string[]> {
  const img = page.getByRole('img', { name: /^Sketch version \d+$/ }).first()
  await expect(img).toBeVisible()
  return img.evaluate((el, n) => {
    const image = el as HTMLImageElement
    const canvas = document.createElement('canvas')
    canvas.width = image.naturalWidth
    canvas.height = image.naturalHeight
    const ctx = canvas.getContext('2d')!
    ctx.drawImage(image, 0, 0)
    const data = ctx.getImageData(0, 0, canvas.width, canvas.height).data
    const counts = new Map<number, number>()
    for (let i = 0; i < data.length; i += 4) {
      const key = (data[i]! << 16) | (data[i + 1]! << 8) | data[i + 2]!
      counts.set(key, (counts.get(key) ?? 0) + 1)
    }
    return [...counts.entries()].sort((a, b) => b[1] - a[1]).slice(0, n).map(([k]) => '#' + k.toString(16).padStart(6, '0'))
  }, count)
}

test('a signed-out visitor is sent to the login page', async () => {
  await page.goto('/workspace')
  await expect(page).toHaveURL(/\/login$/)
  await expect(page.getByRole('heading', { name: 'Sign in' })).toBeVisible()
  await expect(page.getByText(/does not identify people/)).toBeVisible()
})

test('registration requires accepting the responsible-use statement', async () => {
  await page.getByRole('link', { name: 'Create one' }).click()
  await page.getByLabel('Username').fill(USERNAME)
  await page.getByLabel(/^Password/).fill(PASSWORD)
  await page.getByLabel('Repeat password').fill(PASSWORD)
  await page.getByRole('button', { name: 'Create account' }).click()
  await expect(page.getByText(/must accept the responsible-use statement/)).toBeVisible()
  await page.getByRole('checkbox').check()
  await page.getByRole('button', { name: 'Create account' }).click()
  await expect(page.getByRole('heading', { name: 'Dashboard' })).toBeVisible()
  isAdmin = await page.getByText('Administrator').first().isVisible()
})

test('the dashboard starts empty and tells the truth about AI engines', async () => {
  await expect(page.getByRole('region', { name: 'Statistics' })).toBeVisible()
  await expect(page.getByText('No cases yet').first()).toBeVisible()
  await expect(page.getByText('AI engines are not set up')).toBeVisible()
})

test('new investigation: case -> Hindi description read with evidence -> first sketch', async () => {
  await page.getByRole('link', { name: 'New investigation' }).first().click()
  await page.getByLabel(/Case title/).fill(TITLE)
  await page.getByLabel(/Investigator reference/).fill('E2E-001')
  await expect(page.getByLabel(/Investigator name/)).toHaveValue(USERNAME) // pre-filled from the account
  await page.getByLabel(/Investigator name/).fill(INVESTIGATOR)
  await page.getByRole('button', { name: 'Create case and continue' }).click()
  await expect(page.getByText('Enter the witness’s name, or a code such as W-01 if the name must be withheld.')).toBeVisible()
  await page.getByLabel(/Witness name/).fill(WITNESS)
  await page.getByRole('button', { name: 'Create case and continue' }).click()
  await expect(page.getByRole('heading', { name: '2. Witness description' })).toBeVisible()
  await expect(page.locator('header')).toContainText(INVESTIGATOR) // who is investigating ...
  await expect(page.locator('header')).toContainText(WITNESS) // ... and who the witness is, on every page
  await expect(page.getByLabel('Who gave this description')).toHaveValue(WITNESS) // the description starts out as the witness's
  caseId = (await page.locator('header').getByText(/^SA-\d{4}-[A-Z2-9]{6}$/).first().textContent())!.trim()
  expect(caseId).toMatch(/^SA-\d{4}-[A-HJKMNP-Z2-9]{6}$/)

  await page.getByLabel('Language of the text').selectOption('hi')
  await page.getByLabel('What the witness said').fill(HINDI)
  await page.getByRole('button', { name: 'Read description' }).click()
  await expect(page.getByRole('heading', { name: 'Review and correct the attributes' })).toBeVisible()
  await expect(page.getByText('“भौंहें मोटी”')).toBeVisible() // the witness's own words are shown as evidence
  await expect(page.getByText(/NOT reviewed by a native speaker/).first()).toBeVisible()
  await expect(page.getByRole('heading', { name: /Not converted/ })).toBeVisible()
  await expect(page.getByText(/निशान/).first()).toBeVisible() // the unsupported "scar" phrase is listed, not guessed
  await expect(page.getByRole('combobox', { name: /Face shape/ })).toHaveValue('round')
  await expect(page.getByText('“रंग गोरा”')).toBeVisible() // the skin-colour words are shown as evidence ...
  await expect(page.getByRole('combobox', { name: 'Skin colour' })).toHaveValue('white') // ... and become the Hindi -> white skin colour
  await page.getByRole('button', { name: 'Save description to the case' }).click()

  await expect(page.getByRole('heading', { name: '3. First sketch' })).toBeVisible()
  await expect(page.getByRole('radio', { name: /AI engine/ })).toBeDisabled() // not set up, and says so
  await page.getByRole('button', { name: 'Generate first sketch' }).click()
  await expect(page).toHaveURL(/\/workspace$/)
  await expect(page.getByRole('heading', { name: /Version 1 — selected for editing/ })).toBeVisible()
  await expect(page.getByText('Schematic · not AI').first()).toBeVisible()
  await expect(page.getByText('Skin colour:').first()).toBeVisible() // listed with the attributes that were drawn
  await expect.poll(() => topColours(), { message: 'the face should be painted in the white skin colour' }).toContain(WHITE)
})

let version1Pixels: Buffer

test('a revision creates version 2 with really different pixels, and version 1 stays untouched', async () => {
  version1Pixels = await selectedSketchPixels()
  await page.getByLabel('Language of the instruction').selectOption('en')
  await page.getByRole('textbox', { name: 'Instruction' }).fill('remove the glasses and make the eyebrows thinner')
  await page.getByRole('button', { name: 'Create revision (new version)' }).click()
  await expect(page.getByRole('heading', { name: /Version 2 — selected for editing/ })).toBeVisible()
  await expect(page.getByText('Version 2 was just created and is now selected')).toBeVisible()
  await expect(page.getByText('Not applied').or(page.getByText('Applied')).first()).toBeVisible()
  await page.waitForTimeout(600)
  const version2Pixels = await selectedSketchPixels()
  expect(version2Pixels.equals(version1Pixels)).toBe(false)

  const history = page.getByRole('heading', { name: 'Version history (2)' }).locator('xpath=ancestor::section[1]')
  await expect(history.getByRole('listitem')).toHaveCount(2)
  await expect(history.getByRole('listitem').nth(1)).toContainText('Initial sketch')
  await expect(history.getByRole('listitem').nth(0)).toContainText('remove the glasses and make the eyebrows thinner')
})

test('an instruction that cannot be applied is explained and creates nothing', async () => {
  await page.getByRole('textbox', { name: 'Instruction' }).fill('add a scar on the left cheek') // scars are not in the vocabulary
  await page.getByRole('button', { name: 'Create revision (new version)' }).click()
  await expect(page.getByText('Nothing was changed', { exact: true })).toBeVisible()
  await expect(page.getByText('“scar on the left cheek”')).toBeVisible()
  await expect(page.getByRole('heading', { name: 'Version history (2)' })).toBeVisible()
})

test('versions can be compared side by side', async () => {
  await page.getByRole('checkbox', { name: /Compare\s+version 1/ }).check()
  await page.getByRole('checkbox', { name: /Compare\s+version 2/ }).check()
  await page.getByRole('button', { name: /Compare selected \(2\/2\)/ }).click()
  const heading = page.getByRole('heading', { name: 'Comparing version 1 and version 2' })
  await expect(heading).toBeVisible()
  const compare = heading.locator('xpath=ancestor::section[1]')
  await expect(compare.getByRole('row', { name: /Glasses/ })).toContainText('changed')
  await expect(compare.getByRole('row', { name: /Eyebrow thickness/ })).toContainText('changed')
  await expect(compare.getByText(/attributes? differs?/)).toBeVisible()
})

test('an older version can be selected for editing', async () => {
  const history = page.getByRole('heading', { name: 'Version history (2)' }).locator('xpath=ancestor::section[1]')
  await history.getByRole('listitem').nth(1).getByRole('button', { name: 'Select for editing' }).click()
  await expect(page.getByRole('heading', { name: /Version 1 — selected for editing/ })).toBeVisible()
})

test('the selected case follows the user to the Reports page, which downloads a real PDF', async () => {
  await page.getByRole('link', { name: 'Reports' }).first().click()
  await expect(page.getByRole('heading', { name: TITLE })).toBeVisible()
  await expect(page.getByText(/version 1/i).first()).toBeVisible()
  const [download] = await Promise.all([page.waitForEvent('download'), page.getByRole('button', { name: 'Download PDF report' }).click()])
  expect(download.suggestedFilename()).toBe(`SketchAssist_${caseId}_report.pdf`)
  const stream = await download.createReadStream()
  const chunks: Buffer[] = []
  for await (const chunk of stream) chunks.push(chunk as Buffer)
  const pdf = Buffer.concat(chunks)
  expect(pdf.subarray(0, 5).toString()).toBe('%PDF-')
  expect(pdf.length).toBeGreaterThan(20_000)
})

test('case management: names are shown, searchable, and the case can be closed (read-only) and reopened', async () => {
  await page.getByRole('link', { name: 'Case Management' }).first().click()
  const row = page.getByRole('row', { name: new RegExp(TITLE) })
  await expect(row).toContainText(INVESTIGATOR)
  await expect(row).toContainText(WITNESS)
  await page.getByRole('searchbox', { name: 'Search' }).fill('ರವಿ') // search by (part of) the witness name
  await expect(page.getByRole('link', { name: TITLE })).toBeVisible()
  await page.getByRole('searchbox', { name: 'Search' }).fill('nobody-has-this-name')
  await expect(page.getByText('No case matches these filters')).toBeVisible()
  await page.getByRole('searchbox', { name: 'Search' }).fill('')
  await page.getByRole('link', { name: TITLE }).click()
  await expect(page.getByText('Investigator name', { exact: true }).locator('xpath=following-sibling::dd')).toHaveText(INVESTIGATOR)
  await expect(page.getByText('Witness name', { exact: true }).locator('xpath=following-sibling::dd')).toHaveText(WITNESS)
  await page.getByRole('button', { name: 'Close case' }).click()
  await expect(page.getByText('This case is closed', { exact: true })).toBeVisible()
  await page.getByRole('link', { name: 'Sketch Workspace' }).first().click()
  await expect(page.getByRole('button', { name: 'Create revision (new version)' })).toHaveCount(0)
  await page.getByRole('link', { name: 'Case Management' }).first().click()
  await page.getByRole('link', { name: TITLE }).click()
  await page.getByRole('button', { name: 'Reopen case' }).click()
  await expect(page.getByText('Case reopened.')).toBeVisible()
})

test('a skin colour instruction really repaints the face (checked on the actual pixels)', async () => {
  await page.getByRole('link', { name: 'Sketch Workspace' }).first().click()
  await expect(page.getByRole('heading', { name: /Version 1 — selected for editing/ })).toBeVisible()
  expect(await topColours()).not.toContain(BROWN)
  await page.getByLabel('Language of the instruction').selectOption('en')
  await page.getByRole('textbox', { name: 'Instruction' }).fill('make the skin brown')
  await page.getByRole('button', { name: 'Create revision (new version)' }).click()
  await expect(page.getByRole('heading', { name: /Version 3 — selected for editing/ })).toBeVisible()
  await expect.poll(() => topColours(), { message: 'version 3 should be brown' }).toContain(BROWN)

  await page.getByRole('button', { name: 'Make the skin darker' }).click() // brown -> black, one step along the scale
  await page.getByRole('button', { name: 'Create revision (new version)' }).click()
  await expect(page.getByRole('heading', { name: /Version 4 — selected for editing/ })).toBeVisible()
  await expect.poll(() => topColours(), { message: 'version 4 should be black / dark' }).toContain(BLACK)
  expect(await topColours()).not.toContain(BROWN)

  // earlier versions are untouched: version 1 is still the white one
  const history = page.getByRole('heading', { name: 'Version history (4)' }).locator('xpath=ancestor::section[1]')
  await history.getByRole('listitem').nth(3).getByRole('button', { name: 'Select for editing' }).click()
  await expect(page.getByRole('heading', { name: /Version 1 — selected for editing/ })).toBeVisible()
  await expect.poll(() => topColours()).toContain(WHITE)
})

test('dataset page shows real (zero) counts; the administrator can inspect and evaluate', async () => {
  await page.getByRole('link', { name: 'Dataset and AI Evaluation' }).first().click()
  const cufs = page.getByRole('heading', { name: /CUHK Face Sketch Database \(CUFS\)/ }).locator('xpath=ancestor::li[1]')
  await expect(cufs.getByText('Not installed', { exact: true })).toBeVisible()
  await expect(cufs.getByText('Records stored').locator('xpath=following-sibling::dd')).toHaveText('0')
  await expect(page.getByText('Setup required').first()).toBeVisible()
  await expect(page.getByText('Never evaluated').first()).toBeVisible()
  await expect(page.getByText('No evaluation has been run yet (n = 0)')).toBeVisible()

  test.skip(!isAdmin, 'Only the first registered user is an administrator; start the server on a fresh database for this part.')
  await page.getByRole('button', { name: 'Inspect all datasets' }).click()
  await expect(page.getByText(/custom_attributes: 90 files\/rows, 90 valid/)).toBeVisible()
  await page.getByRole('button', { name: 'Run evaluation' }).click()
  await expect(page.getByText('Examples (n)')).toBeVisible()
  await expect(page.getByText('Read these numbers with care')).toBeVisible()
  await expect(page.getByRole('row', { name: /Kannada/ })).toContainText('NOT reviewed by a native speaker')
})

test('another investigator cannot see this case', async ({ browser }) => {
  const other = await (await browser.newContext()).newPage()
  const name = `e2e2_${RUN}`
  await other.goto('/register')
  await other.getByLabel('Username').fill(name)
  await other.getByLabel(/^Password/).fill(PASSWORD)
  await other.getByLabel('Repeat password').fill(PASSWORD)
  await other.getByRole('checkbox').check()
  await other.getByRole('button', { name: 'Create account' }).click()
  await expect(other.getByRole('heading', { name: 'Dashboard' })).toBeVisible()
  await other.goto(`/cases/${caseId}`)
  await expect(other.getByText('Case not found')).toBeVisible()
  await expect(other.getByText(TITLE)).toHaveCount(0)
  await other.context().close()
})

test('the layout works on a phone and signing out ends the session', async () => {
  await page.setViewportSize({ width: 390, height: 844 })
  await page.goto('/')
  await expect(page.getByRole('heading', { name: 'Dashboard' })).toBeVisible()
  await page.getByRole('button', { name: 'Open menu' }).click()
  await expect(page.getByRole('navigation', { name: 'Main (mobile)' }).getByRole('link', { name: 'Sketch Workspace' })).toBeVisible()
  await page.getByRole('navigation', { name: 'Main (mobile)' }).getByRole('button', { name: 'Sign out' }).click()
  await expect(page.getByRole('heading', { name: 'Sign in' })).toBeVisible()
  await page.goto('/cases')
  await expect(page).toHaveURL(/\/login$/)
})
