import { Link } from 'react-router-dom'

import { PageHeader } from '../components/Layout'
import { api } from '../lib/api'
import { useApi } from '../lib/useApi'

const DAYS = ['M', 'T', 'W', 'T', 'F', 'S', 'S']

/** "2d 4h" / "4h 12m" / "18m" — never zero, never negative. */
function countdown(seconds: number): string {
  if (seconds <= 0) return 'now'
  const days = Math.floor(seconds / 86400)
  const hours = Math.floor((seconds % 86400) / 3600)
  const minutes = Math.floor((seconds % 3600) / 60)
  if (days > 0) return `${days}d ${hours}h`
  if (hours > 0) return `${hours}h ${minutes}m`
  return `${Math.max(1, minutes)}m`
}

/**
 * Home dashboard — the daily mission, the engagement strip (streak, week dots,
 * XP), the cup countdown, continue-where-you-left-off and friend signals.
 */
export function HomePage() {
  const { data, loading, error, reload } = useApi(() => api.home(), [])

  if (loading) return <p className="muted">Loading your desk…</p>
  if (error || !data) {
    return (
      <>
        <PageHeader title="Home" />
        <p className="notice notice-error" role="alert">
          <span className="notice-icon" aria-hidden="true">
            ✕
          </span>
          <span className="notice-body">{error ?? 'Home could not be loaded.'}</span>
        </p>
        <button type="button" className="btn btn-secondary" onClick={reload}>
          Try again
        </button>
      </>
    )
  }

  const { progress, weekly_cup: cup, daily_mission: daily } = data
  const xpPercent = Math.min(100, Math.round((progress.xp / progress.level_ceiling) * 100))
  const cupSeconds = cup.status === 'open' ? cup.seconds_until_close : cup.seconds_until_open
  const cupHeadline =
    cup.status === 'open'
      ? `Open now · closes in ${countdown(cupSeconds)}`
      : cup.status === 'scheduled'
        ? `Starts in ${countdown(cupSeconds)}`
        : 'Results are in'

  return (
    <>
      <PageHeader title={data.greeting} subtitle="Your next mystery is ready." />
      {/* Daily mission card, if any. */}
      {daily && (
        <section className="card hero-card" aria-labelledby="daily-title">
          <p className="eyebrow">Daily mission</p>
          <h2 id="daily-title">{daily.title}</h2>
          <p className="muted">
            {daily.difficulty} · {daily.cipher_name} · About {daily.estimated_minutes} minutes
          </p>
          {daily.completed && (
            <p className="muted">
              Solved{daily.best_score ? ` · best score ${daily.best_score}` : ''} — replay it or
              pick another.
            </p>
          )}
          <div className="button-row">
            <Link className="btn btn-primary" to={`/missions/${daily.slug}`}>
              {daily.completed ? 'Replay mission' : 'Start mission'}
            </Link>
            <Link className="btn btn-secondary" to="/missions">
              All missions
            </Link>
          </div>
        </section>
      )}

      <br/>
      {/* Engagement: progress, streak, week dots, cup countdown, continue learning, friend invites. */}
      <div className="card-grid">
        {/* Engagement: progress, streak, week dots. */}
        <section className="card" aria-labelledby="progress-title">
          <h2 id="progress-title">Your progress</h2>
          <div className="stat-line">
            <span>Level {progress.level}</span>
            <span className="muted">
              {progress.xp} / {progress.level_ceiling} XP
            </span>
          </div>
          <div
            className="progress-track"
            role="progressbar"
            aria-valuenow={xpPercent}
            aria-valuemin={0}
            aria-valuemax={100}
            aria-label="Level progress"
          >
            <span style={{ width: `${xpPercent}%` }} />
          </div>
          <p className="muted">
            {progress.streak_days}-day streak · {progress.missions_solved} missions solved
          </p>

          {/* Engagement: this week's activity, Mon → Sun */}
          <div className="week-dots" role="list" aria-label="Activity this week">
            {data.week_dots.map((active, index) => (
              <span className="week-dot-row" role="listitem" key={`${DAYS[index]}-${index}`}>
                <span
                  className={`week-dot${active ? ' on' : ''}`}
                  aria-label={`${active ? 'Played' : 'No activity'} on day ${index + 1}`}
                />
                <span className="week-dot-label">{DAYS[index]}</span>
              </span>
            ))}
          </div>
        </section>
        {/* Engagement: weekly cup countdown. */}
        <section className="card" aria-labelledby="cup-title">
          <h2 id="cup-title">Weekly Free Cup</h2>
          <p className="muted">{cupHeadline}</p>
          <p className="muted">
            {cup.participants} players entered · {cup.label}
          </p>
          <div className="button-row">
            <Link className="btn btn-secondary" to="/compete">
              View event
            </Link>
          </div>
        </section>
        {/* Engagement: continue learning. */}
        {data.continue_learning && (
          <section className="card" aria-labelledby="continue-title">
            <h2 id="continue-title">Continue learning</h2>
            <div className="stat-line">
              <span>{data.continue_learning.cipher_name}</span>
              <span className="muted">
                Lesson {data.continue_learning.step} of {data.continue_learning.total_steps}
              </span>
            </div>
            <div
              className="progress-track"
              role="progressbar"
              aria-valuenow={data.continue_learning.step}
              aria-valuemin={0}
              aria-valuemax={data.continue_learning.total_steps}
              aria-label="Lesson progress"
            >
              <span
                style={{
                  width: `${Math.round(
                    (data.continue_learning.step / data.continue_learning.total_steps) * 100,
                  )}%`,
                }}
              />
            </div>
            <div className="button-row">
              <Link
                className="btn btn-secondary"
                to={`/learn/${data.continue_learning.cipher_slug}/${data.continue_learning.step}`}
              >
                Resume lesson
              </Link>
            </div>
          </section>
        )}
        {/* Engagement: friend invitations. */}
        <section className="card" aria-labelledby="invites-title">
          <h2 id="invites-title">Friend invitations</h2>
          {data.invitations.length === 0 ? (
            <p className="muted">No invitations waiting. Invite a friend from the Friends page.</p>
          ) : (
            <ul className="stack list-plain">
              {data.invitations.map((invite) => (
                <li key={invite.id}>
                  <p>
                    <strong>{invite.from_display_name}</strong> invited you to a{' '}
                    {invite.kind === 'cipher_duel' ? 'Cipher Duel' : 'game'}.
                  </p>
                  <div className="button-row">
                    <InvitationActions id={invite.id} onDone={reload} />
                  </div>
                </li>
              ))}
            </ul>
          )}
        </section>
      </div>

      <br/>

      {/* Engagement: what friends have been doing, straight from the server. */}
      <section className="card" aria-labelledby="activity-title">
        <h2 id="activity-title">Friend activity</h2>
        {data.friend_activity.length === 0 ? (
          <p className="muted">
            Nothing yet. Add friends and their solves will show up here.
          </p>
        ) : (
          <ul className="activity-list">
            {data.friend_activity.map((item, index) => (
              <li key={`${item.display_name}-${index}`}>
                <span className="activity-dot" aria-hidden="true" />
                <span>
                  <strong>{item.display_name}</strong> {item.action}
                </span>
                {item.when && (
                  <time className="muted" dateTime={item.when}>
                    {new Date(item.when).toLocaleDateString()}
                  </time>
                )}
              </li>
            ))}
          </ul>
        )}
      </section>

      {data.suggested_next && (
        <p className="muted">
          Suggested next: <Link to={`/learn/${data.suggested_next}`}>{data.suggested_next}</Link>
        </p>
      )}
    </>
  )
}

function InvitationActions({ id, onDone }: { id: number; onDone: () => void }) {
  return (
    <>
      <button
        type="button"
        className="btn btn-primary"
        onClick={() => api.duelInviteRespond(id, 'accept').then(onDone)}
      >
        Accept
      </button>
      <button
        type="button"
        className="btn btn-secondary"
        onClick={() => api.duelInviteRespond(id, 'decline').then(onDone)}
      >
        Decline
      </button>
    </>
  )
}
