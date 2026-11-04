import { useState } from 'react'

import { PageHeader } from '../components/Layout'
import { ApiError, api } from '../lib/api'
import { useApi } from '../lib/useApi'

/** Friends hub: requests, duel invitations, the friends list and blocks. */
export function FriendsPage() {
  const { data, loading, error, reload } = useApi(() => api.friends(), [])
  const [name, setName] = useState('')
  const [note, setNote] = useState<{ kind: 'ok' | 'bad'; text: string } | null>(null)
  const [busy, setBusy] = useState(false)

  if (loading) return <p className="muted">Loading your friends…</p>
  if (error || !data) {
    return (
      <>
        <PageHeader title="Friends" />
        <p className="notice notice-error" role="alert">
          <span className="notice-icon" aria-hidden="true">
            ✕
          </span>
          <span className="notice-body">{error ?? 'Friends could not be loaded.'}</span>
        </p>
      </>
    )
  }

  async function addFriend(event: React.FormEvent) {
    event.preventDefault()
    const displayName = name.trim()
    if (!displayName) return
    setBusy(true)
    setNote(null)
    try {
      const result = await api.friendRequest(displayName)
      setNote({ kind: 'ok', text: result.message })
      setName('')
      reload()
    } catch (e) {
      setNote({
        kind: 'bad',
        text: e instanceof ApiError ? e.message : 'That request could not be sent.',
      })
    } finally {
      setBusy(false)
    }
  }

  async function run(action: () => Promise<{ message: string }>) {
    try {
      const result = await action()
      setNote({ kind: 'ok', text: result.message })
      reload()
    } catch (e) {
      setNote({
        kind: 'bad',
        text: e instanceof ApiError ? e.message : 'That did not work.',
      })
    }
  }

  return (
    <>
      <PageHeader title="Friends" subtitle="Play together, compare progress, keep it kind." />

      {note && (
        <p className={`notice ${note.kind === 'ok' ? 'notice-success' : 'notice-error'}`} role="status">
          <span className="notice-icon" aria-hidden="true">
            {note.kind === 'ok' ? '✓' : '✕'}
          </span>
          <span className="notice-body">{note.text}</span>
        </p>
      )}

      <section className="card" aria-labelledby="add-title">
        <h2 id="add-title">Add a friend</h2>
        <form className="inline-form" onSubmit={addFriend}>
          <div className="field">
            <label htmlFor="friend-name">Display name</label>
            <input
              id="friend-name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. Maya"
              maxLength={60}
            />
          </div>
          <button type="submit" className="btn btn-primary" disabled={busy}>
            {busy ? 'Sending…' : 'Send request'}
          </button>
        </form>
      </section>

      <div className="card-grid two">
        <section className="card" aria-labelledby="requests-title">
          <h2 id="requests-title">Friend requests</h2>
          {data.requests_incoming.length === 0 ? (
            <p className="muted">No incoming requests right now.</p>
          ) : (
            <ul className="stack list-plain">
              {data.requests_incoming.map((request) => (
                <li key={request.id}>
                  <div className="stat-line">
                    <span>
                      <strong>{request.display_name}</strong>
                    </span>
                    <span className="muted">Level {request.level}</span>
                  </div>
                  <div className="button-row">
                    <button
                      type="button"
                      className="btn btn-primary"
                      onClick={() => run(() => api.friendRespond(request.id, 'accept'))}
                    >
                      Accept
                    </button>
                    <button
                      type="button"
                      className="btn btn-secondary"
                      onClick={() => run(() => api.friendRespond(request.id, 'decline'))}
                    >
                      Decline
                    </button>
                  </div>
                </li>
              ))}
            </ul>
          )}
          {data.requests_outgoing.length > 0 && (
            <>
              <p className="eyebrow">Sent</p>
              <ul className="stack list-plain">
                {data.requests_outgoing.map((request) => (
                  <li key={request.id} className="muted">
                    {request.display_name} — awaiting reply
                  </li>
                ))}
              </ul>
            </>
          )}
        </section>

        <section className="card" aria-labelledby="invites-title">
          <h2 id="invites-title">Cipher Duel invitations</h2>
          {data.invitations.length === 0 ? (
            <p className="muted">No duel invitations waiting.</p>
          ) : (
            <ul className="stack list-plain">
              {data.invitations.map((invite) => (
                <li key={invite.id}>
                  <p>
                    <strong>{invite.from_display_name}</strong> challenged you to a Cipher Duel.
                  </p>
                  <div className="button-row">
                    <button
                      type="button"
                      className="btn btn-primary"
                      onClick={() => run(() => api.duelInviteRespond(invite.id, 'accept'))}
                    >
                      Accept
                    </button>
                    <button
                      type="button"
                      className="btn btn-secondary"
                      onClick={() => run(() => api.duelInviteRespond(invite.id, 'decline'))}
                    >
                      Decline
                    </button>
                  </div>
                </li>
              ))}
            </ul>
          )}
          {data.pending_outgoing.length > 0 && (
            <>
              <p className="eyebrow">Sent</p>
              <ul className="stack list-plain">
                {data.pending_outgoing.map((invite) => (
                  <li key={invite.id} className="muted">
                    Waiting on {invite.from_display_name}
                  </li>
                ))}
              </ul>
            </>
          )}
        </section>
      </div>

      <section className="card" aria-labelledby="list-title">
        <p className="eyebrow" id="list-title">
          Your friends ({data.friends.length})
        </p>
        {data.friends.length === 0 ? (
          <p className="muted">No friends yet. Send a request above to get started.</p>
        ) : (
          <table className="data-table">
            <thead>
              <tr>
                <th scope="col">Player</th>
                <th scope="col">Level</th>
                <th scope="col">Status</th>
                <th scope="col">
                  <span className="sr-only">Actions</span>
                </th>
              </tr>
            </thead>
            <tbody>
              {data.friends.map((friend) => (
                <tr key={friend.id}>
                  <td>{friend.display_name}</td>
                  <td>{friend.level}</td>
                  <td className={friend.status === 'recently_active' ? 'status-on' : 'muted'}>
                    {friend.status === 'recently_active' ? 'Recently active' : 'Offline'}
                  </td>
                  <td>
                    <div className="button-row">
                      <button
                        type="button"
                        className="btn btn-secondary"
                        onClick={() => run(() => api.duelInvite(friend.display_name))}
                      >
                        Duel
                      </button>
                      <button
                        type="button"
                        className="btn btn-secondary"
                        onClick={() => run(() => api.block(friend.display_name))}
                      >
                        Block
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>

      {data.blocked.length > 0 && (
        <section className="card" aria-labelledby="blocked-title">
          <p className="eyebrow" id="blocked-title">
            Blocked
          </p>
          <ul className="stack list-plain">
            {data.blocked.map((entry) => (
              <li key={entry.id} className="muted">
                {entry.display_name}
              </li>
            ))}
          </ul>
        </section>
      )}
    </>
  )
}