/** An error answered by (or on the way to) the backend. `code` is the backend's machine-readable code. */
export class ApiError extends Error {
  status: number
  code: string
  fields: Record<string, string>
  extra: Record<string, unknown>

  constructor(status: number, code: string, message: string, fields: Record<string, string> = {}, extra: Record<string, unknown> = {}) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.code = code
    this.fields = fields
    this.extra = extra
  }
}

export function errorMessage(error: unknown, fallback = 'Something went wrong. Please try again.'): string {
  if (error instanceof ApiError) return error.message
  if (error instanceof Error && error.message) return error.message
  return fallback
}

/** Field-level messages from a 422 response ({} for anything else). */
export function fieldErrors(error: unknown): Record<string, string> {
  return error instanceof ApiError ? error.fields : {}
}

export function isAbort(error: unknown): boolean {
  return error instanceof DOMException && error.name === 'AbortError'
}
