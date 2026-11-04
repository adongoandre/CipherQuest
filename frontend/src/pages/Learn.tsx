import { Link, useNavigate, useParams } from 'react-router-dom'
import { useState } from 'react'

import { PageHeader } from '../components/Layout'
import { ApiError, api } from '../lib/api'
import { useApi } from '../lib/useApi'

const STATUS_LABEL: Record<string, string> = {
  complete: 'Mastered',
  in_progress: 'In progress',
  not_started: 'Not started',
}

/** Cipher Academy: eight cipher tracks, each with a mastery bar and an entry point. */
export function LearnPage() {
  const { data, loading, error } = useApi(() => api.academy(), [])

  if (loading) return <p className="muted">Loading the academy…</p>
  if (error || !data) {
    return (
      <>
        <PageHeader title="Cipher Academy" />
        <p className="notice notice-error" role="alert">
          <span className="notice-icon" aria-hidden="true">
            ✕
          </span>
          <span className="notice-body">{error ?? 'The academy could not be loaded.'}</span>
        </p>
      </>
    )
  }

  return (
    <>
      <PageHeader
        title="Cipher Academy"
        subtitle="Learn each cipher step by step, then practise."
      />

      <div className="card-grid two">
        {data.tracks.map((track) => {
          const percent = track.lessons_total
            ? Math.round((track.lessons_completed / track.lessons_total) * 100)
            : 0
          const primary = track.status === 'in_progress'
          const action =
            track.status === 'complete' ? 'Review' : primary ? 'Continue' : 'Start'
          const step = Math.max(1, track.current_step)
          return (
            <section className="card" key={track.slug}>
              <div className="stat-line">
                <h2>{track.name}</h2>
              </div>
              <div className="stat-line">
                <span className="muted">Mastery</span>
                <span className={track.status === 'complete' ? 'status-on' : 'muted'}>
                  {STATUS_LABEL[track.status] ?? 'Not started'}
                </span>
              </div>
              <div
                className="progress-track"
                role="progressbar"
                aria-valuenow={percent}
                aria-valuemin={0}
                aria-valuemax={100}
                aria-label={`${track.name} mastery`}
              >
                <span style={{ width: `${percent}%` }} />
              </div>
              <p className="muted">{track.blurb}</p>
              <div className="button-row">
                <Link
                  className={`btn ${primary ? 'btn-primary' : 'btn-secondary'}`}
                  to={`/learn/${track.slug}/${step}`}
                >
                  {action}
                </Link>
              </div>
            </section>
          )
        })}
      </div>

      <p className="muted">
        {data.total_lessons_completed} of {data.total_lessons} lessons complete.
      </p>
    </>
  )
}

function caesar(text: string, shift: number): string {
  const normalized = ((shift % 26) + 26) % 26
  return text.replace(/[a-z]/gi, (char) => {
    const base = char <= 'Z' ? 65 : 97
    return String.fromCharCode(((char.charCodeAt(0) - base + normalized) % 26) + base)
  })
}

/** A single lesson: progress, the teaching card with its worked example, prev/next. */
export function LessonPage() {
  const { slug = '', step = '1' } = useParams()
  const stepNumber = Number(step) || 1
  const navigate = useNavigate()
  const { data, loading, error } = useApi(
    async () => {
      const [lesson, track] = await Promise.all([
        api.lesson(slug, stepNumber),
        api.trackDetail(slug),
      ])
      return { lesson, track }
    },
    [slug, stepNumber],
  )
  const [shift, setShift] = useState(3)
  const [busy, setBusy] = useState(false)
  const [xpNote, setXpNote] = useState<string | null>(null)

  if (loading) return <p className="muted">Opening the lesson…</p>
  if (error || !data) {
    return (
      <>
        <PageHeader title="Lesson" />
        <p className="notice notice-error" role="alert">
          <span className="notice-icon" aria-hidden="true">
            ✕
          </span>
          <span className="notice-body">{error ?? 'That lesson could not be loaded.'}</span>
        </p>
        <Link className="btn btn-secondary" to="/learn">
          Back to Cipher Academy
        </Link>
      </>
    )
  }

  const { lesson, track } = data
  const nextLesson = lesson.next_step
    ? track.lessons.find((item) => item.step === lesson.next_step)
    : undefined
  const percent = lesson.total_steps
    ? Math.round((lesson.step / lesson.total_steps) * 100)
    : 0

  async function advance() {
    setBusy(true)
    try {
      const result = await api.completeLesson(slug, lesson.step)
      if (result.completed) setXpNote(`+${result.xp_awarded} XP earned`)
      if (lesson.next_step) {
        navigate(`/learn/${slug}/${lesson.next_step}`)
      } else {
        navigate('/learn')
      }
    } catch (e) {
      setXpNote(e instanceof ApiError ? e.message : 'Could not save your progress.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <>
      <PageHeader
        title={`${lesson.track_name}: Lesson ${lesson.step} of ${lesson.total_steps}`}
        subtitle={lesson.title}
      />

      <section className="card" aria-label="Lesson progress">
        <div className="stat-line">
          <span>Lesson progress</span>
          <span className="muted">
            {lesson.step} of {lesson.total_steps}
          </span>
        </div>
        <div
          className="progress-track"
          role="progressbar"
          aria-valuenow={percent}
          aria-valuemin={0}
          aria-valuemax={100}
          aria-label="Lesson progress"
        >
          <span style={{ width: `${percent}%` }} />
        </div>
      </section>
      <br />
      <section className="card" aria-labelledby="lesson-body">
        <h2 id="lesson-body">{lesson.title}</h2>
        {lesson.body.map((paragraph, index) => (
          <p key={index}>{paragraph}</p>
        ))}

        {lesson.example && <LessonExampleCard example={lesson.example} shift={shift} onShift={setShift} />}

        {xpNote && <p className="muted">{xpNote}</p>}
      </section>

      <div className="lesson-nav">
        <button
          type="button"
          className="btn btn-secondary"
          disabled={lesson.step <= 1 || busy}
          onClick={() => navigate(`/learn/${slug}/${lesson.step - 1}`)}
        >
          Previous
        </button>
        <button type="button" className="btn btn-primary" disabled={busy} onClick={advance}>
          {busy
            ? 'Saving…'
            : lesson.next_step
              ? `Next: ${nextLesson?.title ?? `Lesson ${lesson.next_step}`}`
              : 'Finish lesson'}
        </button>
      </div>
    </>
  )
}

function LessonExampleCard({
  example,
  shift,
  onShift,
}: {
  example: import('../lib/api').LessonExample
  shift: number
  onShift: (value: number) => void
}) {
  const interactive = example.interactive === 'shift'

  return (
    <div className="example">
      {interactive ? (
        <>
          <label className="field-label" htmlFor="shift-input">
            Try a shift (1–25)
          </label>
          <input
            id="shift-input"
            type="number"
            min={1}
            max={25}
            value={shift}
            onChange={(e) => onShift(Math.min(25, Math.max(1, Number(e.target.value) || 1)))}
            className="shift-input"
          />
          <p className="ciphertext demo-line">
            {example.sample_text ?? 'HELLO'} <span aria-hidden="true">→</span>{' '}
            <span className="demo-result">
              {caesar(example.sample_text ?? 'HELLO', shift)}
            </span>
          </p>
          {example.caption && <p className="muted">{example.caption}</p>}
        </>
      ) : (
        <>
          <p className="ciphertext demo-line">
            {example.input} <span aria-hidden="true">→</span>{' '}
            <span className="demo-result">{example.output}</span>
          </p>
          {example.caption && <p className="muted">{example.caption}</p>}
        </>
      )}
    </div>
  )
}