import { Link } from 'react-router-dom'

import { PageHeader } from '../components/Layout'
import type { Badge, CipherMastery, ProfileResponse } from '../lib/api'
import { api } from '../lib/api'
import { useApi } from '../lib/useApi'

const MONTHS = [
  'January',
  'February',
  'March',
  'April',
  'May',
  'June',
  'July',
  'August',
  'September',
  'October',
  'November',
  'December',
]

function joinedLabel(iso: string): string {
  const date = new Date(iso)
  return `${MONTHS[date.getMonth()]} ${date.getFullYear()}`
}

/**
 * Profile: identity, badges, cipher mastery, recent missions and the
 * public-visibility preference.
 */
export function ProfilePage() {
  const { data, loading, error, reload } = useApi(async () => {
    const [profile, settings] = await Promise.all([api.profile(), api.settings()])
    return { profile, settings }
  }, [])

  if (loading) return <p className="muted">Loading your profile…</p>
  if (error || !data) {
    return (
      <>
        <PageHeader title="Profile" />
        <p className="notice notice-error" role="alert">
          <span className="notice-icon" aria-hidden="true">
            ✕
          </span>
          <span className="notice-body">{error ?? 'Your profile could not be loaded.'}</span>
        </p>
      </>
    )
  }

  const { profile, settings } = data

  return (
    <>
      <PageHeader
        title={profile.display_name}
        subtitle={`Level ${profile.level} · Joined ${joinedLabel(profile.joined_at)}`}
      />

      <div className="card-grid two">
        <section className="card" aria-labelledby="badges-title">
          <h2 id="badges-title">Badges</h2>
          {profile.badges.length === 0 ? (
            <p className="muted">Solve a mission to earn your first badge.</p>
          ) : (
            <ul className="badge-list">
              {profile.badges.map((badge: Badge) => (
                <li key={badge.key} className={`badge${badge.earned ? ' earned' : ' locked'}`}>
                  <span>{badge.name}</span>
                  <span className="badge-hint">{badge.earned ? 'Earned' : badge.description}</span>
                </li>
              ))}
            </ul>
          )}
        </section>

        <section className="card" aria-labelledby="mastery-title">
          <h2 id="mastery-title">Cipher mastery</h2>
          {profile.mastery.length === 0 ? (
            <p className="muted">No mastery data yet.</p>
          ) : (
            <ul className="stack list-plain">
              {profile.mastery.map((row: CipherMastery) => {
                const percent = row.lessons_total
                  ? Math.round((row.lessons_completed / row.lessons_total) * 100)
                  : 0
                const status =
                  percent >= 100 ? 'Mastered' : percent > 0 ? 'In progress' : 'Not started'
                return (
                  <li key={row.cipher}>
                    <div className="stat-line">
                      <span>{row.name}</span>
                      <span className={status === 'Mastered' ? 'status-on' : 'muted'}>{status}</span>
                    </div>
                    <div
                      className="progress-track"
                      role="progressbar"
                      aria-valuenow={percent}
                      aria-valuemin={0}
                      aria-valuemax={100}
                      aria-label={`${row.name} mastery`}
                    >
                      <span style={{ width: `${percent}%` }} />
                    </div>
                  </li>
                )
              })}
            </ul>
          )}
        </section>
      </div>

      <section className="card" aria-labelledby="recent-title">
        <p className="eyebrow" id="recent-title">
          Recent missions
        </p>
        {profile.recent_missions.length === 0 ? (
          <p className="muted">Nothing yet — your solved missions will appear here.</p>
        ) : (
          <table className="data-table">
            <thead>
              <tr>
                <th scope="col">Mission</th>
                <th scope="col">Score</th>
                <th scope="col">Completed</th>
              </tr>
            </thead>
            <tbody>
              {profile.recent_missions.map((mission, index) => (
                <tr key={`${mission.slug}-${index}`}>
                  <td>
                    <Link to={`/missions/${mission.slug}`}>{mission.title}</Link>
                  </td>
                  <td>{mission.best_score ?? '—'}</td>
                  <td className="muted">
                    {mission.completed_at
                      ? new Date(mission.completed_at).toLocaleDateString()
                      : '—'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>

      <section className="card" aria-labelledby="privacy-title">
        <h2 id="privacy-title">Privacy</h2>
        <label className="checkbox-row">
          <input
            type="checkbox"
            checked={settings.privacy.show_display_name ?? false}
            onChange={(event) => {
              api
                .saveSettings({
                  privacy: { ...settings.privacy, show_display_name: event.target.checked },
                })
                .then(reload)
            }}
          />
          <span>Show me on public leaderboards</span>
        </label>
        <div className="button-row">
          <Link className="btn btn-secondary btn-block" to="/settings">
            Privacy settings
          </Link>
        </div>
      </section>

      <p className="muted">
        {profile.missions_solved} missions solved · {profile.accuracy}% accuracy ·{' '}
        {profile.streak_days}-day streak
      </p>
    </>
  )
}

export type { ProfileResponse }