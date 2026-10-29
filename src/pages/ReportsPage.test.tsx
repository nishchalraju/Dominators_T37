import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { KEYS } from '@/services/storage'
import { ADMIN, CASE, V2 } from '@/test/fixtures'
import { apiError, baseRoutes, mockFetch, renderApp } from '@/test/utils'
import type { CaseDetail, SketchVersion } from '@/types/api'

const PNG = () => new Response(new Uint8Array([137, 80, 78, 71]), { status: 200 })

function open(detail: CaseDetail = CASE, versions: SketchVersion[] = [V2], over: Record<string, unknown> = {}) {
  window.localStorage.setItem(KEYS.activeCase, CASE.case_id)
  const mock = mockFetch({
    ...baseRoutes(ADMIN),
    'GET /api/cases/:id': detail,
    'GET /api/sketch-versions': { case_id: CASE.case_id, items: versions },
    'GET /api/sketch-versions/:id/image': PNG,
    ...over,
  })
  renderApp('/reports', ADMIN)
  return mock
}

describe('Reports', () => {
  it('needs a case first', async () => {
    mockFetch({ ...baseRoutes(ADMIN), 'GET /api/cases': { items: [], total: 0, page: 1, page_size: 8 } })
    renderApp('/reports', ADMIN)
    expect(await screen.findByText('Choose a case to prepare a report for')).toBeInTheDocument()
  })

  it('lists what the report contains using the real counts of the case, plus the disclaimers', async () => {
    open({ ...CASE, description_count: 2, sketch_count: 3, note_count: 4 })
    expect(await screen.findByText(/Witness description text exactly as entered, with the reviewed attributes — 2 saved/)).toBeInTheDocument()
    expect(screen.getByText(/Version history with every instruction and attribute change — 3 versions/)).toBeInTheDocument()
    expect(screen.getByText(/Investigator notes — 4 recorded/)).toBeInTheDocument()
    expect(await screen.findByText(/Selected sketch with a caption stating whether it is AI-generated — version 2/)).toBeInTheDocument()
    expect(screen.getByText(/preliminary investigative aid requiring human review/)).toBeInTheDocument()
    expect(screen.getAllByText(/does not identify people/).length).toBeGreaterThan(0)
  })

  it('shows the investigator and witness names that will be printed, and says when one is missing', async () => {
    open()
    expect(await screen.findByText(/investigator and witness names, your reference/)).toBeInTheDocument()
    const term = (name: string) => screen.getByText(name, { selector: 'dt' }).parentElement!
    expect(term('Investigator:')).toHaveTextContent('Test Investigator')
    expect(term('Witness:')).toHaveTextContent('Test Witness')
    expect(screen.queryByText(/a name is not recorded/)).not.toBeInTheDocument()
  })

  it('warns when a name is not recorded (a case from before names were collected)', async () => {
    open({ ...CASE, witness_name: '' })
    expect(await screen.findByText(/a name is not recorded; the report will say so/)).toBeInTheDocument()
    expect(screen.getAllByText('not recorded').length).toBeGreaterThanOrEqual(2) // on the page and in the header's active-case bar
  })

  it('warns that an incomplete case will give an incomplete report', async () => {
    open({ ...CASE, description_count: 0, sketch_count: 0, note_count: 0 }, [])
    expect(await screen.findByText(/it will be incomplete/)).toBeInTheDocument()
    expect(screen.getByText(/the report will say none was saved/)).toBeInTheDocument()
    expect(await screen.findByText('No sketch is selected for this case.')).toBeInTheDocument()
  })

  it('downloads the PDF from the server and saves it under the server’s file name', async () => {
    const user = userEvent.setup()
    const saved: string[] = []
    const click = vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(function (this: HTMLAnchorElement) {
      saved.push(this.download)
    })
    const { called } = open(CASE, [V2], {
      'GET /api/cases/:id/report': () => new Response('%PDF-1.7', { status: 200, headers: { 'Content-Type': 'application/pdf', 'Content-Disposition': 'attachment; filename="SketchAssist_SA-2026-ABC234_report.pdf"' } }),
    })
    await user.click(await screen.findByRole('button', { name: 'Download PDF report' }))
    await screen.findByText('The report was generated and downloaded.')
    expect(called('GET', '/api/cases/SA-2026-ABC234/report')).toHaveLength(1)
    expect(saved).toEqual(['SketchAssist_SA-2026-ABC234_report.pdf'])
    click.mockRestore()
  })

  it('shows an error when the report cannot be generated', async () => {
    const user = userEvent.setup()
    open(CASE, [V2], { 'GET /api/cases/:id/report': () => apiError(500, 'internal_error', 'Something went wrong on the server.') })
    await user.click(await screen.findByRole('button', { name: 'Download PDF report' }))
    await waitFor(() => expect(screen.getByText('Something went wrong on the server.')).toBeInTheDocument())
  })
})
