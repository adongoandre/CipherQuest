import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'

import { api, type ProgressResponse } from '../lib/api'

type LoadState =
  | { status: 'loading' }
  | { status: 'ready'; data: ProgressResponse }
  | { status: 'error'; message: string }

const DIFFICULTY_LABEL: Record<string, string> = {
  beginner: 'Beginner',
  intermediate: 'Intermediate',
  advanced: 'Advanced',
  expert: 'Expert',
}

export function ProgressPage() {
  const [state, setState] = useState<LoadState>({ status: 'loading' })

  useEffect(() => {
    document.title = 'Progress — CipherQuest'
    let cancelled = false

    api
      .progress()
      .then((data) => {
        if (!cancelled) setState({ status: 'ready', data })
      })
      .catch((error: unknown) => {
        if (cancelled) return
        setState({
          status: 'error',
          message: error instanceof Error ? error.message : 'Progress could not be loaded.',
        })
      })

    return () => {
      cancelled = true
    }
  }, [])

  return (
    <>
      <p className="eyebrow">Your case notes</p>
      <h1>Progress</h1>
      <p className="lead">
        Saved against this browser tab only. Nothing here is tied to your name or email.
      </p>

      {state.status === 'loading' && (
        <p className="skeleton" role="status">
          Loading your progress…
        </p>
      )}

      {state.status === 'error' && (
        <div className="notice notice-error" role="alert">
          <span className="notice-icon" aria-hidden="true">
            ✕
          </span>
          <div className="notice-body">
            <p>{state.message}</p>
            <p className="muted">Check that the API is running, then reload.</p>
          </div>
        </div>
      )}

      {state.status === 'ready' && (
        <>
          <dl className="score-grid">
            <div>
              <dt>Missions completed</dt>
              <dd>{state.data.progress.missions_completed}</dd>
            </div>
            <div>
              <dt>Puzzles solved</dt>
              <dd>{state.data.progress.total_puzzles_solved}</dd>
            </div>
            <div className="score-total">
              <dt>Total score</dt>
              <dd>{state.data.progress.total_score}</dd>
            </div>
          </dl>

          {state.data.progress.missions_completed === 0 ? (
            <div className="notice">
              <span className="notice-icon" aria-hidden="true">
                ◎
              </span>
              <div className="notice-body">
                <p style={{ margin: 0 }}>
                  No missions finished yet.{' '}
                  <Link to="/missions">Start with the first case file</Link> — it takes about five
                  minutes.
                </p>
              </div>
            </div>
          ) : (
            <ul className="mission-grid">
              {state.data.missions.map((mission) => (
                <li className="mission-card" key={mission.slug}>
                  <div className="badge-row">
                    <span className={`badge tag-difficulty-${mission.difficulty}`}>
                      {DIFFICULTY_LABEL[mission.difficulty] ?? mission.difficulty}
                    </span>
                    {mission.completed && <span className="badge badge-key">Completed</span>}
                    {mission.comprehension_awarded && (
                      <span className="badge">Check passed</span>
                    )}
                  </div>
                  <h3>{mission.title}</h3>
                  <p className="muted" style={{ margin: 0 }}>
                    Best score {mission.best_score}/100 · played {mission.completion_count}{' '}
                    {mission.completion_count === 1 ? 'time' : 'times'}
                  </p>
                  <Link className="btn btn-secondary" to={`/missions/${mission.slug}`}>
                    {mission.completed ? 'Play again' : 'Start mission'}
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </>
      )}
    </>
  )
}
