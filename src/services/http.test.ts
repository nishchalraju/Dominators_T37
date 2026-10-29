import { afterEach, describe, expect, it, vi } from 'vitest'
import { apiError, json, mockFetch } from '@/test/utils'
import { ApiError } from '@/utils/errors'
import { configureHttp, request, requestBlob } from './http'

afterEach(() => configureHttp({ getToken: () => null }))

describe('request', () => {
  it('sends the bearer token and a JSON body, and builds the query string', async () => {
    configureHttp({ getToken: () => 'secret-token' })
    const { calls } = mockFetch({ 'POST /api/cases': { ok: true } })
    await request('/api/cases', { method: 'POST', body: { title: 'x' }, query: { q: 'a b', empty: '', skip: undefined, page: 2 } })
    const call = calls[0]!
    expect(call.headers.get('Authorization')).toBe('Bearer secret-token')
    expect(call.headers.get('Content-Type')).toBe('application/json')
    expect(call.body).toEqual({ title: 'x' })
    expect(call.search).toBe('?q=a+b&page=2')
  })

  it('sends no Authorization header when signed out', async () => {
    const { calls } = mockFetch({ 'GET /api/health': { ok: true } })
    await request('/api/health')
    expect(calls[0]!.headers.get('Authorization')).toBeNull()
  })

  it('turns an error body into an ApiError with code, message, fields and extras', async () => {
    mockFetch({
      'POST /api/cases': () =>
        json({ detail: 'Some fields are missing or invalid.', code: 'validation_error', fields: { title: 'Too short' }, setup_steps: ['a'] }, 422),
    })
    const error = await request('/api/cases', { method: 'POST', body: {} }).catch((e: unknown) => e)
    expect(error).toBeInstanceOf(ApiError)
    expect(error).toMatchObject({ status: 422, code: 'validation_error', message: 'Some fields are missing or invalid.', fields: { title: 'Too short' } })
    expect((error as ApiError).extra).toEqual({ setup_steps: ['a'] })
  })

  it('falls back to a readable message for non-JSON errors', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => new Response('<html>Bad gateway</html>', { status: 502 })))
    const error = (await request('/api/x').catch((e: unknown) => e)) as ApiError
    expect(error.status).toBe(502)
    expect(error.message).toContain('502')
  })

  it('reports an unreachable server clearly', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => { throw new TypeError('Failed to fetch') }))
    const error = (await request('/api/x').catch((e: unknown) => e)) as ApiError
    expect(error).toMatchObject({ status: 0, code: 'network_error' })
    expect(error.message).toMatch(/Cannot reach the server/)
  })

  it('signs the user out when the token is rejected', async () => {
    const onUnauthorized = vi.fn()
    configureHttp({ getToken: () => 'stale', onUnauthorized })
    mockFetch({ 'GET /api/cases': () => apiError(401, 'invalid_token', 'expired') })
    await request('/api/cases').catch(() => undefined)
    expect(onUnauthorized).toHaveBeenCalledTimes(1)
  })

  it('does not treat a failed LOGIN as an expired session', async () => {
    const onUnauthorized = vi.fn()
    configureHttp({ getToken: () => null, onUnauthorized })
    mockFetch({ 'POST /api/auth/login': () => apiError(401, 'invalid_credentials', 'Incorrect username or password.') })
    await request('/api/auth/login', { method: 'POST', body: {} }).catch(() => undefined)
    expect(onUnauthorized).not.toHaveBeenCalled()
  })

  it('returns undefined for 204 responses', async () => {
    mockFetch({ 'DELETE /api/cases/:id': () => json(null, 204) })
    await expect(request('/api/cases/SA-1', { method: 'DELETE' })).resolves.toBeUndefined()
  })
})

describe('requestBlob', () => {
  it('returns the bytes and the file name from Content-Disposition', async () => {
    mockFetch({
      'GET /api/cases/:id/report': () =>
        new Response('%PDF-1.7', { status: 200, headers: { 'Content-Disposition': 'attachment; filename="SketchAssist_SA-1_report.pdf"' } }),
    })
    const { blob, filename } = await requestBlob('/api/cases/SA-1/report')
    expect(filename).toBe('SketchAssist_SA-1_report.pdf')
    expect(await blob.text()).toBe('%PDF-1.7')
  })
})
