import { useMemo, useRef, useState } from 'react'

import { decodeCaesar, normaliseShift } from '../lib/caesar'

/**
 * The decoder wheel: the graphical way to solve a Caesar cipher.
 *
 * Two concentric alphabet rings — the outer reading ring is fixed, the inner
 * ciphertext ring turns with the shift. Find a ciphertext letter on the inner
 * ring and read the outer letter above it to recover the plaintext. The live
 * reading under the wheel always shows what the current position produces, so
 * the player can turn until the message makes sense and then submit it.
 */

const ALPHABET = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
const STEP = 360 / ALPHABET.length
const CX = 180
const CY = 180
const R_OUTER = 150
const R_TICK = 132
const R_INNER = 111
const R_HUB = 62

function pointOnCircle(position: number, radius: number): { x: number; y: number } {
  const angle = ((position * STEP - 90) * Math.PI) / 180
  return { x: CX + radius * Math.cos(angle), y: CY + radius * Math.sin(angle) }
}

interface CipherWheelProps {
  ciphertext: string
  busy?: boolean
  onSubmit: (reading: string) => void
}

export function CipherWheel({ ciphertext, busy = false, onSubmit }: CipherWheelProps) {
  const [shift, setShift] = useState(0)
  const [dragging, setDragging] = useState(false)
  const svgRef = useRef<SVGSVGElement>(null)
  const dragRef = useRef<{ startAngle: number; startShift: number } | null>(null)

  const reading = useMemo(() => decodeCaesar(ciphertext, shift), [ciphertext, shift])

  const cipherLetters = useMemo(() => {
    const set = new Set<string>()
    for (const ch of ciphertext.toUpperCase()) {
      if (ALPHABET.includes(ch)) set.add(ch)
    }
    return set
  }, [ciphertext])

  function pointerAngle(clientX: number, clientY: number): number {
    const svg = svgRef.current
    if (!svg) return 0
    const rect = svg.getBoundingClientRect()
    const scale = rect.width / (CX * 2)
    const x = (clientX - rect.left) / scale - CX
    const y = (clientY - rect.top) / scale - CY
    return (Math.atan2(y, x) * 180) / Math.PI
  }

  function handlePointerDown(event: React.PointerEvent<SVGSVGElement>) {
    // Touch users get the slider instead — dragging here would fight scrolling.
    if (event.pointerType === 'touch') return
    event.preventDefault()
    event.currentTarget.setPointerCapture(event.pointerId)
    dragRef.current = { startAngle: pointerAngle(event.clientX, event.clientY), startShift: shift }
    setDragging(true)
  }

  function handlePointerMove(event: React.PointerEvent<SVGSVGElement>) {
    const drag = dragRef.current
    if (!drag) return
    const delta = pointerAngle(event.clientX, event.clientY) - drag.startAngle
    const wrapped = ((delta % 360) + 540) % 360 - 180
    setShift(normaliseShift(drag.startShift + Math.round(wrapped / STEP)))
  }

  function handlePointerEnd(event: React.PointerEvent<SVGSVGElement>) {
    if (!dragRef.current) return
    dragRef.current = null
    setDragging(false)
    if (event.currentTarget.hasPointerCapture(event.pointerId)) {
      event.currentTarget.releasePointerCapture(event.pointerId)
    }
  }

  const outerLetters = ALPHABET.split('').map((letter, position) => {
    const { x, y } = pointOnCircle(position, R_OUTER)
    return (
      <text key={`o-${letter}`} className="wheel-letter wheel-letter-outer" x={x} y={y}>
        {letter}
      </text>
    )
  })

  const innerLetters = ALPHABET.split('').map((letter, position) => {
    const { x, y } = pointOnCircle(position, R_INNER)
    const hot = cipherLetters.has(letter)
    return (
      <text
        key={`i-${letter}`}
        className={`wheel-letter wheel-letter-inner${hot ? ' wheel-letter-hot' : ''}`}
        x={x}
        y={y}
      >
        {letter}
      </text>
    )
  })

  const ticks = Array.from({ length: 26 }, (_, position) => {
    const a = pointOnCircle(position, R_TICK - 5)
    const b = pointOnCircle(position, R_TICK + 5)
    return <line key={`t-${position}`} className="wheel-tick" x1={a.x} y1={a.y} x2={b.x} y2={b.y} />
  })

  return (
    <section className="wheel" aria-label="Decoder wheel">
      <h3 className="wheel-title">The decoder wheel</h3>

      <div className="wheel-stage">
        <svg
          ref={svgRef}
          className={`wheel-svg${dragging ? ' is-dragging' : ''}`}
          viewBox="0 0 360 360"
          aria-hidden="true"
          onPointerDown={handlePointerDown}
          onPointerMove={handlePointerMove}
          onPointerUp={handlePointerEnd}
          onPointerCancel={handlePointerEnd}
        >
          {/* index marker */}
          <polygon className="wheel-index" points={`${CX},14 ${CX - 9},0 ${CX + 9},0`} />
          <line className="wheel-index-line" x1={CX} y1={16} x2={CX} y2={CY - R_HUB - 4} />

          <circle className="wheel-ring" cx={CX} cy={CY} r={R_OUTER} />
          <circle className="wheel-ring wheel-ring-inner" cx={CX} cy={CY} r={R_INNER + 14} />
          <circle className="wheel-ring wheel-ring-hub" cx={CX} cy={CY} r={R_HUB} />
          {ticks}

          {/* outer ring: the fixed reading alphabet */}
          <g>{outerLetters}</g>

          {/* inner ring: ciphertext letters, turned by the shift */}
          <g
            className="wheel-disc"
            style={{
              transform: `rotate(${-shift * STEP}deg)`,
              transformOrigin: `${CX}px ${CY}px`,
              transition: dragging ? 'none' : 'transform 220ms cubic-bezier(0.22, 1, 0.36, 1)',
            }}
          >
            {innerLetters}
          </g>

          <text className="wheel-hub-label" x={CX} y={CY - 12}>
            SHIFT
          </text>
          <text className="wheel-hub-value" x={CX} y={CY + 20}>
            {shift}
          </text>
          <text className="wheel-hub-unit" x={CX} y={CY + 40}>
            letters
          </text>
        </svg>
      </div>

      <div className="wheel-legend">
        <span>
          <span className="wheel-dot wheel-dot-outer" aria-hidden="true" /> Outer ring — the reading
        </span>
        <span>
          <span className="wheel-dot wheel-dot-inner" aria-hidden="true" /> Inner ring — ciphertext
        </span>
      </div>

      <div className="wheel-readings">
        <div className="wheel-row">
          <span className="wheel-row-label">Ciphertext</span>
          <span className="wheel-row-text" data-testid="wheel-ciphertext">
            {ciphertext}
          </span>
        </div>
        <div className="wheel-row">
          <span className="wheel-row-label">Reading</span>
          <span className="wheel-row-text wheel-row-reading" data-testid="wheel-reading">
            {reading}
          </span>
        </div>
      </div>

      <div className="wheel-controls">
        <label className="field-label" htmlFor="wheel-shift">
          Turn the wheel
        </label>
        <input
          id="wheel-shift"
          className="wheel-slider"
          type="range"
          min={0}
          max={25}
          step={1}
          value={shift}
          aria-valuetext={`Shift ${shift} letters`}
          onChange={(event) => setShift(normaliseShift(Number(event.target.value)))}
        />
        <output className="wheel-value" htmlFor="wheel-shift">
          {shift}
        </output>
      </div>

      <p className="field-hint">
        Set the wheel to the shift you derived, then read across — find a ciphertext letter on the
        inner ring and the outer letter above it is the plaintext. Drag the wheel or slide it; the
        reading updates as you turn.
      </p>

      <div className="button-row" style={{ marginTop: '0.75rem' }}>
        <button
          type="button"
          className="btn btn-primary"
          onClick={() => onSubmit(reading)}
          disabled={busy}
        >
          {busy ? 'Checking…' : 'Check this reading'}
        </button>
      </div>
    </section>
  )
}
