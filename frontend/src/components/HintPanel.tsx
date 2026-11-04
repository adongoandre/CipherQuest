import { useState } from 'react'

import { api, type HintResponse } from '../lib/api'

interface HintPanelProps {
  slug: string
  totalHints: number
  hintsUsed: number
  /** Hints this session already earned, restored when the page reloads. */
  initialHints: string[]
  onHintUsed: (hint: HintResponse) => void
  disabled?: boolean
}

/**
 * Hints reveal one at a time. Usage is tracked server-side; this panel only
 * reflects what the server returns.
 */
export function HintPanel({
  slug,
  totalHints,
  hintsUsed,
  initialHints,
  onHintUsed,
  disabled = false,
}: HintPanelProps) {
  const [revealed, setRevealed] = useState<Array<{ number: number; text: string }>>(() =>
    initialHints.map((text, index) => ({ number: index + 1, text })),
  )
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  const used = Math.max(hintsUsed, revealed.length)
  const exhausted = used >= totalHints

  async function reveal() {
    setBusy(true)
    setError(null)
    try {
      const hint = await api.hint(slug)
      setRevealed((current) => [...current, { number: hint.hint_number, text: hint.hint }])
      onHintUsed(hint)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'The hint could not be loaded.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <section className="panel" aria-labelledby="hints-title">
      <h3 id="hints-title" style={{ fontSize: '1.1rem', marginBottom: '0.35em' }}>
        Hints
      </h3>
      <p className="muted" style={{ marginBottom: '0.75rem' }}>
        {used} of {totalHints} used. Hints are free, but they cost the 10-point no-hint bonus.
      </p>

      <div className="button-row">
        <button
          type="button"
          className="btn btn-secondary"
          onClick={reveal}
          disabled={busy || exhausted || disabled}
        >
          {busy
            ? 'Loading hint…'
            : exhausted
              ? 'All hints used'
              : `Reveal hint ${used + 1} of ${totalHints}`}
        </button>
      </div>

      {error && (
        <p className="notice notice-error" role="alert">
          <span className="notice-icon" aria-hidden="true">
            ✕
          </span>
          <span className="notice-body">{error}</span>
        </p>
      )}

      {revealed.length > 0 && (
        <ul className="hint-list">
          {revealed.map((hint) => (
            <li className="hint-item" key={hint.number}>
              <strong>Hint {hint.number}</strong>
              {hint.text}
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}
