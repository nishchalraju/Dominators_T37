import { screen, waitFor } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { apiError, mockFetch, renderWithProviders } from '@/test/utils'
import { configureHttp } from '@/services/http'
import { AuthImage } from './AuthImage'

describe('AuthImage', () => {
  it('fetches the image WITH the token and shows it from an object URL', async () => {
    configureHttp({ getToken: () => 'tok-123' })
    const { calls } = mockFetch({
      'GET /api/sketch-versions/1/image': () => new Response(new Uint8Array([137, 80, 78, 71]), { status: 200, headers: { 'Content-Type': 'image/png' } }),
    })
    renderWithProviders(<AuthImage src="/api/sketch-versions/1/image" alt="Sketch version 1" />)
    const img = await screen.findByRole('img', { name: 'Sketch version 1' })
    expect(img).toHaveAttribute('src', 'blob:test-image')
    expect(calls[0]!.headers.get('Authorization')).toBe('Bearer tok-123')
  })

  it('shows a clear fallback when the image cannot be loaded', async () => {
    mockFetch({ 'GET /api/sketch-versions/2/image': () => apiError(410, 'image_missing', 'The image file is missing.') })
    renderWithProviders(<AuthImage src="/api/sketch-versions/2/image" alt="Sketch version 2" />)
    expect(await screen.findByText('Image unavailable')).toBeInTheDocument()
    expect(screen.getByRole('img', { name: /could not be loaded/ })).toBeInTheDocument()
  })

  it('releases the object URL when it goes away', async () => {
    mockFetch({ 'GET /api/sketch-versions/3/image': () => new Response(new Uint8Array([1, 2, 3]), { status: 200 }) })
    const { unmount } = renderWithProviders(<AuthImage src="/api/sketch-versions/3/image" alt="Sketch 3" />)
    await screen.findByRole('img', { name: 'Sketch 3' })
    unmount()
    await waitFor(() => expect(URL.revokeObjectURL).toHaveBeenCalledWith('blob:test-image'))
  })
})
