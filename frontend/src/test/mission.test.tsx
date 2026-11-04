import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { afterEach, describe, expect, it } from 'vitest'

import { MissionPage } from '../pages/Mission'
import { installFetchMock, resetFetchMock } from './mockApi'

afterEach(() => resetFetchMock())

const SLUG = 'midnight-clock'
const CIPHERTEXT = 'Htzsy jfhm mtzw zsynq ymj kjwwd fwwnajx'
const PLAINTEXT = 'Count each hour until the ferry arrives'
const CLUE = 'The hidden sentence is about keeping track of passing time.'

const BRIEF = {
  id: 1,
  slug: SLUG,
  title: 'The Midnight Secret',
  narrative: 'A folded note was worked loose from the brickwork of the old clock tower.',
  difficulty: 'beginner',
  cipher_type: 'caesar',
  cipher_name: 'Caesar Cipher',
  estimated_minutes: 5,
  hint_count_total: 3,
  hints_revealed: 0,
  is_completed: false,
}

const KEY_REVEAL = {
  accepted_answer: 'CLOCK',
  key_rule_description: 'Count the letters in your riddle answer. That number is the Caesar shift.',
  key_type: 'shift',
  parameter: 5,
}

const MISSION_LIST = {
  missions: [
    {
      id: 1,
      slug: SLUG,
      title: 'The Midnight Secret',
      difficulty: 'beginner',
      cipher_type: 'caesar',
      estimated_minutes: 5,
      display_order: 1,
      is_completed: false,
    },
  ],
  daily_slug: SLUG,
}

const SCORE = {
  total: 80,
  solve_points: 70,
  no_hint_bonus: 10,
  time_bonus: 0,
  comprehension_bonus: 0,
  hints_used: 1,
  elapsed_seconds: null,
  breakdown: { correct: true },
}

function renderMission() {
  return render(
    <MemoryRouter initialEntries={[`/missions/${SLUG}`]}>
      <Routes>
        <Route path="/missions/:slug" element={<MissionPage />} />
      </Routes>
    </MemoryRouter>,
  )
}

describe('mission loop', () => {
  it('walks riddle -> key -> clue -> decrypt -> explanation and never leaks ahead of stage', async () => {
    let riddleSubmissions = 0
    let decryptSubmissions = 0
    let advanceCalls = 0
    let hintCalls = 0

    const { calls } = installFetchMock([
      { method: 'GET', match: /\/missions\/daily$/, reply: () => ({ ...BRIEF, stage: 'riddle', riddle_prompt: 'I have hands but cannot clap. What am I?' }) },
      {
        method: 'GET',
        match: /\/missions\/[^/]+$/,
        reply: () => ({ ...BRIEF, stage: 'riddle', riddle_prompt: 'I have hands but cannot clap. What am I?' }),
      },
      { method: 'GET', match: /\/missions$/, reply: () => MISSION_LIST },
      {
        method: 'POST',
        match: /\/riddle-attempt$/,
        reply: ({ body }) => {
          riddleSubmissions += 1
          const correct = String(body.answer ?? '').trim().toLowerCase() === 'clock'
          return {
            correct,
            stage: correct ? 'key_reveal' : 'riddle',
            attempts: riddleSubmissions,
            key_reveal: correct ? KEY_REVEAL : null,
            message: correct
              ? 'Correct — this is the key for your mission.'
              : 'Not quite. Re-read the riddle, or reveal a hint.',
          }
        },
      },
      {
        method: 'POST',
        match: /\/advance$/,
        reply: () => {
          advanceCalls += 1
          return advanceCalls === 1
            ? { stage: 'context_clue', contextual_clue: CLUE, ciphertext: null, message: 'Read the clue, then reveal the message.' }
            : { stage: 'decrypt', contextual_clue: CLUE, ciphertext: CIPHERTEXT, message: 'Decrypt the message and submit your answer.' }
        },
      },
      {
        method: 'POST',
        match: /\/hint$/,
        reply: () => {
          hintCalls += 1
          return {
            hint_number: hintCalls,
            total_hints: 3,
            hint: 'It hangs on a wall, it ticks, and it has a face with no expression.',
            hints_used: hintCalls,
            score_penalty_note: 'The 10-point no-hint bonus is lost from 100.',
          }
        },
      },
      {
        method: 'POST',
        match: /\/decrypt-attempt$/,
        reply: ({ body }) => {
          decryptSubmissions += 1
          const correct = String(body.answer ?? '').trim().toLowerCase() === PLAINTEXT.toLowerCase()
          return {
            correct,
            stage: correct ? 'explanation' : 'decrypt',
            attempts: decryptSubmissions,
            hints_used: 1,
            score: correct ? SCORE : null,
            solution: correct
              ? {
                  plaintext: PLAINTEXT,
                  explanation:
                    'Key rule: Count the letters in your riddle answer. That number is the Caesar shift. Applied to the accepted answer "CLOCK" that produces 5, so this message uses a Caesar shift of 5.',
                  worked_example: 'The ciphertext begins with "Htzsy". Decrypting it: H - 5 = C.',
                }
              : null,
            message: correct ? 'Correct — here is the message and how it was made.' : 'Not quite.',
            progress_awarded: correct,
            comprehension_check: correct
              ? {
                  question: 'In this mission, where did the Caesar shift come from?',
                  choices: ['The number of letters in the riddle answer', 'The first letter'],
                  correct_index: 0,
                  explanation: 'The key rule counts letters.',
                }
              : null,
          }
        },
      },
      {
        method: 'POST',
        match: /\/comprehension$/,
        reply: ({ body }) => ({
          correct: Number(body.choice) === 0,
          earned: Number(body.choice) === 0 ? 5 : 0,
          total: Number(body.choice) === 0 ? 85 : 80,
          correct_index: 0,
          explanation: 'The key rule counts letters.',
          awarded: Number(body.choice) === 0,
        }),
      },
    ])

    renderMission()

    // ---- stage 1: riddle, with nothing protected on screen ----
    expect(await screen.findByRole('heading', { name: /the midnight secret/i })).toBeInTheDocument()
    expect(screen.getByText(/I have hands but cannot clap/i)).toBeInTheDocument()
    expect(screen.queryByText(new RegExp(CIPHERTEXT.slice(0, 12)))).not.toBeInTheDocument()
    expect(screen.queryByText(new RegExp(PLAINTEXT, 'i'))).not.toBeInTheDocument()

    // wrong answer stays on the riddle with an accessible error
    await userEvent.type(screen.getByLabelText(/your answer/i), 'banana')
    await userEvent.click(screen.getByRole('button', { name: /submit answer/i }))
    expect(await screen.findByRole('alert')).toHaveTextContent(/not quite/i)
    expect(screen.queryByText(new RegExp(CIPHERTEXT.slice(0, 12)))).not.toBeInTheDocument()

    // correct answer reveals the key — still no ciphertext
    const riddleInput = screen.getByLabelText(/your answer/i)
    await userEvent.clear(riddleInput)
    await userEvent.type(riddleInput, 'CLOCK{Enter}')
    expect(await screen.findByText(/count the letters/i)).toBeInTheDocument()
    expect(screen.getByText('shift = 5')).toBeInTheDocument()
    expect(screen.queryByText(new RegExp(CIPHERTEXT.slice(0, 12)))).not.toBeInTheDocument()

    // ---- stage 3: context clue ----
    await userEvent.click(screen.getByRole('button', { name: /read the context clue/i }))
    expect(await screen.findByText(new RegExp(CLUE.slice(0, 30)))).toBeInTheDocument()
    expect(screen.queryByText(new RegExp(CIPHERTEXT.slice(0, 12)))).not.toBeInTheDocument()

    // ---- stage 4: ciphertext ----
    await userEvent.click(screen.getByRole('button', { name: /reveal the message/i }))
    expect(await screen.findByTestId('dispatch-text')).toHaveTextContent(CIPHERTEXT)

    // hints reveal one at a time
    await userEvent.click(screen.getByRole('button', { name: /reveal hint 1 of 3/i }))
    expect(await screen.findByText(/it hangs on a wall/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /reveal hint 2 of 3/i })).toBeEnabled()

    // wrong decryption never reveals the plaintext
    await userEvent.type(screen.getByLabelText(/decrypted message/i), 'definitely not it')
    await userEvent.click(screen.getByRole('button', { name: /submit decryption/i }))
    expect(await screen.findByRole('alert')).toHaveTextContent(/not quite/i)
    expect(screen.queryByText(new RegExp(PLAINTEXT, 'i'))).not.toBeInTheDocument()

    // correct decryption reveals plaintext, explanation and score
    const decryptInput = screen.getByLabelText(/decrypted message/i)
    await userEvent.clear(decryptInput)
    await userEvent.type(decryptInput, PLAINTEXT)
    await userEvent.click(screen.getByRole('button', { name: /submit decryption/i }))

    expect(await screen.findByRole('heading', { name: /here is how it worked/i })).toBeInTheDocument()
    expect(screen.getByTestId('score-card')).toHaveTextContent('70 pts')
    expect(screen.getByTestId('score-card')).toHaveTextContent('80')
    expect(screen.getByText(/why it works/i)).toBeInTheDocument()
    expect(screen.getByText(/worked example/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /replay mission/i })).toBeEnabled()

    // the feedback survey appears only after the result
    expect(screen.getByRole('heading', { name: /how was that mission/i })).toBeInTheDocument()

    // the 5-point comprehension check ships with the solution
    expect(screen.getByRole('heading', { name: /check what you learned/i })).toBeInTheDocument()
    await userEvent.click(
      screen.getByRole('button', { name: /the number of letters in the riddle answer/i }),
    )
    expect(await screen.findByText(/correct — 5 points added/i)).toBeInTheDocument()
    // the score card picks up the 5 points
    expect(screen.getByTestId('score-card')).toHaveTextContent('5 pts')
    expect(screen.getByTestId('score-card')).toHaveTextContent('85')
    // it is graded once; the question does not reappear
    expect(screen.queryByRole('heading', { name: /check what you learned/i })).not.toBeInTheDocument()

    // every reveal was a real server call:
    // 2 riddle attempts, 2 advances, 1 hint, 2 decrypt attempts, 1 comprehension
    expect(calls.filter((call) => call.method === 'POST')).toHaveLength(8)
  })

  it('offers the reveal-solution path without awarding a score', async () => {
    let advanceCalls = 0

    installFetchMock([
      {
        method: 'GET',
        match: /\/missions\/[^/]+$/,
        reply: () => ({ ...BRIEF, stage: 'riddle', riddle_prompt: 'I have hands but cannot clap.' }),
      },
      { method: 'GET', match: /\/missions$/, reply: () => MISSION_LIST },
      {
        method: 'POST',
        match: /\/riddle-attempt$/,
        reply: () => ({
          correct: true,
          stage: 'key_reveal',
          attempts: 1,
          key_reveal: KEY_REVEAL,
          message: 'Correct.',
        }),
      },
      {
        method: 'POST',
        match: /\/advance$/,
        reply: () => {
          advanceCalls += 1
          return advanceCalls === 1
            ? { stage: 'context_clue', contextual_clue: CLUE, ciphertext: null, message: 'ok' }
            : { stage: 'decrypt', contextual_clue: CLUE, ciphertext: CIPHERTEXT, message: 'ok' }
        },
      },
      {
        method: 'POST',
        match: /\/reveal$/,
        reply: () => ({
          stage: 'explanation',
          solution: {
            plaintext: PLAINTEXT,
            explanation: 'The message was encrypted with a Caesar shift of 5.',
            worked_example: 'H - 5 = C.',
          },
          score_awarded: 0,
          message: 'Solution revealed.',
        }),
      },
    ])

    renderMission()

    await userEvent.type(await screen.findByLabelText(/your answer/i), 'clock')
    await userEvent.click(screen.getByRole('button', { name: /submit answer/i }))
    await userEvent.click(await screen.findByRole('button', { name: /read the context clue/i }))
    await userEvent.click(await screen.findByRole('button', { name: /reveal the message/i }))
    await userEvent.click(await screen.findByRole('button', { name: /reveal the solution/i }))

    expect(await screen.findByRole('heading', { name: /solution revealed/i })).toBeInTheDocument()
    expect(screen.queryByTestId('score-card')).not.toBeInTheDocument()
    expect(screen.getByText(/no solve points are awarded/i)).toBeInTheDocument()
    // The 5-point comprehension check is not offered on a revealed solution.
    expect(screen.queryByRole('heading', { name: /check what you learned/i })).not.toBeInTheDocument()
  })

  it('restores the earned score when the result screen is reloaded', async () => {
    installFetchMock([
      {
        method: 'GET',
        match: /\/missions\/[^/]+$/,
        reply: () => ({
          ...BRIEF,
          stage: 'explanation',
          key_reveal: KEY_REVEAL,
          contextual_clue: CLUE,
          ciphertext: CIPHERTEXT,
          revealed_hints: [],
          solution: {
            plaintext: PLAINTEXT,
            explanation: 'This message uses a Caesar shift of 5.',
            worked_example: 'H - 5 = C.',
          },
          comprehension_check: {
            question: 'Where did the shift come from?',
            choices: ['Letter count', 'First letter'],
            correct_index: 0,
            explanation: 'The key rule counts letters.',
          },
          earned_score: SCORE,
          comprehension_awarded: false,
        }),
      },
      { method: 'GET', match: /\/missions$/, reply: () => MISSION_LIST },
    ])

    renderMission()

    expect(await screen.findByRole('heading', { name: /here is how it worked/i })).toBeInTheDocument()
    expect(screen.getByTestId('score-card')).toHaveTextContent('80')
    expect(screen.queryByText(/no solve points are awarded/i)).not.toBeInTheDocument()
    expect(screen.getByRole('heading', { name: /check what you learned/i })).toBeInTheDocument()
  })

  it('solves the decrypt stage graphically on the decoder wheel', async () => {
    let advanceCalls = 0

    installFetchMock([
      {
        method: 'GET',
        match: /\/missions\/[^/]+$/,
        reply: () => ({ ...BRIEF, stage: 'riddle', riddle_prompt: 'I have hands but cannot clap.' }),
      },
      { method: 'GET', match: /\/missions$/, reply: () => MISSION_LIST },
      {
        method: 'POST',
        match: /\/riddle-attempt$/,
        reply: () => ({
          correct: true,
          stage: 'key_reveal',
          attempts: 1,
          key_reveal: KEY_REVEAL,
          message: 'Correct.',
        }),
      },
      {
        method: 'POST',
        match: /\/advance$/,
        reply: () => {
          advanceCalls += 1
          return advanceCalls === 1
            ? { stage: 'context_clue', contextual_clue: CLUE, ciphertext: null, message: 'ok' }
            : { stage: 'decrypt', contextual_clue: CLUE, ciphertext: CIPHERTEXT, message: 'ok' }
        },
      },
      {
        method: 'POST',
        match: /\/decrypt-attempt$/,
        reply: ({ body }) => {
          const correct = String(body.answer ?? '').trim().toLowerCase() === PLAINTEXT.toLowerCase()
          return {
            correct,
            stage: correct ? 'explanation' : 'decrypt',
            attempts: 1,
            hints_used: 0,
            score: correct ? SCORE : null,
            solution: correct
              ? { plaintext: PLAINTEXT, explanation: 'Shift of 5.', worked_example: 'H - 5 = C.' }
              : null,
            message: correct ? 'Correct.' : 'Not quite.',
            progress_awarded: correct,
            comprehension_check: null,
          }
        },
      },
    ])

    renderMission()

    await userEvent.type(await screen.findByLabelText(/your answer/i), 'clock{Enter}')
    await userEvent.click(await screen.findByRole('button', { name: /read the context clue/i }))
    await userEvent.click(await screen.findByRole('button', { name: /reveal the message/i }))

    // the wheel opens on the ciphertext: nothing is decoded yet
    expect(await screen.findByTestId('wheel-reading')).toHaveTextContent(CIPHERTEXT)

    // turn the wheel to the key they were given (shift = 5)
    fireEvent.change(screen.getByLabelText(/turn the wheel/i), { target: { value: '5' } })
    expect(screen.getByTestId('wheel-reading')).toHaveTextContent(PLAINTEXT)

    await userEvent.click(screen.getByRole('button', { name: /check this reading/i }))

    expect(await screen.findByRole('heading', { name: /here is how it worked/i })).toBeInTheDocument()
    expect(screen.getByTestId('score-card')).toHaveTextContent('80')
  })

  it('keeps Enter-key submission on the riddle form', async () => {
    installFetchMock([
      {
        method: 'GET',
        match: /\/missions\/[^/]+$/,
        reply: () => ({ ...BRIEF, stage: 'riddle', riddle_prompt: 'A riddle goes here.' }),
      },
      { method: 'GET', match: /\/missions$/, reply: () => MISSION_LIST },
      {
        method: 'POST',
        match: /\/riddle-attempt$/,
        reply: () => ({
          correct: true,
          stage: 'key_reveal',
          attempts: 1,
          key_reveal: KEY_REVEAL,
          message: 'Correct.',
        }),
      },
    ])

    renderMission()

    const input = await screen.findByLabelText(/your answer/i)
    await userEvent.type(input, 'clock{Enter}')

    await waitFor(() => {
      expect(screen.getByText(/count the letters/i)).toBeInTheDocument()
    })
  })
})
