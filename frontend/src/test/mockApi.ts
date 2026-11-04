import { vi } from 'vitest'

export interface Route {
  method: 'GET' | 'POST'
  match: RegExp
  /** Called on every matching request so tests can sequence replies. */
  reply: (context: { url: string; body: Record<string, unknown> }) => unknown
  /** Optional HTTP status; defaults to 200. */
  status?: number
}

function fakeResponse(data: unknown, status: number): Response {
  const headers = new Headers({ 'Content-Type': 'application/json' })
  headers.set('X-Session-Token', 'test-session-token')
  return {
    ok: status >= 200 && status < 300,
    status,
    headers,
    json: async () => data,
  } as unknown as Response
}

/** Replace `fetch` with a router over the supplied fixtures. */
export function installFetchMock(routes: Route[]) {
  const calls: Array<{ method: string; url: string; body: Record<string, unknown> }> = []

  const mock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = typeof input === 'string' ? input : String(input)
    const method = (init?.method ?? 'GET').toUpperCase()
    let body: Record<string, unknown> = {}
    if (typeof init?.body === 'string') {
      try {
        body = JSON.parse(init.body) as Record<string, unknown>
      } catch {
        body = {}
      }
    }

    calls.push({ method, url, body })

    const route = routes.find((candidate) => candidate.method === method && candidate.match.test(url))
    if (!route) {
      throw new Error(`Unhandled ${method} request to ${url}`)
    }

    return fakeResponse(route.reply({ url, body }), route.status ?? 200)
  })

  vi.stubGlobal('fetch', mock)
  return { mock, calls }
}

export function resetFetchMock(): void {
  vi.unstubAllGlobals()
}
