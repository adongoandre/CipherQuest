import { useEffect, useState } from 'react'

import { decodeCaesar, encodeCaesar, normaliseShift } from '../lib/caesar'

/**
 * The cipher lab: a free-play Caesar tool.
 *
 * The wheel follows the input → output pairing of whatever mode is selected,
 * so the inner ring always shows where each outer letter lands: forward by the
 * shift when encrypting, back by the shift when decrypting. The hub reports
 * that same signed rotation. Everything runs in the browser — nothing typed
 * here is sent anywhere.
 */

type Mode = 'encrypt' | 'decrypt'

const ALPHABET = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
const STEP = 360 / ALPHABET.length
const CX = 180
const CY = 180
const R_OUTER = 150
const R_INNER = 110
const R_BADGE_OUTER = 14
const R_BADGE_INNER = 12.5
const R_HUB = 60

function pointOnCircle(position: number, radius: number): { x: number; y: number } {
  const angle = ((position * STEP - 90) * Math.PI) / 180
  return { x: CX + radius * Math.cos(angle), y: CY + radius * Math.sin(angle) }
}

const MODES: { value: Mode; label: string }[] = [
  { value: 'encrypt', label: 'Encrypt' },
  { value: 'decrypt', label: 'Decrypt' },
]

export function CipherPage() {
  const [source, setSource] = useState('HELLO WORLD')
  const [shift, setShift] = useState(3)
  const [mode, setMode] = useState<Mode>('decrypt')

  useEffect(() => {
    document.title = 'Try the Caesar Cipher — CipherQuest'
  }, [])

  const translation =
    mode === 'decrypt' ? decodeCaesar(source, shift) : encodeCaesar(source, shift)

  /** Signed rotation of the operation: back by the shift, or forward by it. */
  const rotation = mode === 'decrypt' ? -shift : shift

  /** Where the inner ring physically sits, in letter steps. */
  const discRotation = -rotation

  const outerLetters = ALPHABET.split('').map((letter, position) => {
    const { x, y } = pointOnCircle(position, R_OUTER)
    return (
      <g key={`o-${letter}`}>
        <circle className="caesar-badge-outer" cx={x} cy={y} r={R_BADGE_OUTER} />
        <text className="caesar-letter-outer" x={x} y={y}>
          {letter}
        </text>
      </g>
    )
  })

  const innerLetters = ALPHABET.split('').map((letter, position) => {
    const { x, y } = pointOnCircle(position, R_INNER)
    return (
      <g key={`i-${letter}`}>
        <circle className="caesar-badge-inner" cx={x} cy={y} r={R_BADGE_INNER} />
        <text className="caesar-letter-inner" x={x} y={y}>
          {letter}
        </text>
      </g>
    )
  })

  return (
    <section aria-labelledby="caesar-title">
      <p className="eyebrow">Cipher lab</p>
      <h1 id="caesar-title">Try the Caesar Cipher</h1>
      <p className="muted">
        Type a message, set the shift, and watch every letter land on the ring below. It all runs
        in this page — nothing you type is sent anywhere.
      </p>

      <div className="caesar-stage">
        <p className="caesar-ring-label">Plaintext (Outer)</p>

        <div className="caesar-stage-wheel">
          <svg className="caesar-wheel-svg" viewBox="0 0 360 360" aria-hidden="true">
            <g>{outerLetters}</g>

            <g
              className="caesar-wheel-disc"
              data-rotation={discRotation}
              style={{
                transform: `rotate(${discRotation * STEP}deg)`,
                transformOrigin: `${CX}px ${CY}px`,
              }}
            >
              {innerLetters}
            </g>

            <circle className="caesar-hub" cx={CX} cy={CY} r={R_HUB} />
            <text className="caesar-hub-label" x={CX} y={CY - 12}>
              ROTATION
            </text>
            <text className="caesar-hub-value" x={CX} y={CY + 20} data-testid="caesar-rotation">
              {rotation}
            </text>
          </svg>
        </div>

        <p className="caesar-ring-label caesar-ring-label-inner">Ciphertext (Inner)</p>
      </div>

      <div className="caesar-summary">
        <div>
          <span className="caesar-summary-label">Input text</span>
          <span className="caesar-summary-value" data-testid="caesar-input">
            {source || '—'}
          </span>
        </div>
        <div>
          <span className="caesar-summary-label">Translation</span>
          <span className="caesar-summary-value caesar-summary-value-out" data-testid="caesar-translation">
            {translation || '—'}
          </span>
        </div>
      </div>

      <div className="caesar-controls">
        <div className="field">
          <label className="field-label" htmlFor="caesar-source">
            Source string
          </label>
          <input
            id="caesar-source"
            className="input input-cipher"
            type="text"
            value={source}
            onChange={(event) => setSource(event.target.value)}
            autoComplete="off"
            spellCheck={false}
          />
        </div>

        <div className="field">
          <label className="field-label" htmlFor="caesar-shift">
            Shift magnitude
          </label>
          <div className="caesar-slider-row">
            <input
              id="caesar-shift"
              className="caesar-slider"
              type="range"
              min={0}
              max={25}
              step={1}
              value={shift}
              aria-valuetext={`Shift ${shift} letters`}
              onChange={(event) => setShift(normaliseShift(Number(event.target.value)))}
            />
            <output className="caesar-slider-value" htmlFor="caesar-shift">
              {shift}
            </output>
          </div>
        </div>

        <div className="field">
          <span className="field-label" id="caesar-mode-label">
            Cryptographic mode
          </span>
          <div className="caesar-modes" role="group" aria-labelledby="caesar-mode-label">
            {MODES.map(({ value, label }) => (
              <button
                key={value}
                type="button"
                className="caesar-mode"
                aria-pressed={mode === value}
                onClick={() => setMode(value)}
              >
                {label}
              </button>
            ))}
          </div>
        </div>
      </div>

      <p className="field-hint caesar-note">
        Educational only — classical ciphers are not real security. Don&apos;t enter sensitive
        personal info.
      </p>
    </section>
  )
}