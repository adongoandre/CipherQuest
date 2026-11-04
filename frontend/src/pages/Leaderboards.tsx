import { useState } from 'react'

import { PageHeader } from '../components/Layout'
import type { LeaderboardScope, StandingEntry } from '../lib/api'
import { api } from '../lib/api'
import { useApi } from '../lib/useApi'

const SCOPES: Array<{ value: LeaderboardScope; label: string }> = [
  { value: 'week', label: 'This week' },
  { value: 'friends', label: 'Friends' },
  { value: 'season', label: 'Season' },
  { value: 'all_time', label: 'All time' },
]

/** Server-ranked standings with scope tabs and a "your position" card. */
export function LeaderboardsPage() {
  const [scope, setScope] = useState<LeaderboardScope>('week')
  const { data, loading, error } = useApi(() => api.leaderboards(scope), [scope])

  return (
    <>
      <PageHeader
        title="Leaderboards"
        subtitle="Display names only. Real names are never shown."
      />

      <div className="tab-row" role="tablist" aria-label="Leaderboard scope">
        {SCOPES.map((item) => (
          <button
            key={item.value}
            type="button"
            role="tab"
            aria-selected={scope === item.value}
            className={`tab${scope === item.value ? ' active' : ''}`}
            onClick={() => setScope(item.value)}
          >
            {item.label}
          </button>
        ))}
      </div>

      {loading && <p className="muted">Loading standings…</p>}
      {error && (
        <p className="notice notice-error" role="alert">
          <span className="notice-icon" aria-hidden="true">
            ✕
          </span>
          <span className="notice-body">{error}</span>
        </p>
      )}

      {data && (
        <>
          <section className="card" aria-labelledby="board-title">
            <p className="eyebrow" id="board-title">
              {SCOPES.find((s) => s.value === data.scope)?.label} ranking
            </p>
            {data.standings.length === 0 ? (
              <p className="muted">No scores in this scope yet. Play a mission to appear here.</p>
            ) : (
              <table className="data-table">
                <thead>
                  <tr>
                    <th scope="col">Rank</th>
                    <th scope="col">Player</th>
                    <th scope="col">Score</th>
                    <th scope="col">Missions</th>
                    <th scope="col">Change</th>
                  </tr>
                </thead>
                <tbody>
                  {data.standings.map((row: StandingEntry) => (
                    <tr key={`${row.rank}-${row.display_name}`} className={row.is_you ? 'row-you' : ''}>
                      <td>{row.rank}</td>
                      <td>{row.display_name}</td>
                      <td>{row.score}</td>
                      <td>{row.missions}</td>
                      <td>{formatChange(row.change)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
            <p className="muted">{data.footer}</p>
          </section>

          {data.you && (
            <section className="card your-position" aria-labelledby="you-title">
              <p className="eyebrow" id="you-title">
                Your position
              </p>
              <p className="score-total">
                #{data.you.rank}
              </p>
              <p className="muted">
                {data.you.score} points · {data.you.missions} missions
              </p>
              <p className="muted">
                {data.you.gap_to_next > 0
                  ? `${data.you.gap_to_next} points to overtake ${
                      data.you.next_rank_name ?? 'the next player'
                    }`
                  : 'You are at the top — hold it.'}
              </p>
            </section>
          )}
          <p className="muted">Scores are checked on our servers before they appear.</p>
        </>
      )}
    </>
  )
}

function formatChange(change: number | null): string {
  if (change === null || change === 0) return '— same'
  return change > 0 ? `▲ ${change}` : `▼ ${Math.abs(change)}`
}
