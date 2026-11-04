import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'

import { ApiError } from '../lib/api'
import { api } from '../lib/api'

/**
 * Decorative specimen only — this string belongs to no published mission, so
 * no real answer can leak from the landing page.
 */
const SPECIMEN = 'A SECRET WAITS INSIDE'
const SPECIMEN_SHIFT = 3

function shiftText(text: string, shift: number): string {
  return text.replace(/[a-z]/gi, (char) => {
    const base = char <= 'Z' ? 65 : 97
    return String.fromCharCode(((char.charCodeAt(0) - base + shift) % 26) + base)
  })
}

function SpecimenDispatch() {
  const cipher = shiftText(SPECIMEN, SPECIMEN_SHIFT)
  return (
    <div className="dispatch" aria-hidden="true">
      <div className="dispatch-label">
        <span>Specimen ciphertext</span>
        <span>Caesar · shift {SPECIMEN_SHIFT}</span>
      </div>
      <p className="ciphertext">
        {cipher.split('').map((char, index) => (
          <span
            key={`${char}-${index}`}
            className="decode-letter"
            style={{ animationDelay: `${index * 45}ms` }}
          >
            {char === ' ' ? '\u00A0' : char}
          </span>
        ))}
      </p>
    </div>
  )
}

function SampleMissionButton({ className = 'btn btn-primary' }: { className?: string }) {
  const navigate = useNavigate()
  const [state, setState] = useState<'idle' | 'loading' | 'error'>('idle')

  async function play() {
    setState('loading')
    try {
      const daily = await api.daily()
      navigate(`/missions/${daily.slug}`)
    } catch (error) {
      setState('error')
      if (error instanceof ApiError) {
        // fall through to the error message below
      }
    }
  }

  return (
    <div>
      <div className="button-row hero-actions">
        <button type="button" className={className} onClick={play} disabled={state === 'loading'}>
          {state === 'loading' ? 'Preparing your mission…' : 'Play a sample mission'}
        </button>
        <Link className="btn btn-secondary" to="/missions">
          See all five missions
        </Link>
      </div>
      {state === 'error' && (
        <p className="notice notice-error" role="alert">
          <span className="notice-icon" aria-hidden="true">
            ✕
          </span>
          <span className="notice-body">
            The missions could not be loaded. Check that the API is running, then try again.
          </span>
        </p>
      )}
    </div>
  )
}

const STEPS = [
  {
    title: 'Solve a riddle',
    body: 'Every mission opens with a short story and one riddle. Its answer is the way in.',
  },
  {
    title: 'Discover the key',
    body: 'A stated rule turns your riddle answer into a cipher parameter — a number you can actually use.',
  },
  {
    title: 'Decode the secret',
    body: 'Read the context clue, shift the letters, and submit what the message says.',
  },
]

const HOW_IT_WORKS = [
  {
    heading: 'The briefing',
    body: 'You get a short mystery: where the message came from, what cipher was used, and roughly how long it takes.',
  },
  {
    heading: 'The riddle and the key rule',
    body: 'Solve the riddle and the game explains exactly how your answer becomes the key. For a Caesar cipher the key is always a number — never the word itself.',
  },
  {
    heading: 'The context clue',
    body: 'A separate clue tells you what the hidden message is about, without ever showing you the words.',
  },
  {
    heading: 'The decryption',
    body: 'You get the ciphertext, the parameter, and a decoder wheel — turn it until the message reads, or type it out. Three optional hints; practice is untimed by default.',
  },
  {
    heading: 'The explanation',
    body: 'You are shown the plaintext, a worked letter-by-letter example, and your score broken down into parts.',
  },
]

export function LandingPage() {
  useEffect(() => {
    document.title = 'CipherQuest — Crack the code. Solve the riddle. Unlock the message.'
    return () => {
      document.title = 'CipherQuest'
    }
  }, [])

  return (
    <>
      <section className="hero" aria-labelledby="hero-title">
        <div>
          <p className="eyebrow">Classical cryptography, playable</p>
          <h1 id="hero-title">Crack the code. Solve the riddle. Unlock the message.</h1>
          <p className="hero-tagline">A mystery you decrypt, one letter at a time.</p>
          <p className="lead">
            CipherQuest teaches real classical encryption through short mysteries. No account, no
            timer, no pressure — just a riddle, a key, a clue, and a message waiting to be read.
          </p>
          <SampleMissionButton />
        </div>
        <SpecimenDispatch />
      </section>

      <section aria-labelledby="steps-title" style={{ paddingTop: 'clamp(2rem, 5vw, 3rem)' }}>
        <p className="eyebrow">Three moves</p>
        <h2 id="steps-title">How you play</h2>
        <ol className="steps">
          {STEPS.map((step) => (
            <li className="step" key={step.title}>
              <h3>{step.title}</h3>
              <p>{step.body}</p>
            </li>
          ))}
        </ol>
      </section>

      <hr className="rule" />

      <section aria-labelledby="how-title" className="prose">
        <p className="eyebrow">How it works</p>
        <h2 id="how-title">Every mission runs the same loop</h2>
        <p className="muted">
          The loop is deliberately short so you can finish a mission in a few minutes and still
          understand what you just did.
        </p>
        <div className="stack">
          {HOW_IT_WORKS.map((item) => (
            <div className="panel" key={item.heading}>
              <h3 style={{ fontSize: '1.15rem', marginBottom: '0.3em' }}>{item.heading}</h3>
              <p style={{ margin: 0 }} className="muted">
                {item.body}
              </p>
            </div>
          ))}
        </div>
      </section>

      <hr className="rule" />

      <section className="prose" aria-labelledby="promise-title">
        <p className="eyebrow">Our promises</p>
        <h2 id="promise-title">Free to try, safe to ignore, easy to read</h2>
        <ul>
          <li>
            <strong>No registration</strong> to play a sample mission — you get a pseudonymous
            session automatically.
          </li>
          <li>
            <strong>Untimed by default.</strong> Speed is never the point, and every mission can be
            finished at your own pace.
          </li>
          <li>
            <strong>Keyboard first.</strong> Every action is reachable by Tab and Enter, with a
            visible focus ring throughout.
          </li>
          <li>
            <strong>Educational only.</strong> Classical ciphers are wonderful for learning and
            useless for real secrets.
          </li>
        </ul>
        <p>
          Full details live on the <Link to="/help">help and accessibility page</Link>.
        </p>
      </section>
    </>
  )
}
