import { Link, useNavigate, useParams } from 'react-router-dom'
import { useState } from 'react'

import { PageHeader } from '../components/Layout'
import { ApiError, api } from '../lib/api'
import { useApi } from '../lib/useApi'

const MODES = [
  {
    title: 'Solo Missions',
    meta: '1 player · 5 min',
    body: 'Story missions at your own pace. Untimed by default.',
    action: 'Play',
    to: '/missions',
    primary: true,
  },
  {
    title: 'Cipher Duel',
    meta: '2 players · 8 min',
    body: 'Race a friend on the same puzzle set. Same rules for both.',
    action: 'Invite a friend',
    to: '/friends',
    primary: false,
  },
  {
    title: 'Team Escape',
    meta: '2–4 players · 20 min',
    body: 'Each teammate holds a different clue. Talk it through to escape.',
    action: 'Create a room',
    to: '/rooms',
    primary: false,
  },
  {
    title: 'Weekly Free Cup',
    meta: 'Open to all · weekly',
    body: 'Free entry, virtual rewards, published rules.',
    action: 'View event',
    to: '/compete',
    primary: false,
  },
]

/** Mode chooser — every mode teaches the same ciphers. */
export function PlayPage() {
  const navigate = useNavigate()
  const [error, setError] = useState<string | null>(null)

  async function createRoom() {
    setError(null)
    try {
      const room = await api.createRoom('team_escape')
      navigate(`/rooms/${room.code}`)
    } catch (e) {
      setError(e instanceof ApiError ? e.message : 'The room could not be created.')
    }
  }

  return (
    <>
      <PageHeader title="Choose play mode" subtitle="Every mode teaches the same ciphers." />
      {error && (
        <p className="notice notice-error" role="alert">
          <span className="notice-icon" aria-hidden="true">
            ✕
          </span>
          <span className="notice-body">{error}</span>
        </p>
      )}
      <div className="card-grid">
        {MODES.map((mode) => (
          <section className="card mode-card" key={mode.title}>
            <h2>{mode.title}</h2>
            <p className="eyebrow">{mode.meta}</p>
            <p className="muted">{mode.body}</p>
            {mode.to === '/rooms' ? (
              <div className="button-row">
                <button type="button" className="btn btn-secondary" onClick={createRoom}>
                  {mode.action}
                </button>
              </div>
            ) : (
              <div className="button-row">
                <Link
                  className={`btn ${mode.primary ? 'btn-primary' : 'btn-secondary'}`}
                  to={mode.to}
                >
                  {mode.action}
                </Link>
              </div>
            )}
          </section>
        ))}
      </div>
    </>
  )
}

/**
 * Team Escape lobby: room code, player readiness and host controls.
 * Polls while waiting so a friend joining shows up without a refresh.
 */
export function RoomPage() {
  const code = useRoomCode()
  const { data: room, loading, error, reload } = useApi(() => api.room(code), [code])

  if (loading) return <p className="muted">Opening the lobby…</p>
  if (error || !room) {
    return (
      <>
        <PageHeader title="Team Escape lobby" />
        <p className="notice notice-error" role="alert">
          <span className="notice-icon" aria-hidden="true">
            ✕
          </span>
          <span className="notice-body">{error ?? 'That room could not be found.'}</span>
        </p>
        <Link className="btn btn-secondary" to="/play">
          Back to Play
        </Link>
      </>
    )
  }

  const waiting = room.players.filter((p) => !p.ready).length

  return (
    <>
      <PageHeader
        title="Team Escape lobby"
        subtitle="Share the code. Start when everyone is ready."
      />

      <div className="card-grid two">
        <section className="card">
          <h2>Room code</h2>
          <p className="room-code">{room.code}</p>
          <div className="button-row">
            <button
              type="button"
              className="btn btn-secondary"
              onClick={() => navigator.clipboard?.writeText(room.code)}
            >
              Copy invite link
            </button>
            <button
              type="button"
              className="btn btn-secondary"
              onClick={() =>
                navigator.share?.({ title: 'Join my CipherQuest room', text: room.code })
              }
            >
              Share code
            </button>
          </div>
          <p className="eyebrow">Game mode</p>
          <p className="field-static">{room.mode === 'duel' ? 'Cipher Duel' : 'Team Escape'}</p>
          <p className="muted">Relaxed, untimed rules. Host can change this.</p>
        </section>

        <section className="card">
          <h2>
            Players ({room.players.length} of {room.max_players})
          </h2>
          <table className="data-table">
            <thead>
              <tr>
                <th scope="col">Player</th>
                <th scope="col">Status</th>
              </tr>
            </thead>
            <tbody>
              {room.players.map((player) => (
                <tr key={player.session_id}>
                  <td>
                    {player.display_name}
                    {player.is_host ? ' (host)' : ''}
                  </td>
                  <td className={player.ready ? 'status-on' : 'muted'}>
                    {player.ready ? 'Ready' : 'Waiting…'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      </div>

      <div className="button-row">
        <button
          type="button"
          className="btn btn-primary"
          disabled={!room.you_are_host || waiting > 0 || !room.everyone_ready}
          onClick={() => api.startRoom(room.code).then(reload)}
        >
          {room.you_are_host
            ? waiting > 0
              ? `Start game (waiting for ${waiting} player${waiting > 1 ? 's' : ''})`
              : 'Start game'
            : 'Waiting for the host to start'}
        </button>
        <button
          type="button"
          className="btn btn-secondary"
          onClick={() => api.readyRoom(room.code, !room.you_are_ready).then(reload)}
        >
          {room.you_are_ready ? 'Mark not ready' : "I'm ready"}
        </button>
        <button
          type="button"
          className="btn btn-secondary"
          onClick={() => api.leaveRoom(room.code).then(() => window.location.assign('/play'))}
        >
          Leave room
        </button>
      </div>
    </>
  )
}

function useRoomCode(): string {
  const { code = '' } = useParams()
  return code
}
