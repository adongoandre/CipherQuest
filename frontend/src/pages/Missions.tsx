import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'

import { api, type MissionListResponse } from '../lib/api'

type LoadState =
  | { status: 'loading' }
  | { status: 'ready'; data: MissionListResponse }
  | { status: 'error'; message: string }

const DIFFICULTY_LABEL: Record<string, string> = {
  beginner: 'Beginner',
  intermediate: 'Intermediate',
  advanced: 'Advanced',
  expert: 'Expert',
}

export function MissionsPage() {
  const [state, setState] = useState<LoadState>({ status: 'loading' })

  useEffect(() => {
    document.title = 'Missions — CipherQuest'
    let cancelled = false

    api
      .missions()
      .then((data) => {
        if (!cancelled) setState({ status: 'ready', data })
      })
      .catch((error: unknown) => {
        if (cancelled) return
        setState({
          status: 'error',
          message: error instanceof Error ? error.message : 'Missions could not be loaded.',
        })
      })

    return () => {
      cancelled = true
    }
  }, [])

  function trackNext(slug: string) {
    api.track('next_mission_clicked', slug).catch(() => {
      /* analytics must never block navigation */
    })
  }

  return (
    <>
      <h1>Missions</h1>
      <p className="lead">
        Five verified missions, ordered from a gentle warm-up to a trick that hides a room inside
        another word.
      </p>

      {state.status === 'loading' && (
        <p className="skeleton" role="status">
          Loading missions…
        </p>
      )}

      {state.status === 'error' && (
        <div className="notice notice-error" role="alert">
          <span className="notice-icon" aria-hidden="true">
            ✕
          </span>
          <div className="notice-body">
            <p>{state.message}</p>
            <p className="muted">Check that the API is running on port 8000, then reload.</p>
          </div>
        </div>
      )}

      {state.status === 'ready' && (
        <>
          <div className="lead">
            
            <div className="notice-body">
              <p style={{ margin: 0 }}>
                <strong>Today&apos;s mission:</strong>{' '}
                <Link
                  to={`/missions/${state.data.daily_slug}`}
                  onClick={() => trackNext(state.data.daily_slug)}
                >
                  start the daily pick
                </Link>
                . It rotates through all five each day.
              </p>
            </div>
          </div>

          <ul className="mission-grid">
            {state.data.missions.map((mission) => (
              <li className="mission-card" key={mission.slug}>
                <h3>
                  {mission.display_order}. {mission.title}
                </h3>
                <p className="muted" style={{ marginBottom: 10 }}>
                  Caesar cipher · {mission.cipher_type === 'caesar' ? 'shift parameter' : 'parameter'}
                </p>
                <div style={{ marginTop: 'auto' }}>
                  {/* difficulty, time estimate, completion status */}
                  <div className="badge-row">
                    <span className={`badge tag-difficulty-${mission.difficulty}`}>
                      {DIFFICULTY_LABEL[mission.difficulty] ?? mission.difficulty}
                    </span>
                    <span className="badge">{mission.estimated_minutes} min</span>
                    {mission.is_completed && <span className="badge badge-key">Completed</span>}
                  </div>
                  <Link
                    className="btn btn-primary"
                    to={`/missions/${mission.slug}`}
                    onClick={() => trackNext(mission.slug)}
                    style={{ display: 'inline-block', marginTop: '0.6rem' }}
                  >
                    {mission.is_completed ? 'Play again' : 'Start mission'}
                  </Link>
                </div>
              </li>
            ))}
          </ul>
        </>
      )}
    </>
  )
}
