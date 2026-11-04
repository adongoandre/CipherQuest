import { useState } from 'react'

import { api, type FeedbackPayload } from '../lib/api'

interface FeedbackSurveyProps {
  missionSlug: string
}

const SCALE = [1, 2, 3, 4, 5] as const

function ScaleGroup({
  name,
  legend,
  value,
  onChange,
}: {
  name: string
  legend: string
  value: number | null
  onChange: (value: number) => void
}) {
  return (
    <fieldset>
      <legend>{legend}</legend>
      <div className="choice-row">
        {SCALE.map((option) => (
          <label className="choice" key={option}>
            <input
              type="radio"
              name={name}
              value={option}
              checked={value === option}
              onChange={() => onChange(option)}
            />
            {option}
          </label>
        ))}
      </div>
      <p className="field-hint" style={{ marginTop: '0.5rem', marginBottom: 0 }}>
        1 = not at all, 5 = completely
      </p>
    </fieldset>
  )
}

function ChoiceGroup<T extends string>({
  name,
  legend,
  options,
  value,
  onChange,
}: {
  name: string
  legend: string
  options: Array<{ value: T; label: string }>
  value: T | null
  onChange: (value: T) => void
}) {
  return (
    <fieldset>
      <legend>{legend}</legend>
      <div className="choice-row">
        {options.map((option) => (
          <label className="choice" key={option.value}>
            <input
              type="radio"
              name={name}
              value={option.value}
              checked={value === option.value}
              onChange={() => onChange(option.value)}
            />
            {option.label}
          </label>
        ))}
      </div>
    </fieldset>
  )
}

/** Optional short survey (MVP Master Prompt §11). */
export function FeedbackSurvey({ missionSlug }: FeedbackSurveyProps) {
  const [clarity, setClarity] = useState<number | null>(null)
  const [learned, setLearned] = useState<'yes' | 'a_little' | 'no' | null>(null)
  const [enjoyment, setEnjoyment] = useState<number | null>(null)
  const [wouldReturn, setWouldReturn] = useState<'yes' | 'maybe' | 'no' | null>(null)
  const [comment, setComment] = useState('')
  const [status, setStatus] = useState<'idle' | 'sending' | 'saved' | 'error'>('idle')
  const [error, setError] = useState<string | null>(null)

  const answered = clarity !== null || learned !== null || enjoyment !== null || wouldReturn !== null || comment.trim() !== ''

  async function submit(event: React.FormEvent) {
    event.preventDefault()
    if (!answered) {
      setStatus('error')
      setError('Answer at least one question before sending.')
      return
    }

    setStatus('sending')
    setError(null)
    const payload: FeedbackPayload = {
      mission_slug: missionSlug,
      clarity_rating: (clarity as 1 | 2 | 3 | 4 | 5 | null) ?? undefined,
      learned: learned ?? undefined,
      enjoyment_rating: (enjoyment as 1 | 2 | 3 | 4 | 5 | null) ?? undefined,
      would_return: wouldReturn ?? undefined,
      comment: comment.trim() ? comment.trim() : undefined,
    }

    try {
      await api.feedback(payload)
      setStatus('saved')
    } catch (err) {
      setStatus('error')
      setError(err instanceof Error ? err.message : 'Your feedback could not be sent.')
    }
  }

  if (status === 'saved') {
    return (
      <div className="notice notice-success" role="status">
        <span className="notice-icon" aria-hidden="true">
          ✓
        </span>
        <span className="notice-body">
          Thank you — your feedback was recorded. It is reviewed in aggregate only.
        </span>
      </div>
    )
  }

  return (
    <form className="survey" onSubmit={submit} noValidate aria-labelledby="survey-title">
      <h3 id="survey-title" style={{ fontSize: '1.2rem' }}>
        How was that mission?
      </h3>
      <p className="muted">Completely optional. Nothing here is tied to your name.</p>

      <ScaleGroup
        name="clarity"
        legend="1. Was the mission easy to understand?"
        value={clarity}
        onChange={setClarity}
      />

      <ChoiceGroup<'yes' | 'a_little' | 'no'>
        name="learned"
        legend="2. Did you learn something?"
        options={[
          { value: 'yes', label: 'Yes' },
          { value: 'a_little', label: 'A little' },
          { value: 'no', label: 'No' },
        ]}
        value={learned}
        onChange={setLearned}
      />

      <ScaleGroup
        name="enjoyment"
        legend="3. How enjoyable was it?"
        value={enjoyment}
        onChange={setEnjoyment}
      />

      <div className="field">
        <label className="field-label" htmlFor="survey-comment">
          4. What was confusing or enjoyable? <span className="muted">(optional)</span>
        </label>
        <textarea
          id="survey-comment"
          className="textarea"
          value={comment}
          maxLength={1000}
          onChange={(event) => setComment(event.target.value)}
        />
      </div>

      <ChoiceGroup<'yes' | 'maybe' | 'no'>
        name="would_return"
        legend="5. Would you play another mission or share this?"
        options={[
          { value: 'yes', label: 'Yes' },
          { value: 'maybe', label: 'Maybe' },
          { value: 'no', label: 'No' },
        ]}
        value={wouldReturn}
        onChange={setWouldReturn}
      />

      {status === 'error' && error && (
        <p className="notice notice-error" role="alert">
          <span className="notice-icon" aria-hidden="true">
            ✕
          </span>
          <span className="notice-body">{error}</span>
        </p>
      )}

      <div className="button-row" style={{ marginTop: '0.5rem' }}>
        <button type="submit" className="btn btn-primary" disabled={status === 'sending'}>
          {status === 'sending' ? 'Sending…' : 'Send feedback'}
        </button>
      </div>
    </form>
  )
}
