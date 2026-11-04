import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'

import { PageHeader } from '../components/Layout'
import type { AdminMissionDetail, AdminMissionSummary, AuditEntry, MissionDraftRequest } from '../lib/api'
import { ApiError, api } from '../lib/api'
import { useApi } from '../lib/useApi'

/** Caesar shift used by the key rule "answer letter count is the shift". */
function shiftFromAnswer(answer: string): number {
  const letters = answer.replace(/[^a-z]/gi, '')
  return letters.length === 0 ? 0 : letters.length % 26
}

function caesar(text: string, shift: number): string {
  return text.replace(/[a-z]/gi, (ch) => {
    const base = ch <= 'Z' ? 65 : 97
    return String.fromCharCode(((ch.charCodeAt(0) - base + shift) % 26) + base)
  })
}

function splitList(value: string): string[] {
  return value
    .split(',')
    .map((item) => item.trim())
    .filter(Boolean)
}

const EMPTY: MissionDraftRequest = {
  title: '',
  narrative: '',
  riddle_prompt: '',
  accepted_riddle_answers: [],
  key_rule_description: '',
  contextual_clue: '',
  plaintext_answer: '',
  hints: [],
  difficulty: 'gentle',
  cipher_type: 'caesar',
  estimated_minutes: 5,
}

function toDraft(detail: AdminMissionDetail): MissionDraftRequest {
  return {
    title: detail.title,
    narrative: detail.narrative,
    riddle_prompt: detail.riddle_prompt,
    accepted_riddle_answers: detail.accepted_riddle_answers,
    key_rule_description: detail.key_rule_description,
    contextual_clue: detail.contextual_clue,
    plaintext_answer: detail.plaintext_answer,
    hints: detail.hints,
    difficulty: detail.difficulty,
    cipher_type: detail.cipher_type,
    estimated_minutes: detail.estimated_minutes,
  }
}

/**
 * Admin mission editor: pick a mission (or start a new one), edit every field
 * the API accepts, watch the ciphertext preview, then verify / save / publish.
 * Every action writes to the real admin endpoints and the audit log below.
 */
export function AdminPage() {
  const list = useApi(() => api.adminMissions(), [])
  const [selectedId, setSelectedId] = useState<number | null>(null)
  const [detail, setDetail] = useState<AdminMissionDetail | null>(null)
  const [draft, setDraft] = useState<MissionDraftRequest>(EMPTY)
  const [answers, setAnswers] = useState('')
  const [hints, setHints] = useState<string[]>(['', '', ''])
  const [busy, setBusy] = useState(false)
  const [saved, setSaved] = useState<string | null>(null)
  const [problem, setProblem] = useState<string | null>(null)
  const audit = useApi(() => api.adminAudit(), [])

  // Load the selected mission's full detail into the form.
  useEffect(() => {
    if (selectedId === null) {
      setDetail(null)
      setDraft(EMPTY)
      setAnswers('')
      setHints(['', '', ''])
      return
    }
    let active = true
    api
      .adminMission(selectedId)
      .then((data) => {
        if (!active) return
        setDetail(data)
        setDraft(toDraft(data))
        setAnswers(data.accepted_riddle_answers.join(', '))
        const next = ['', '', '']
        data.hints.forEach((hint, index) => {
          if (index < next.length) next[index] = hint
        })
        setHints(next)
        setSaved(null)
        setProblem(null)
      })
      .catch((error: unknown) => {
        if (active) setProblem(error instanceof ApiError ? error.message : 'Mission could not be loaded.')
      })
    return () => {
      active = false
    }
  }, [selectedId])

  const shift = shiftFromAnswer(splitList(answers)[0] ?? '')
  const ciphertext = draft.plaintext_answer ? caesar(draft.plaintext_answer, shift) : ''
  const verified = detail?.verification.verified ?? false
  const verifyProblems = detail?.verification.problems ?? []

  function update<K extends keyof MissionDraftRequest>(key: K, value: MissionDraftRequest[K]) {
    setDraft((prev) => ({ ...prev, [key]: value }))
    setSaved(null)
  }

  async function run(action: () => Promise<unknown>, success: string) {
    setBusy(true)
    setSaved(null)
    setProblem(null)
    try {
      await action()
      setSaved(success)
    } catch (error) {
      setProblem(error instanceof ApiError ? error.message : 'That action failed.')
    } finally {
      setBusy(false)
    }
  }

  async function saveDraft() {
    const payload: MissionDraftRequest = {
      ...draft,
      accepted_riddle_answers: splitList(answers),
      hints: hints.filter((hint) => hint.trim() !== ''),
    }
    if (selectedId === null) {
      const created = await api.createMission(payload)
      setSelectedId(created.id)
      setDetail(created)
      setSaved('Mission created as a draft.')
      return
    }
    const updated = await api.updateMission(selectedId, payload)
    setDetail(updated)
    setSaved('Draft saved.')
  }

  async function verify() {
    if (selectedId === null) return
    const result = await api.verifyMission(selectedId)
    if (result.verified) {
      setSaved('Verified: round-trip test passed.')
    } else {
      setProblem(`Verification failed: ${result.problems.join(' · ')}`)
    }
    setDetail(await api.adminMission(selectedId))
  }

  return (
    <>
      <p className="eyebrow">ADMIN · CHANGES ARE LOGGED</p>
      <PageHeader title="Mission editor" subtitle="Write, verify and publish cipher missions." />

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

      {list.error && (
        <p className="notice notice-error" role="alert">
          <span className="notice-icon" aria-hidden="true">
            ✕
          </span>
          <span className="notice-body">{list.error}</span>
        </p>
      )}

      <div className="admin-layout">
        <aside className="mission-list" aria-label="Missions">
          <button type="button" className="btn btn-block" onClick={() => setSelectedId(null)}>
            + New mission
          </button>
          {(list.data ?? []).map((mission: AdminMissionSummary) => (
            <button
              key={mission.id}
              type="button"
              className={`mission-list-item${selectedId === mission.id ? ' active' : ''}`}
              onClick={() => setSelectedId(mission.id)}
            >
              <span className="mission-list-title">{mission.title}</span>
              <span className={`status-pill status-${mission.status}`}>{mission.status}</span>
            </button>
          ))}
          {list.loading && <p className="muted">Loading missions…</p>}
        </aside>

        <section className="editor-card card">
          {selectedId === null ? (
            <>
              <header className="editor-head">
                <h2>New mission</h2>
                <p className="status-pill status-draft">STATUS: DRAFT</p>
              </header>
              <p className="muted">
                Fill in the fields below, watch the ciphertext preview, then save the draft.
              </p>
            </>
          ) : detail ? (
            <header className="editor-head">
              <h2>{detail.title || 'Untitled mission'}</h2>
              <p className={`status-pill status-${detail.status}`}>
                STATUS: {detail.status.toUpperCase()}
              </p>
            </header>
          ) : (
            <p className="muted">Loading mission…</p>
          )}

          <div className="field">
            <label htmlFor="admin-title">Title</label>
            <input
              id="admin-title"
              type="text"
              value={draft.title}
              onChange={(event) => update('title', event.target.value)}
            />
          </div>

          <div className="field">
            <label htmlFor="admin-riddle">Riddle</label>
            <input
              id="admin-riddle"
              type="text"
              value={draft.riddle_prompt}
              onChange={(event) => update('riddle_prompt', event.target.value)}
            />
          </div>

          <div className="field">
            <label htmlFor="admin-answers">Accepted riddle answers</label>
            <input
              id="admin-answers"
              type="text"
              value={answers}
              onChange={(event) => {
                setAnswers(event.target.value)
                setSaved(null)
              }}
              placeholder="lantern, a lantern"
            />
            <p className="field-help">Comma-separated. The first answer sets the shift.</p>
          </div>

          <div className="field">
            <label htmlFor="admin-keyrule">Key rule</label>
            <input
              id="admin-keyrule"
              type="text"
              value={draft.key_rule_description ?? ''}
              onChange={(event) => update('key_rule_description', event.target.value)}
            />
          </div>

          <div className="field">
            <label htmlFor="admin-plaintext">Plaintext</label>
            <input
              id="admin-plaintext"
              type="text"
              value={draft.plaintext_answer}
              onChange={(event) => update('plaintext_answer', event.target.value.toUpperCase())}
            />
          </div>

          <p className="cipher-preview">
            Shift {shift} → ciphertext: <span className="mono">{ciphertext || '—'}</span>
          </p>

          <p className={`verify-line${verified ? ' ok' : ''}`} role="status">
            {verified ? '✓ Verified: round-trip test passed' : verifyProblems.length > 0 ? `✕ ${verifyProblems.join(' · ')}` : 'Not verified yet'}
          </p>

          <div className="field">
            <label htmlFor="admin-narrative">Narrative</label>
            <textarea
              id="admin-narrative"
              rows={3}
              value={draft.narrative}
              onChange={(event) => update('narrative', event.target.value)}
            />
          </div>

          <div className="field">
            <label htmlFor="admin-clue">Contextual clue</label>
            <input
              id="admin-clue"
              type="text"
              value={draft.contextual_clue}
              onChange={(event) => update('contextual_clue', event.target.value)}
            />
          </div>

          {hints.map((hint, index) => (
            <div className="field" key={`hint-${index}`}>
              <label htmlFor={`admin-hint-${index}`}>Hint {index + 1}</label>
              <input
                id={`admin-hint-${index}`}
                type="text"
                value={hint}
                onChange={(event) => {
                  const next = [...hints]
                  next[index] = event.target.value
                  setHints(next)
                  setSaved(null)
                }}
              />
            </div>
          ))}

          <div className="editor-actions">
            {detail && (
              <Link className="btn" to={`/missions/${detail.slug}`}>
                Preview mission
              </Link>
            )}
            <button type="button" className="btn" onClick={() => void run(verify, 'Verified.')} disabled={busy}>
              Verify
            </button>
            <button type="button" className="btn" onClick={() => void run(saveDraft, 'Saved.')} disabled={busy}>
              Save draft
            </button>
            <button
              type="button"
              className="btn btn-primary"
              onClick={() =>
                void run(async () => {
                  if (selectedId === null) throw new ApiError(400, 'save_first', 'Save the draft before publishing.')
                  await api.publishMission(selectedId)
                  setDetail(await api.adminMission(selectedId))
                }, 'Mission published.')
              }
              disabled={busy}
            >
              Publish
            </button>
            {detail && detail.status === 'published' && (
              <button
                type="button"
                className="btn btn-danger"
                onClick={() =>
                  void run(async () => {
                    await api.retireMission(selectedId as number)
                    setDetail(await api.adminMission(selectedId as number))
                  }, 'Mission retired.')
                }
                disabled={busy}
              >
                Retire
              </button>
            )}
          </div>
        </section>
      </div>

      <section className="audit-section" aria-label="Audit log">
        <h2 className="audit-title">Recent changes</h2>
        {audit.error && <p className="muted">{audit.error}</p>}
        <ul className="audit-list">
          {(audit.data?.entries ?? []).slice(0, 20).map((entry: AuditEntry) => (
            <li key={entry.id}>
              <span className="audit-action">{entry.action}</span>
              <span className="audit-entity">{entry.entity_id}</span>
              <time dateTime={entry.created_at}>{new Date(entry.created_at).toLocaleString()}</time>
            </li>
          ))}
        </ul>
        {!audit.loading && (audit.data?.entries.length ?? 0) === 0 && (
          <p className="muted">No changes recorded yet.</p>
        )}
      </section>
    </>
  )
}