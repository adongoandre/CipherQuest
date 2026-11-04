import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'

import { PageHeader } from '../components/Layout'
import type { SettingsResponse } from '../lib/api'
import { ApiError, api, getSessionToken, storeSessionToken } from '../lib/api'
import { useApi } from '../lib/useApi'

type TextSize = 'default' | 'large' | 'xl'
const TEXT_SIZE_KEY = 'cipherquest.text-size'
const SIZES: Array<{ value: TextSize; label: string }> = [
  { value: 'default', label: 'Default' },
  { value: 'large', label: 'Large' },
  { value: 'xl', label: 'Extra large' },
]

function readTextSize(): TextSize {
  try {
    const stored = window.localStorage.getItem(TEXT_SIZE_KEY)
    if (stored === 'large' || stored === 'xl') return stored
  } catch {
    /* storage disabled */
  }
  return 'default'
}

/**
 * Settings: accessibility preferences, privacy and account controls.
 * Server-backed toggles go to POST /settings; text size is a device
 * preference stored locally and applied to the document root.
 */
export function SettingsPage() {
  const navigate = useNavigate()
  const { data, loading, error } = useApi(() => api.settings(), [])
  const [draft, setDraft] = useState<SettingsResponse | null>(null)
  const [textSize, setTextSize] = useState<TextSize>(readTextSize)
  const [saved, setSaved] = useState<string | null>(null)
  const [problem, setProblem] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    if (data) setDraft(data)
  }, [data])

  useEffect(() => {
    const scale = textSize === 'large' ? '112.5%' : textSize === 'xl' ? '125%' : ''
    document.documentElement.style.fontSize = scale || ''
  }, [textSize])

  if (loading || !draft) {
    return (
      <>
        <PageHeader title="Settings" subtitle="Make CipherQuest comfortable for you." />
        {error && (
          <p className="notice notice-error" role="alert">
            <span className="notice-icon" aria-hidden="true">
              ✕
            </span>
            <span className="notice-body">{error}</span>
          </p>
        )}
        <p className="muted">Loading your settings…</p>
      </>
    )
  }

  function toggle(group: 'accessibility' | 'privacy' | 'play_style', key: string, value: boolean) {
    setDraft((prev) =>
      prev ? { ...prev, [group]: { ...prev[group], [key]: value } } : prev,
    )
    setSaved(null)
  }

  async function save(event: React.FormEvent) {
    event.preventDefault()
    if (!draft) return
    setBusy(true)
    setSaved(null)
    setProblem(null)
    try {
      const updated = await api.saveSettings({
        display_name: draft.display_name ?? undefined,
        accessibility: draft.accessibility,
        privacy: draft.privacy,
        play_style: draft.play_style,
      })
      setDraft(updated)
      setSaved('Changes saved.')
    } catch (e) {
      setProblem(e instanceof ApiError ? e.message : 'Changes could not be saved.')
    } finally {
      setBusy(false)
    }
  }

  async function downloadData() {
    try {
      const [profile, settings] = await Promise.all([api.profile(), api.settings()])
      const blob = new Blob([JSON.stringify({ profile, settings }, null, 2)], {
        type: 'application/json',
      })
      const url = URL.createObjectURL(blob)
      const anchor = document.createElement('a')
      anchor.href = url
      anchor.download = 'cipherquest-my-data.json'
      anchor.click()
      URL.revokeObjectURL(url)
    } catch {
      setProblem('Your data could not be prepared right now.')
    }
  }

  async function deleteAccount() {
    const confirmed = window.confirm(
      'Delete your account? This removes your progress, badges and settings. It cannot be undone.',
    )
    if (!confirmed) return
    setBusy(true)
    try {
      await api.deleteAccount()
      storeSessionToken('')
      sessionStorage.removeItem('cipherquest.session')
      navigate('/')
    } catch (e) {
      setProblem(e instanceof ApiError ? e.message : 'The account could not be deleted.')
      setBusy(false)
    }
  }

  return (
    <>
      <PageHeader title="Settings" subtitle="Make CipherQuest comfortable for you." />

      {saved && (
        <p className="notice notice-success" role="status">
          <span className="notice-icon" aria-hidden="true">
            ✓
          </span>
          <span className="notice-body">{saved}</span>
        </p>
      )}
      {problem && (
        <p className="notice notice-error" role="alert">
          <span className="notice-icon" aria-hidden="true">
            ✕
          </span>
          <span className="notice-body">{problem}</span>
        </p>
      )}

      <form onSubmit={save}>
        <section className="card" aria-labelledby="a11y-title">
          <h2 id="a11y-title">Accessibility</h2>

          <fieldset className="radio-group" style={{ marginBottom: '1rem' }}>
            <legend>Text size</legend>
            {SIZES.map((size) => (
              <label key={size.value} className="radio-row">
                <input
                  type="radio"
                  name="text-size"
                  checked={textSize === size.value}
                  onChange={() => {
                    setTextSize(size.value)
                    try {
                      window.localStorage.setItem(TEXT_SIZE_KEY, size.value)
                    } catch {
                      /* storage disabled */
                    }
                  }}
                />
                <span>{size.label}</span>
              </label>
            ))}
          </fieldset>

          <fieldset className="checkbox-group">
            <legend>Accessibility toggles</legend>
            {Object.entries(draft.accessibility).map(([key, value]) => (
              <label key={key} className="checkbox-row">
                <input
                  type="checkbox"
                  checked={value}
                  onChange={(e) => toggle('accessibility', key, e.target.checked)}
                />
                <span>{key.replace(/_/g, ' ')}</span>
              </label>
            ))}
          </fieldset>
        </section>
        <br />
        <section className="card" aria-labelledby="privacy-title">
          <h2 id="privacy-title">Privacy and account</h2>
          <fieldset className="checkbox-group" style={{ marginBottom: '1rem' }}>
            <legend>Privacy settings</legend>
            <label className="checkbox-row">
              <input
                type="checkbox"
                checked={draft.privacy.show_display_name ?? false}
                onChange={(e) => toggle('privacy', 'show_display_name', e.target.checked)}
              />
              <span>Show my display name on leaderboards</span>
            </label>
            <label className="checkbox-row">
              <input
                type="checkbox"
                checked={draft.privacy.anonymous_leaderboards ?? false}
                onChange={(e) => toggle('privacy', 'anonymous_leaderboards', e.target.checked)}
              />
              <span>Hide my name, show me as anonymous</span>
            </label>
            <label className="checkbox-row">
              <input
                type="checkbox"
                checked={draft.privacy.share_anonymous_data ?? false}
                onChange={(e) => toggle('privacy', 'share_anonymous_data', e.target.checked)}
              />
              <span>Share anonymous play data to improve the game</span>
            </label>
          </fieldset>
          <fieldset className="checkbox-group" style={{ marginBottom: '1rem' }}>
            <legend>Account settings</legend>
            <label className="checkbox-row">
              <input
                type="checkbox"
                checked={draft.play_style.remember_play_style ?? false}
                onChange={(e) => toggle('play_style', 'remember_play_style', e.target.checked)}
              />
              <span>Remember my play style (duel or team)</span>
            </label>
            <div className="field">
              <label htmlFor="settings-name">Display name</label>
              <input
                id="settings-name"
                value={draft.display_name ?? ''}
                onChange={(e) => {
                  setDraft({ ...draft, display_name: e.target.value })
                  setSaved(null)
                }}
                minLength={3}
                maxLength={24}
                disabled={draft.is_guest}
              />
              {draft.is_guest && <p className="field-help">Guests do not have an account yet.</p>}
              {!draft.is_guest && draft.email && (
                <p className="field-help">Signed in as {draft.email}</p>
              )}
            </div>
            <div className="button-row">
              <button type="button" className="btn btn-secondary" onClick={downloadData}>
                Download my data
              </button>
              <button
                type="button"
                className="btn btn-danger"
                onClick={deleteAccount}
                disabled={busy}
              >
                Delete my account
              </button>
            </div>
          </fieldset>
          <div className="button-row" >
            <button type="submit" className="btn btn-primary" disabled={busy}>
              {busy ? 'Working…' : 'Save changes'}
            </button>
          </div>
        </section>
      </form>

      <p className="muted">
        Your preferences are stored on the server with your progress. Typed answers are never
        recorded in analytics.
      </p>
      {getSessionToken() === null && <p className="muted">No session on this device yet.</p>}
    </>
  )
}