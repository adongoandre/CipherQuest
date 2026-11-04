import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, describe, expect, it } from 'vitest'

import App from '../App'
import { installFetchMock, resetFetchMock } from './mockApi'

afterEach(() => resetFetchMock())

const RIDDLE_PAYLOAD = {
  id: 1,
  slug: 'midnight-clock',
  title: 'The Midnight Secret',
  narrative: 'A folded note was worked loose from the brickwork of the old clock tower.',
  difficulty: 'beginner',
  cipher_type: 'caesar',
  cipher_name: 'Caesar Cipher',
  estimated_minutes: 5,
  stage: 'riddle',
  hint_count_total: 3,
  hints_revealed: 0,
  is_completed: false,
  riddle_prompt: 'I have hands but cannot clap.',
}

const MISSION_LIST = {
  missions: [
    {
      id: 1,
      slug: 'midnight-clock',
      title: 'The Midnight Secret',
      difficulty: 'beginner',
      cipher_type: 'caesar',
      estimated_minutes: 5,
      display_order: 1,
      is_completed: false,
    },
  ],
  daily_slug: 'midnight-clock',
}

describe('landing page', () => {
  it('shows the tagline, the three steps and the educational disclaimer', () => {
    installFetchMock([
      { method: 'POST', match: /\/analytics$/, reply: () => ({ recorded: true }) },
      { method: 'GET', match: /\/missions$/, reply: () => MISSION_LIST },
    ])

    render(
      <MemoryRouter initialEntries={['/']}>
        <App />
      </MemoryRouter>,
    )

    expect(
      screen.getByRole('heading', { level: 1, name: /crack the code/i }),
    ).toBeInTheDocument()
    expect(screen.getByText(/solve a riddle/i)).toBeInTheDocument()
    expect(screen.getByText(/discover the key/i)).toBeInTheDocument()
    expect(screen.getByText(/decode the secret/i)).toBeInTheDocument()

    // Three numbered steps, in document order.
    expect(document.querySelectorAll('.step')).toHaveLength(3)

    // Privacy note + educational disclaimer live in the footer.
    // Footer wording follows mockup page-01 verbatim.
    expect(screen.getByText(/classical ciphers are for learning and fun/i)).toBeInTheDocument()
    expect(screen.getByText(/not safe for protecting real secrets/i)).toBeInTheDocument()
    expect(screen.getByText(/only anonymous play data/i)).toBeInTheDocument()

    // Accessibility/help link is present.
    expect(screen.getByRole('link', { name: /help & accessibility/i })).toBeInTheDocument()
  })

  it('requires no registration to reach the sample mission', async () => {
    const { calls } = installFetchMock([
      { method: 'POST', match: /\/analytics$/, reply: () => ({ recorded: true }) },
      {
        method: 'GET',
        match: /\/missions\/daily$/,
        reply: () => RIDDLE_PAYLOAD,
      },
      { method: 'GET', match: /\/missions\/[^/]+$/, reply: () => RIDDLE_PAYLOAD },
      { method: 'GET', match: /\/missions$/, reply: () => MISSION_LIST },
    ])

    render(
      <MemoryRouter initialEntries={['/']}>
        <App />
      </MemoryRouter>,
    )

    const cta = screen.getByRole('button', { name: /play a sample mission/i })
    await userEvent.click(cta)

    await waitFor(() => {
      expect(calls.some((call) => call.url.includes('/api/v1/missions/daily'))).toBe(true)
    })

    // No login or registration screen was involved.
    expect(screen.queryByRole('button', { name: /sign in/i })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /register/i })).not.toBeInTheDocument()
  })

  it('shows a recoverable error when the API is unavailable', async () => {
    installFetchMock([
      { method: 'POST', match: /\/analytics$/, reply: () => ({ recorded: true }) },
      {
        method: 'GET',
        match: /\/missions\/daily$/,
        reply: () => ({ error: { code: 'no_missions', message: 'No published missions yet.' } }),
        status: 503,
      },
    ])

    render(
      <MemoryRouter initialEntries={['/']}>
        <App />
      </MemoryRouter>,
    )

    await userEvent.click(screen.getByRole('button', { name: /play a sample mission/i }))

    const alert = await screen.findByRole('alert')
    expect(alert).toHaveTextContent(/could not be loaded/i)
    // The primary action is still on screen — no dead end.
    expect(screen.getByRole('button', { name: /play a sample mission/i })).toBeEnabled()
  })
})
