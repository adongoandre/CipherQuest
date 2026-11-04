import { useEffect, useRef, useState } from 'react'
import { Link, useParams } from 'react-router-dom'

import { CipherWheel } from '../components/CipherWheel'
import { Dispatch } from '../components/Dispatch'
import { FeedbackSurvey } from '../components/FeedbackSurvey'
import { HintPanel } from '../components/HintPanel'
import { ScoreCard } from '../components/ScoreCard'
import {
  api,
  type Brief,
  type ComprehensionCheck as ComprehensionCheckData,
  type KeyReveal,
  type MissionListResponse,
  type MissionStage,
  type ScoreBreakdown,
  type Solution,
} from '../lib/api'

type Phase = 'loading' | 'error' | 'ready'

type ComprehensionCheckContent = NonNullable<ComprehensionCheckData>

interface MissionState {
  brief: Brief
  riddlePrompt: string
  keyReveal: KeyReveal | null
  clue: string | null
  ciphertext: string | null
  revealedHints: string[]
  solution: Solution | null
  comprehensionCheck: ComprehensionCheckContent | null
}

interface LoadedState {
  phase: Phase
  mission: MissionState | null
  message: string | null
}

const TRACK: Array<{ stage: MissionStage; label: string }> = [
  { stage: 'riddle', label: 'Riddle' },
  { stage: 'key_reveal', label: 'Key' },
  { stage: 'context_clue', label: 'Clue' },
  { stage: 'decrypt', label: 'Decrypt' },
  { stage: 'explanation', label: 'Result' },
]

const STAGE_INDEX: Record<MissionStage, number> = {
  riddle: 0,
  key_reveal: 1,
  context_clue: 2,
  decrypt: 3,
  explanation: 4,
}

function newStateFromPayload(
  payload: Awaited<ReturnType<typeof api.mission>>,
): MissionState {
  return {
    brief: payload as Brief,
    riddlePrompt: 'riddle_prompt' in payload ? payload.riddle_prompt : '',
    keyReveal: 'key_reveal' in payload ? payload.key_reveal : null,
    clue: 'contextual_clue' in payload ? payload.contextual_clue : null,
    ciphertext: 'ciphertext' in payload ? payload.ciphertext : null,
    revealedHints: 'revealed_hints' in payload ? payload.revealed_hints : [],
    solution: 'solution' in payload ? payload.solution : null,
    comprehensionCheck: 'comprehension_check' in payload ? payload.comprehension_check : null,
  }
}

function newIdempotencyKey(): string {
  if (typeof crypto !== 'undefined' && 'randomUUID' in crypto) return crypto.randomUUID()
  return `k-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`
}

export function MissionPage() {
  const { slug = '' } = useParams()

  const [state, setState] = useState<LoadedState>({
    phase: 'loading',
    mission: null,
    message: null,
  })
  const [stage, setStage] = useState<MissionStage>('riddle')
  const [riddleAnswer, setRiddleAnswer] = useState('')
  const [decryptAnswer, setDecryptAnswer] = useState('')
  const [riddleError, setRiddleError] = useState<string | null>(null)
  const [decryptError, setDecryptError] = useState<string | null>(null)
  const [feedback, setFeedback] = useState<string | null>(null)
  const [hintsUsed, setHintsUsed] = useState(0)
  const [score, setScore] = useState<ScoreBreakdown | null>(null)
  const [comprehension, setComprehension] = useState<{
    answered: boolean
    correct: boolean
    awarded: boolean
    explanation: string
  } | null>(null)
  const [busy, setBusy] = useState(false)
  const [nextSlug, setNextSlug] = useState<string | null>(null)

  const headingRef = useRef<HTMLHeadingElement>(null)
  const liveRef = useRef<HTMLParagraphElement>(null)

  // --- load -----------------------------------------------------------------
  useEffect(() => {
    document.title = 'Mission — CipherQuest'
    let cancelled = false

    Promise.all([api.mission(slug), api.missions()])
      .then(([payload, list]) => {
        if (cancelled) return
        const mission = newStateFromPayload(payload)
        setState({ phase: 'ready', mission, message: null })
        setStage(payload.stage)
        setHintsUsed(payload.hints_revealed)
        if ('earned_score' in payload) {
          // Reloading the result screen must show the score that was earned,
          // not fall back to the "solution revealed" presentation.
          setScore(payload.earned_score)
          if (payload.comprehension_awarded && payload.comprehension_check) {
            setComprehension({
              answered: true,
              correct: true,
              awarded: true,
              explanation: payload.comprehension_check.explanation,
            })
          }
        }
        setNextSlug(nextOf(list, payload.slug))
      })
      .catch((error: unknown) => {
        if (cancelled) return
        setState({
          phase: 'error',
          mission: null,
          message: error instanceof Error ? error.message : 'The mission could not be loaded.',
        })
      })

    return () => {
      cancelled = true
    }
  }, [slug])

  // Move focus to the stage heading whenever the stage advances.
  useEffect(() => {
    if (state.phase === 'ready') headingRef.current?.focus()
  }, [stage, state.phase])

  const mission = state.mission
  const stageIndex = STAGE_INDEX[stage]

  function announce(text: string) {
    if (liveRef.current) liveRef.current.textContent = text
  }

  function applyMission(patch: Partial<MissionState>) {
    setState((current) =>
      current.mission
        ? { ...current, mission: { ...current.mission, ...patch } }
        : current,
    )
  }

  // --- actions ---------------------------------------------------------------

  async function submitRiddle(event: React.FormEvent) {
    event.preventDefault()
    if (!mission) return
    setBusy(true)
    setRiddleError(null)
    try {
      const result = await api.submitRiddle(slug, riddleAnswer, newIdempotencyKey())
      if (result.correct && result.key_reveal) {
        applyMission({ keyReveal: result.key_reveal })
        setStage('key_reveal')
        setFeedback(result.message)
        announce(`${result.message} The answer was ${result.key_reveal.accepted_answer}.`)
      } else {
        setRiddleError(result.message)
        announce(result.message)
      }
    } catch (error) {
      setRiddleError(error instanceof Error ? error.message : 'Your answer could not be checked.')
    } finally {
      setBusy(false)
    }
  }

  async function showClue() {
    setBusy(true)
    setFeedback(null)
    try {
      const result = await api.advance(slug)
      applyMission({ clue: result.contextual_clue })
      setStage('context_clue')
      announce(result.message)
    } catch (error) {
      setFeedback(error instanceof Error ? error.message : 'The clue could not be revealed.')
    } finally {
      setBusy(false)
    }
  }

  async function showMessage() {
    setBusy(true)
    setFeedback(null)
    try {
      const result = await api.advance(slug)
      applyMission({ ciphertext: result.ciphertext })
      setStage('decrypt')
      announce(result.message)
    } catch (error) {
      setFeedback(error instanceof Error ? error.message : 'The message could not be revealed.')
    } finally {
      setBusy(false)
    }
  }

  async function submitDecrypt(event: React.FormEvent) {
    event.preventDefault()
    await runDecrypt(decryptAnswer)
  }

  async function runDecrypt(answerText: string) {
    if (!mission) return
    setBusy(true)
    setDecryptError(null)
    try {
      const result = await api.submitDecrypt(slug, answerText, {
        idempotencyKey: newIdempotencyKey(),
      })
      if (result.correct && result.solution) {
        applyMission({ solution: result.solution, comprehensionCheck: result.comprehension_check })
        setScore(result.score)
        setStage('explanation')
        setFeedback(result.message)
        announce(`${result.message} Score: ${result.score?.total ?? 0} out of 100.`)
      } else {
        setDecryptError(result.message)
        announce(result.message)
      }
    } catch (error) {
      setDecryptError(error instanceof Error ? error.message : 'Your answer could not be checked.')
    } finally {
      setBusy(false)
    }
  }

  async function revealSolution() {
    setBusy(true)
    try {
      const result = await api.reveal(slug, 'stuck')
      applyMission({ solution: result.solution })
      setScore(null)
      setStage('explanation')
      setFeedback(result.message)
      announce(result.message)
    } catch (error) {
      setFeedback(error instanceof Error ? error.message : 'The solution could not be revealed.')
    } finally {
      setBusy(false)
    }
  }

  async function answerComprehension(choice: number) {
    try {
      const result = await api.comprehension(slug, choice)
      setComprehension({
        answered: true,
        correct: result.correct,
        awarded: result.awarded,
        explanation: result.explanation,
      })
      announce(result.correct ? 'Correct.' : `Not this time. ${result.explanation}`)
    } catch (error) {
      setFeedback(error instanceof Error ? error.message : 'Your answer could not be checked.')
    }
  }

  /**
   * Play the case again. A finished mission moves on to its next telling — a
   * fresh story, riddle and message that share only the cipher — while an
   * unfinished one rewinds to the same telling. The server hands back the
   * payload for the new run, so every stage local state resets with it.
   */
  async function restartMission() {
    if (busy) return
    setBusy(true)
    try {
      const payload = await api.restart(slug)
      const fresh = newStateFromPayload(payload)
      setState({ phase: 'ready', mission: fresh, message: null })
      setStage(payload.stage)
      setHintsUsed(payload.hints_revealed)
      setScore(null)
      setComprehension(null)
      setRiddleAnswer('')
      setDecryptAnswer('')
      setRiddleError(null)
      setDecryptError(null)
      const note =
        payload.telling_number > 1
          ? `Case retold — telling ${payload.telling_number} of ${payload.telling_count}. The same rule still guards the key.`
          : 'The case is open again from the beginning.'
      setFeedback(note)
      announce(note)
    } catch (error) {
      setFeedback(error instanceof Error ? error.message : 'The mission could not be restarted.')
    } finally {
      setBusy(false)
    }
  }

  // --- render ----------------------------------------------------------------

  if (state.phase === 'loading') {
    return (
      <p className="skeleton" role="status">
        Opening the case file…
      </p>
    )
  }

  if (state.phase === 'error' || !mission) {
    return (
      <div className="prose">
        <p className="eyebrow">Problem</p>
        <h1>The mission could not be opened.</h1>
        <div className="notice notice-error" role="alert">
          <span className="notice-icon" aria-hidden="true">
            ✕
          </span>
          <span className="notice-body">{state.message ?? 'Unknown error.'}</span>
        </div>
        <p className="muted">Check that the API is running, then try again.</p>
        <Link className="btn btn-primary" to="/missions">
          Back to missions
        </Link>
      </div>
    )
  }

  const { brief, keyReveal, clue, ciphertext, solution, riddlePrompt } = mission

  return (
    <>
      <header className="mission-header">
        <div>
          <h1 ref={headingRef} tabIndex={-1} style={{ marginBottom: '0.2em' }}>
            {brief.title}
          </h1>
          <div className="badge-row" style={{ marginBottom: '1.5rem' }}>
            <span className={`badge tag-difficulty-${brief.difficulty}`}>{brief.difficulty}</span>
            <span className="badge">{brief.estimated_minutes} min</span>
            <span className="badge">Untimed</span>
          </div>
          <ol className="progress-track" aria-label="Mission progress">
            {TRACK.map((item, index) => (
              <li
                key={item.stage}
                data-done={index < stageIndex}
                aria-current={index === stageIndex ? 'step' : undefined}
              >
                {item.label}
              </li>
            ))}
          </ol>
          <p className="muted" style={{ margin: 0 }}>
            {brief.narrative}
          </p>
        </div>
        <p className="sr-only" aria-live="polite" ref={liveRef} />
        {feedback && (
          <p className="notice" role="status">
            <span className="notice-icon" aria-hidden="true">
              ℹ
            </span>
            <span className="notice-body">{feedback}</span>
          </p>
        )}
      </header>

      

      {/* ---- stage: riddle ---- */}
      {stage === 'riddle' && (
        <div className="stack">
          <section className="card" aria-labelledby="riddle-title">
            <h2 id="riddle-title">Solve the riddle to find the key</h2>
            <p className="stage-sub">Find the key that opens the message. Think carefully…</p>

            <blockquote className="parchment riddle-box">
              <p>{riddlePrompt}</p>
            </blockquote>

            <form onSubmit={submitRiddle} noValidate>
            <div className="field">
              <label className="field-label" htmlFor="riddle-answer">
                Your answer
              </label>
              <span className="field-hint" id="riddle-hint">
                One word is usually enough. Capitals do not matter.
              </span>
              <input
                id="riddle-answer"
                className="input"
                value={riddleAnswer}
                onChange={(event) => setRiddleAnswer(event.target.value)}
                autoComplete="off"
                spellCheck={false}
                required
                maxLength={120}
                aria-describedby="riddle-hint"
                aria-invalid={riddleError ? true : undefined}
              />
            </div>

            {riddleError && (
              <div className="notice notice-error" role="alert">
                <span className="notice-icon" aria-hidden="true">
                  ✕
                </span>
                <span className="notice-body">{riddleError}</span>
              </div>
            )}

            <div className="button-row" style={{ marginTop: '1rem' }}>
              <button type="submit" className="btn btn-primary" disabled={busy}>
                {busy ? 'Checking…' : 'Submit answer'}
              </button>
              <Link className="btn btn-secondary" to="/missions">
                Leave mission
              </Link>
            </div>
          </form>
          </section>

          <HintPanel
            slug={slug}
            totalHints={brief.hint_count_total}
            hintsUsed={hintsUsed}
            initialHints={mission.revealedHints}
            onHintUsed={(hint) => {
              setHintsUsed(hint.hints_used)
              announce(`Hint ${hint.hint_number} revealed.`)
            }}
          />
        </div>
      )}

      {/* ---- stage: key reveal ---- */}
      {stage === 'key_reveal' && keyReveal && (
        <div className="stack">
          <section className="card card-key" aria-labelledby="key-title">
            <div className="key-art" aria-hidden="true">
              <svg viewBox="0 0 64 64" width="92" height="92" focusable="false">
                <circle cx="23" cy="23" r="13.5" fill="none" stroke="currentColor" strokeWidth="5" />
                <circle cx="23" cy="23" r="4.5" fill="currentColor" />
                <path
                  d="M32.5 32.5 L56 56"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="5"
                  strokeLinecap="round"
                />
                <path
                  d="M47 47 L41.5 52.5 M53 53 L48 58"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="4"
                  strokeLinecap="round"
                />
              </svg>
            </div>
            <h2 id="key-title">How {keyReveal.accepted_answer} becomes your key</h2>
            <p className="key-word">{keyReveal.accepted_answer}</p>
            <p style={{ maxWidth: '52ch' }}>{keyReveal.key_rule_description}</p>

            <div className="panel" style={{ marginTop: '1rem' }}>
              <p className="mono" style={{ margin: 0, letterSpacing: '0.16em' }}>
                {keyReveal.accepted_answer.split('').join(' · ')} = {keyReveal.parameter} letters
              </p>
              <p className="mono" style={{ margin: '0.35rem 0 0' }}>
                shift = {keyReveal.parameter}
              </p>
            </div>

            <div className="button-row" style={{ marginTop: '1.25rem' }}>
              <button type="button" className="btn btn-primary" onClick={showClue} disabled={busy}>
                {busy ? 'Revealing…' : 'Read the context clue'}
              </button>
              <Link className="btn btn-secondary" to="/missions">
                Leave mission
              </Link>
            </div>
          </section>

          <HintPanel
            slug={slug}
            totalHints={brief.hint_count_total}
            hintsUsed={hintsUsed}
            initialHints={mission.revealedHints}
            onHintUsed={(hint) => {
              setHintsUsed(hint.hints_used)
              announce(`Hint ${hint.hint_number} revealed.`)
            }}
          />
        </div>
      )}

      {/* ---- stage: context clue ---- */}
      {stage === 'context_clue' && clue && (
        <section className="card" aria-labelledby="clue-title">
          <h2 id="clue-title">What is the hidden message about?</h2>

          <div className="panel" style={{ borderLeft: '3px solid var(--verdigris)' }}>
            <p style={{ margin: 0 }}>{clue}</p>
          </div>

          <p className="muted" style={{ marginTop: '1rem' }}>
            The clue hints at the topic only. It never hands you the words — you still have to
            shift every letter yourself.
          </p>

          <div className="button-row" style={{ marginTop: '1.25rem' }}>
            <button type="button" className="btn btn-primary" onClick={showMessage} disabled={busy}>
              {busy ? 'Revealing…' : 'Reveal the message'}
            </button>
          </div>
        </section>
      )}

      {/* ---- stage: decrypt ---- */}
      {stage === 'decrypt' && ciphertext && keyReveal && (
        <div className="stack">
          <section className="card" aria-labelledby="decrypt-title">
            <h2 id="decrypt-title">Read the message</h2>

            <div className="badge-row" style={{ marginBottom: '1rem' }}>
              <span className="badge">{brief.cipher_name}</span>
              <span className="badge">{keyReveal.key_rule_description ? 'Rule stated below' : ''}</span>
            </div>

            {clue && (
              <div className="panel" style={{ marginBottom: '1rem' }}>
                <strong>Context clue:</strong> {clue}
              </div>
            )}

            <Dispatch label="Ciphertext"  text={ciphertext} />

            <CipherWheel
              ciphertext={ciphertext}
              busy={busy}
              onSubmit={(reading) => {
                setDecryptAnswer(reading)
                void runDecrypt(reading)
              }}
            />

            <form onSubmit={submitDecrypt} noValidate style={{ marginTop: '1.5rem' }}>
              <div className="field">
                <label className="field-label" htmlFor="decrypt-answer">
                  Decrypted message
                </label>
                <span className="field-hint" id="decrypt-hint">
                  Type the message exactly as it should read. Capitals, spaces and punctuation are
                  ignored at the edges but kept in the middle.
                </span>
                <input
                  id="decrypt-answer"
                  className="input input-cipher"
                  value={decryptAnswer}
                  onChange={(event) => setDecryptAnswer(event.target.value)}
                  autoComplete="off"
                  spellCheck={false}
                  required
                  maxLength={500}
                  aria-describedby="decrypt-hint"
                  aria-invalid={decryptError ? true : undefined}
                />
              </div>

              {decryptError && (
                <div className="notice notice-error" role="alert">
                  <span className="notice-icon" aria-hidden="true">
                    ✕
                  </span>
                  <span className="notice-body">{decryptError}</span>
                </div>
              )}

              <div className="button-row" style={{ marginTop: '1rem' }}>
                <button type="submit" className="btn btn-primary" disabled={busy}>
                  {busy ? 'Checking…' : 'Submit decryption'}
                </button>
                <button
                  type="button"
                  className="btn btn-quiet"
                  onClick={revealSolution}
                  disabled={busy}
                >
                  Reveal the solution
                </button>
              </div>
            </form>
          </section>

          <HintPanel
            slug={slug}
            totalHints={brief.hint_count_total}
            hintsUsed={hintsUsed}
            initialHints={mission.revealedHints}
            onHintUsed={(hint) => {
              setHintsUsed(hint.hints_used)
              announce(`Hint ${hint.hint_number} revealed.`)
            }}
          />
        </div>
      )}

      {/* ---- stage: explanation ---- */}
      {stage === 'explanation' && solution && (
        <div className="stack">
          <section className="card" aria-labelledby="result-title">
            <h2 id="result-title">
              {score ? 'Correct — here is how it worked' : 'Solution revealed'}
            </h2>

            {score ? (
              <div role="status"></div>
            ) : (
              <div className="notice" role="status">
                <span className="notice-icon" aria-hidden="true">
                  ◍
                </span>
                <span className="notice-body">
                  <p style={{ margin: 0 }}>
                    <strong>Solution revealed.</strong> No solve points are awarded for a reveal,
                    but the worked example below is yours to read.
                  </p>
                </span>
              </div>
            )}

            <Dispatch label="Plaintext" meta="Recovered message" text={solution.plaintext} variant="plain" />

            {score && (
              <ScoreCard score={score} comprehensionAwarded={comprehension?.awarded ?? false} />
            )}

            <h3 style={{ fontSize: '1.15rem', marginTop: '1.5rem' }}>Why it works</h3>
            <p>{solution.explanation}</p>

            <h3 style={{ fontSize: '1.15rem' }}>Worked example</h3>
            <div className="panel worked-example">{solution.worked_example}</div>

            <div className="button-row" style={{ marginTop: '1.5rem' }}>
              {nextSlug && (
                <Link className="btn btn-primary" to={`/missions/${nextSlug}`}>
                  Next mission
                </Link>
              )}
              <button
                type="button"
                className="btn btn-secondary"
                onClick={() => void restartMission()}
                disabled={busy}
              >
                {busy ? 'Opening…' : 'Replay mission'}
              </button>
              <Link className="btn btn-secondary" to="/home">
                Home
              </Link>
            </div>
          </section>

          {score && !comprehension && mission.comprehensionCheck && (
            <ComprehensionCheck check={mission.comprehensionCheck} onAnswered={answerComprehension} />
          )}

          {comprehension && (
            <section className="card" aria-labelledby="check-result-title">
              <h3 id="check-result-title" style={{ fontSize: '1.15rem' }}>
                Comprehension check
              </h3>
              <div className = { comprehension.correct ? 'notice notice-success' : 'notice notice-error'} role="status">
                <span className="notice-icon" aria-hidden="true">
                  {comprehension.correct ? '✓' : '✕'}
                </span>
                <span className="notice-body">
                  <p style={{ margin: 0 }}>
                    <strong>{comprehension.correct ? 'Correct — 5 points added.' : 'Not this time.'}</strong>{' '}
                    {comprehension.explanation}
                  </p>
                </span>
              </div>
            </section>
          )}

          <section className="card" aria-labelledby="survey-section-title">
            <h2 id="survey-section-title" style={{ fontSize: '1.35rem' }}>
              Optional feedback
            </h2>
            <FeedbackSurvey missionSlug={brief.slug} />
          </section>
        </div>
      )}
    </>
  )
}

function ComprehensionCheck({
  check,
  onAnswered,
}: {
  check: ComprehensionCheckContent
  onAnswered: (choice: number) => Promise<void>
}) {
  return (
    <section className="card" aria-labelledby="check-title">
      <p className="eyebrow">Worth 5 points</p>
      <h3 id="check-title" style={{ fontSize: '1.15rem' }}>
        Check what you learned
      </h3>
      <p>{check.question}</p>
      <div className="choice-row">
        {check.choices.map((choice, index) => (
          <button
            key={choice}
            type="button"
            className="btn btn-secondary"
            onClick={() => void onAnswered(index)}
          >
            {choice}
          </button>
        ))}
      </div>
    </section>
  )
}

function nextOf(list: MissionListResponse, currentSlug: string): string | null {
  if (!list.missions.length) return null
  const index = list.missions.findIndex((mission) => mission.slug === currentSlug)
  if (index === -1) return list.missions[0].slug
  return list.missions[(index + 1) % list.missions.length].slug
}
