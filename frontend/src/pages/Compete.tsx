import { Link } from 'react-router-dom'
import { useState } from 'react'

import { PageHeader } from '../components/Layout'
import { api } from '../lib/api'
import { useApi } from '../lib/useApi'

/** Weekly Free Cup: rules, schedule with a live countdown, current standings. */
export function CompetePage() {
  const { data: cup, loading, error, reload } = useApi(() => api.cup(), [])
  const [entering, setEntering] = useState(false)
  const [message, setMessage] = useState<string | null>(null)

  if (loading) return <p className="muted">Loading the cup…</p>
  if (error || !cup) {
    return (
      <>
        <PageHeader title="Weekly Free Cup" />
        <p className="notice notice-error" role="alert">
          <span className="notice-icon" aria-hidden="true">
            ✕
          </span>
          <span className="notice-body">{error ?? 'The cup could not be loaded.'}</span>
        </p>
      </>
    )
  }

  async function enter() {
    setEntering(true)
    try {
      const result = await api.enterCup()
      setMessage(result.message)
      reload()
    } finally {
      setEntering(false)
    }
  }

  const seasonWeek = Number(cup.week.split('-W')[1] ?? 1)

  return (
    <>
      <PageHeader
        title="Weekly Free Cup"
        subtitle={`Free entry · Virtual rewards only · Week ${seasonWeek} of the season`}
      />

      <div className="card-grid two">
        <section className="card">
          <h2>Rules</h2>
          <ul className="list-bullets">
            <li>One attempt per puzzle</li>
            <li>3 hints allowed; each reduces the bonus</li>
            <li>Server-timed rounds</li>
            <li>Ties broken by fewer hints, then time</li>
          </ul>
        </section>

        <section className="card">
          <h2>Schedule</h2>
          <p className="muted">{cup.label}</p>
          <p className="muted">
            {cup.status === 'open'
              ? `Closes in ${formatSeconds(cup.seconds_until_close)}`
              : cup.status === 'scheduled'
                ? `Opens in ${formatSeconds(cup.seconds_until_open)}`
                : 'Results announced Monday'}
          </p>
          <p className="muted">{cup.note}</p>
          <div className="button-row">
            {cup.you_entered ? (
              <span className="badge">You are entered</span>
            ) : (
              <button type="button" className="btn btn-primary" onClick={enter} disabled={entering}>
                {entering ? 'Entering…' : 'Enter for free'}
              </button>
            )}
          </div>
          {message && <p className="muted">{message}</p>}
        </section>
      </div>
      <br />
      <section className="card" aria-labelledby="standings-title">
        <p className="eyebrow" id="standings-title">
          Current standings
        </p>
        <StandingsTable cup={cup} />
        <p className="muted">
          <Link to="/compete/leaderboards">Full leaderboards</Link> · Scores are checked on our
          servers before they appear.
        </p>
      </section>
    </>
  )
}

function formatSeconds(seconds: number): string {
  if (seconds <= 0) return 'any moment now'
  const days = Math.floor(seconds / 86400)
  const hours = Math.floor((seconds % 86400) / 3600)
  const minutes = Math.floor((seconds % 3600) / 60)
  if (days > 0) return `${days}d ${hours}h`
  if (hours > 0) return `${hours}h ${minutes}m`
  return `${Math.max(1, minutes)}m`
}

export function StandingsTable({
  cup,
}: {
  cup: { standings: import('../lib/api').StandingEntry[] }
}) {
  return (
    <table className="data-table">
      <thead>
        <tr>
          <th scope="col">Rank</th>
          <th scope="col">Player</th>
          <th scope="col">Points</th>
          <th scope="col">Status</th>
        </tr>
      </thead>
      <tbody>
        {cup.standings.map((row) => (
          <tr key={`${row.rank}-${row.display_name}`} className={row.is_you ? 'row-you' : ''}>
            <td>{row.rank}</td>
            <td>{row.display_name}</td>
            <td>{row.score}</td>
            <td>{row.rank <= 2 ? 'Qualified' : 'In contention'}</td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}
