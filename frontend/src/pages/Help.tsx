import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'

import { api, type HealthResponse } from '../lib/api'

function ApiStatus() {
  const [health, setHealth] = useState<HealthResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [checking, setChecking] = useState(true)

  useEffect(() => {
    let cancelled = false
    api
      .health()
      .then((result) => {
        if (!cancelled) setHealth(result)
      })
      .catch((err: unknown) => {
        if (cancelled) return
        setHealth(null)
        setError(err instanceof Error ? err.message : 'The API did not answer.')
      })
      .finally(() => {
        if (!cancelled) setChecking(false)
      })
    return () => {
      cancelled = true
    }
  }, [])

  function recheck() {
    setChecking(true)
    setHealth(null)
    setError(null)
    api
      .health()
      .then(setHealth)
      .catch((err: unknown) => {
        setHealth(null)
        setError(err instanceof Error ? err.message : 'The API did not answer.')
      })
      .finally(() => setChecking(false))
  }

  return (
    <section className="panel" aria-labelledby="status-title">
      <h3 id="status-title" style={{ fontSize: '1.1rem', marginBottom: '0.4em' }}>
        Connection status
      </h3>

      {checking && (
        <p className="muted" role="status">
          Checking the API…
        </p>
      )}

      {!checking && health && (
        <div className="notice notice-success" role="status">
          <span className="notice-icon" aria-hidden="true">
            ✓
          </span>
          <span className="notice-body">
            <p style={{ margin: 0 }}>
              <strong>Connected.</strong> API {health.version} · {health.app_env} ·{' '}
              {health.database} · {new Date(health.time).toLocaleTimeString()}
            </p>
          </span>
        </div>
      )}

      {!checking && error && (
        <div className="notice notice-error" role="alert">
          <span className="notice-icon" aria-hidden="true">
            ✕
          </span>
          <div className="notice-body">
            <p style={{ margin: '0 0 0.5rem' }}>
              <strong>Not reachable.</strong> {error}
            </p>
            <p className="muted" style={{ margin: 0 }}>
              If you are developing locally, start the backend with{' '}
              <code>uvicorn app.main:app --reload</code> from <code>backend/</code>.
            </p>
          </div>
        </div>
      )}

      <div className="button-row" style={{ marginTop: '0.75rem' }}>
        <button type="button" className="btn btn-secondary" onClick={recheck}>
          Check again
        </button>
      </div>
    </section>
  )
}

const ACCESSIBILITY = [
  'Every action can be completed with the keyboard alone — Tab to move, Enter to submit.',
  'Focus is always visible, with a high-contrast outline on interactive controls.',
  'Success and failure are shown with words and icons, never colour alone.',
  'Body text never drops below 17px, and the layout reflows down to a 320px viewport.',
  'Animations are switched off entirely if your system asks for reduced motion.',
  'Practice is untimed. No mission requires speed, and there is no countdown to fight.',
  'The mission reads its own progress through a polite screen-reader announcement region.',
]

const PRIVACY = [
  'No account, name, email or password is ever requested.',
  'A random pseudonymous identifier is stored in this tab to remember your progress; closing the tab discards it.',
  'Analytics record whether a submission was right or wrong — never what you typed.',
  'Typed answers, comments and free text are never written to analytics events.',
  'Feedback surveys are optional and reviewed only in aggregate.',
]

export function HelpPage() {
  useEffect(() => {
    document.title = 'Help & accessibility — CipherQuest'
  }, [])

  return (
    <>
      <p className="eyebrow">Help</p>
      <h1>How to play, and what we promise</h1>

      <ApiStatus />

      <hr className="rule" />

      <section className="prose" aria-labelledby="play-title">
        <h2 id="play-title">How to play a mission</h2>
        <ol className="steps" style={{ gridTemplateColumns: '1fr' }}>
          <li className="step">
            <h3>Read the briefing</h3>
            <p>The story tells you where the message came from and which cipher was used.</p>
          </li>
          <li className="step">
            <h3>Answer the riddle</h3>
            <p>Type your answer and press Enter. A wrong answer simply tries again.</p>
          </li>
          <li className="step">
            <h3>Read the key rule</h3>
            <p>
              The game explains exactly how your answer becomes a number. For a Caesar cipher that
              number is the shift.
            </p>
          </li>
          <li className="step">
            <h3>Read the clue, then decrypt</h3>
            <p>
              The clue says what the message is about. Turn the decoder wheel to your shift and read
              the message off it, or type the decrypted words and submit. Three hints are available
              if you want them.
            </p>
          </li>
          <li className="step">
            <h3>Check the explanation</h3>
            <p>You get the plaintext, a worked letter-by-letter example, and a scored breakdown.</p>
          </li>
        </ol>
        <p>
          <Link className="btn btn-primary" to="/missions">
            Browse missions
          </Link>
        </p>
      </section>

      <hr className="rule" />

      <section className="prose" aria-labelledby="a11y-title">
        <h2 id="a11y-title">Accessibility</h2>
        <ul>
          {ACCESSIBILITY.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
        <p className="muted">
          Something not working for you? It is a bug — the mission loop must be completable with a
          keyboard, a screen reader, and at 200% text size.
        </p>
      </section>

      <section className="prose" aria-labelledby="privacy-title">
        <h2 id="privacy-title">Privacy</h2>
        <ul>
          {PRIVACY.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      </section>

      <section className="prose" aria-labelledby="disclaimer-title">
        <div className="notice notice-error">
          <span className="notice-icon" aria-hidden="true">
            !
          </span>
          <div className="notice-body">
            <p style={{ margin: '0 0 0.5rem' }}>
              <strong id="disclaimer-title">Educational use only.</strong>
            </p>
            <p style={{ margin: 0 }}>
              Caesar, Atbash and every other classical cipher taught here are historical curiosities.
              They will not protect a password, a message, or anything else that matters. Use real
              modern encryption for anything you actually need to keep secret.
            </p>
          </div>
        </div>
      </section>
    </>
  )
}
