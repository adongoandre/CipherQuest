import { Link, useNavigate } from 'react-router-dom'
import { useState } from 'react'

import { ApiError, api, storeSessionToken } from '../lib/api'

type Mode = 'create' | 'signin'

/** Join screen: create an account or sign in, with a guest shortcut. */
export function JoinPage() {
  const navigate = useNavigate()
  const [mode, setMode] = useState<Mode>('create')
  const [displayName, setDisplayName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [accepted, setAccepted] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  async function submit(event: React.FormEvent) {
    event.preventDefault()
    setError(null)
    setBusy(true)
    try {
      const result =
        mode === 'create'
          ? await api.register({
              display_name: displayName,
              email,
              password,
              accepted_terms: accepted,
            })
          : await api.login({ email, password })
      storeSessionToken(result.token)
      navigate('/home')
    } catch (e) {
      setError(e instanceof ApiError ? e.message : 'That did not work. Please try again.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="auth-wrap">
      <section className="card auth-card" aria-labelledby="join-title">
        <h1 id="join-title">Join CipherQuest</h1>

        <div className="tab-row" role="tablist" aria-label="Account">
          <button
            type="button"
            role="tab"
            aria-selected={mode === 'create'}
            className={`tab${mode === 'create' ? ' active' : ''}`}
            onClick={() => {
              setMode('create')
              setError(null)
            }}
          >
            Create account
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={mode === 'signin'}
            className={`tab${mode === 'signin' ? ' active' : ''}`}
            onClick={() => {
              setMode('signin')
              setError(null)
            }}
          >
            Sign in
          </button>
        </div>

        {error && (
          <p className="notice notice-error" role="alert">
            <span className="notice-icon" aria-hidden="true">
              ✕
            </span>
            <span className="notice-body">{error}</span>
          </p>
        )}

        <form onSubmit={submit} className="stack">
          {mode === 'create' && (
            <div className="field">
              <label htmlFor="display-name">Display name</label>
              <input
                id="display-name"
                name="display_name"
                value={displayName}
                onChange={(e) => setDisplayName(e.target.value)}
                autoComplete="nickname"
                required
                minLength={3}
                maxLength={24}
              />
              <p className="field-help">Use a nickname, not your real name.</p>
            </div>
          )}

          <div className="field">
            <label htmlFor="email">Email</label>
            <input
              id="email"
              name="email"
              type="email"
              placeholder="you@example.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              autoComplete="email"
              required
            />
          </div>

          <div className="field">
            <label htmlFor="password">Password</label>
            <input
              id="password"
              name="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete={mode === 'create' ? 'new-password' : 'current-password'}
              required
              minLength={8}
            />
          </div>

          {mode === 'create' && (
            <label className="checkbox-row">
              <input
                type="checkbox"
                checked={accepted}
                onChange={(e) => setAccepted(e.target.checked)}
                required
              />
              <span>
                I agree to the <Link to="/help">Terms and Privacy notice</Link>
              </span>
            </label>
          )}

          <button type="submit" className="btn btn-primary btn-block" disabled={busy}>
            {busy ? 'Working…' : mode === 'create' ? 'Create account' : 'Sign in'}
          </button>
        </form>

        <p className="center">
          <Link to="/help" className="text-link">
            Forgot your password?
          </Link>
        </p>

        <hr className="divider" />

        <div className="stack">
          <button
            type="button"
            className="btn btn-secondary btn-block"
            onClick={() => navigate('/home')}
          >
            Continue as guest
          </button>
          <p className="field-help center">
            Guests can play, but progress stays on this device.
          </p>
        </div>
      </section>
    </div>
  )
}