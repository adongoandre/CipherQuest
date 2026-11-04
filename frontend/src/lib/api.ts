/**
 * Typed client for the CipherQuest API.
 *
 * The browser only ever calls same-origin `/api/*` paths — Vite proxies them to
 * FastAPI in development, and the same origin is served in production.
 */

const SESSION_KEY = 'cipherquest.session'

/**
 * Pseudonymous progress key for a guest player.
 *
 * This is an application-level identifier, not a credential: it carries no
 * authority beyond "this browser's saved progress". It is deliberately held in
 * `sessionStorage` so it disappears when the tab closes. The documented
 * production hardening is to move it to an HttpOnly cookie (see README,
 * "Security notes").
 */
export function getSessionToken(): string | null {
  try {
    return window.sessionStorage.getItem(SESSION_KEY)
  } catch {
    return null
  }
}

export function storeSessionToken(token: string): void {
  try {
    window.sessionStorage.setItem(SESSION_KEY, token)
  } catch {
    /* storage disabled: progress simply will not persist */
  }
}

export class ApiError extends Error {
  readonly status: number
  readonly code: string
  readonly details: Record<string, unknown>

  constructor(status: number, code: string, message: string, details: Record<string, unknown> = {}) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.code = code
    this.details = details
  }
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers)
  headers.set('Content-Type', 'application/json')
  const token = getSessionToken()
  if (token) headers.set('X-Session-Token', token)

  const response = await fetch(`/api/v1${path}`, { ...init, headers })

  const issued = response.headers.get('X-Session-Token')
  if (issued) storeSessionToken(issued)

  if (!response.ok) {
    let code = 'request_failed'
    let message = `Request failed with status ${response.status}.`
    let details: Record<string, unknown> = {}
    try {
      const body = (await response.json()) as {
        error?: { code?: string; message?: string; details?: Record<string, unknown> }
      }
      if (body.error) {
        code = body.error.code ?? code
        message = body.error.message ?? message
        details = body.error.details ?? {}
      }
    } catch {
      /* non-JSON error body: keep the generic message */
    }
    throw new ApiError(response.status, code, message, details)
  }

  return (await response.json()) as T
}

function post<T>(path: string, body?: unknown): Promise<T> {
  return request<T>(path, {
    method: 'POST',
    body: body === undefined ? undefined : JSON.stringify(body),
  })
}

function get<T>(path: string): Promise<T> {
  return request<T>(path, { method: 'GET' })
}

// --- types -----------------------------------------------------------------

export type MissionStage = 'riddle' | 'key_reveal' | 'context_clue' | 'decrypt' | 'explanation'

export interface Brief {
  id: number
  slug: string
  title: string
  narrative: string
  difficulty: 'beginner' | 'intermediate' | 'advanced' | 'expert'
  cipher_type: string
  cipher_name: string
  estimated_minutes: number
  stage: MissionStage
  hint_count_total: number
  hints_revealed: number
  is_completed: boolean
  /** 1-based: which telling of this mission the session is playing. */
  telling_number: number
  /** Total tellings stored for this mission (original + alternatives). */
  telling_count: number
}

/**
 * What the server reveals after a correct riddle answer — deliberately not
 * the shift. Working out that the Caesar shift equals the letter count of the
 * answer is the puzzle; the progressive hints carry the player there.
 */
export interface KeyReveal {
  accepted_answer: string
  key_type: string
  parameter: number
  key_rule_description: string
}

export interface RiddlePayload extends Brief {
  riddle_prompt: string
}

export interface KeyPayload extends Brief {
  key_reveal: KeyReveal
}

export interface CluePayload extends KeyPayload {
  contextual_clue: string
}

export interface DecryptPayload extends CluePayload {
  ciphertext: string
  revealed_hints: string[]
}

export interface Solution {
  plaintext: string
  explanation: string
  worked_example: string
}

export interface ComprehensionCheck {
  question: string
  choices: string[]
  correct_index: number
  explanation: string
}

export interface ExplanationPayload extends DecryptPayload {
  solution: Solution
  /** Revealed only alongside the solution; worth 5 points. */
  comprehension_check: ComprehensionCheck | null
  /** What this session actually earned, restored after a reload. */
  earned_score: ScoreBreakdown | null
  comprehension_awarded: boolean
}

export interface RiddleResponse {
  correct: boolean
  stage: MissionStage
  attempts: number
  key_reveal: KeyReveal | null
  message: string
}

export interface AdvanceResponse {
  stage: MissionStage
  contextual_clue: string | null
  ciphertext: string | null
  message: string
}

export interface HintResponse {
  hint_number: number
  total_hints: number
  hint: string
  hints_used: number
  score_penalty_note: string
}

export interface ScoreBreakdown {
  total: number
  solve_points: number
  no_hint_bonus: number
  time_bonus: number
  comprehension_bonus: number
  hints_used: number
  elapsed_seconds: number | null
  breakdown: Record<string, string | boolean | number>
}

export interface DecryptResponse {
  correct: boolean
  stage: MissionStage
  attempts: number
  hints_used: number
  score: ScoreBreakdown | null
  solution: Solution | null
  message: string
  progress_awarded: boolean
  /** Revealed together with the solution; worth 5 points. */
  comprehension_check: ComprehensionCheck | null
}

export interface RevealResponse {
  stage: MissionStage
  solution: Solution
  score_awarded: number
  message: string
}

export interface ComprehensionResponse {
  correct: boolean
  earned: number
  total: number
  correct_index: number
  explanation: string
  awarded: boolean
}

export interface MissionListItem {
  id: number
  slug: string
  title: string
  difficulty: string
  cipher_type: string
  estimated_minutes: number
  display_order: number
  is_completed: boolean
}

export interface MissionListResponse {
  missions: MissionListItem[]
  daily_slug: string
}

export type MissionPayload =
  | RiddlePayload
  | KeyPayload
  | CluePayload
  | DecryptPayload
  | ExplanationPayload

export interface ProgressSummary {
  missions_completed: number
  total_puzzles_solved: number
  total_score: number
  xp: number
  completed_slugs: string[]
}

export interface ProgressResponse {
  progress: ProgressSummary
  missions: Array<{
    slug: string
    title: string
    difficulty: string
    display_order: number
    completed: boolean
    best_score: number
    completion_count: number
    comprehension_awarded: boolean
  }>
}

export interface FeedbackPayload {
  mission_slug: string
  clarity_rating?: 1 | 2 | 3 | 4 | 5
  learned?: 'yes' | 'a_little' | 'no'
  enjoyment_rating?: 1 | 2 | 3 | 4 | 5
  would_return?: 'yes' | 'maybe' | 'no'
  comment?: string
}

export interface HealthResponse {
  status: string
  app_env: string
  database: string
  version: string
  time: string
}

// --- mockup screens: home, compete, social, academy, rooms, admin ----------

export interface DailyMissionCard {
  slug: string
  title: string
  difficulty: string
  cipher_name: string
  estimated_minutes: number
  completed: boolean
  best_score: number | null
}

export interface ProgressStrip {
  level: number
  xp: number
  level_ceiling: number
  streak_days: number
  missions_solved: number
}

export interface ContinueLearning {
  cipher_slug: string
  cipher_name: string
  step: number
  total_steps: number
  title: string
}

export interface InvitationCard {
  id: number
  from_display_name: string
  kind: string
}

export interface FriendActivity {
  display_name: string
  action: string
  when: string | null
}

export interface HomeResponse {
  greeting: string
  progress: ProgressStrip
  daily_mission: DailyMissionCard | null
  week_dots: boolean[]
  weekly_cup: CupState
  continue_learning: ContinueLearning | null
  invitations: InvitationCard[]
  friend_activity: FriendActivity[]
  suggested_next: string | null
}

export interface StandingEntry {
  rank: number
  display_name: string
  score: number
  missions: number
  change: number | null
  is_you: boolean
}

export interface YourPosition {
  rank: number
  score: number
  missions: number
  gap_to_next: number
  next_rank_name: string | null
}

export type LeaderboardScope = 'week' | 'friends' | 'season' | 'all_time'

export interface LeaderboardResponse {
  scope: LeaderboardScope
  standings: StandingEntry[]
  you: YourPosition | null
  footer: string
  total_players: number
}

export interface CupState {
  week: string
  label: string
  status: 'scheduled' | 'open' | 'closed'
  opens_at: string
  closes_at: string
  seconds_until_open: number
  seconds_until_close: number
  participants: number
  you_entered: boolean
  your_score: number
  standings: StandingEntry[]
  you: YourPosition | null
  note: string
}

export interface Badge {
  key: string
  name: string
  description: string
  earned: boolean
}

export interface CipherMastery {
  cipher: string
  name: string
  lessons_completed: number
  lessons_total: number
}

export interface RecentMission {
  slug: string
  title: string
  best_score: number | null
  completed_at: string | null
}

export interface ProfileResponse {
  display_name: string
  is_guest: boolean
  is_admin: boolean
  level: number
  xp: number
  level_ceiling: number
  level_floor: number
  missions_solved: number
  streak_days: number
  longest_streak: number
  accuracy: number
  hints_used: number
  average_score: number
  time_played_minutes: number
  badges: Badge[]
  mastery: CipherMastery[]
  recent_missions: RecentMission[]
  joined_at: string
}

export interface SettingsResponse {
  display_name: string | null
  email: string | null
  is_guest: boolean
  accessibility: Record<string, boolean>
  privacy: Record<string, boolean>
  play_style: Record<string, boolean>
}

export interface FriendEntry {
  id: number
  display_name: string
  level: number
  status: 'offline' | 'recently_active'
}

export interface InvitationEntry {
  id: number
  from_display_name: string
  kind: 'cipher_duel'
  created_at: string
}

export interface BlockedEntry {
  id: number
  display_name: string
}

export interface FriendRequestEntry {
  id: number
  display_name: string
  level: number
  created_at: string
}

export interface FriendsResponse {
  friends: FriendEntry[]
  invitations: InvitationEntry[]
  pending_outgoing: InvitationEntry[]
  blocked: BlockedEntry[]
  requests_incoming: FriendRequestEntry[]
  requests_outgoing: FriendRequestEntry[]
}

export interface ActionResult {
  ok: boolean
  message: string
}

export type TrackStatus = 'not_started' | 'in_progress' | 'complete'

export interface TrackSummary {
  slug: string
  name: string
  blurb: string
  difficulty: string
  lessons_total: number
  lessons_completed: number
  current_step: number
  status: TrackStatus
}

export interface AcademyResponse {
  tracks: TrackSummary[]
  total_lessons_completed: number
  total_lessons: number
  suggested_next: string | null
}

export interface LessonSummary {
  step: number
  title: string
  summary: string
  completed: boolean
}

export interface TrackResponse {
  slug: string
  name: string
  blurb: string
  difficulty: string
  lessons: LessonSummary[]
  current_step: number
  xp_available: number
}

export interface LessonExample {
  input: string | null
  output: string | null
  caption: string | null
  interactive: string | null
  sample_text: string | null
  default_shift: number | null
}

export interface LessonResponse {
  slug: string
  track_name: string
  step: number
  title: string
  summary: string
  body: string[]
  example: LessonExample | null
  completed: boolean
  xp_awarded: number
  next_step: number | null
  total_steps: number
}

export interface LessonCompleteResponse {
  completed: boolean
  xp_awarded: number
  total_xp: number
  lessons_completed: number
  next_step: number | null
  finished_track: boolean
}

export interface RoomPlayerEntry {
  session_id: number
  display_name: string
  ready: boolean
  is_host: boolean
}

export interface RoomState {
  code: string
  mode: 'team_escape' | 'duel'
  status: 'waiting' | 'in_progress' | 'finished' | 'abandoned'
  host_session_id: number
  players: RoomPlayerEntry[]
  max_players: number
  you_are_host: boolean
  you_are_ready: boolean
  everyone_ready: boolean
  mission_slug: string | null
  mission_title: string | null
}

export interface AdminMissionSummary {
  id: number
  slug: string
  title: string
  status: 'draft' | 'published' | 'retired'
  difficulty: string
  cipher_type: string
  updated_at: string | null
  verified: boolean
  verify_problems: string[]
}

export interface VerifyResult {
  verified: boolean
  problems: string[]
  round_trip_ok: boolean
  parameter: number | null
  ciphertext: string | null
  plaintext: string | null
}

export interface AdminMissionDetail {
  id: number
  slug: string
  title: string
  status: 'draft' | 'published' | 'retired'
  difficulty: string
  cipher_type: string
  estimated_minutes: number
  narrative: string
  riddle_prompt: string
  accepted_riddle_answers: string[]
  key_rule_description: string
  contextual_clue: string
  plaintext_answer: string
  hints: string[]
  parameter: number | null
  ciphertext: string | null
  verification: VerifyResult
  updated_at: string | null
}

export interface MissionDraftRequest {
  title: string
  narrative: string
  riddle_prompt: string
  accepted_riddle_answers: string[]
  key_rule_description?: string
  contextual_clue: string
  plaintext_answer: string
  hints?: string[]
  difficulty?: string
  cipher_type?: string
  estimated_minutes?: number
}

export interface PublishResult {
  id: number
  status: 'draft' | 'published' | 'retired'
  message: string
}

export interface AuditEntry {
  id: number
  action: string
  entity_type: string
  entity_id: string
  detail: Record<string, unknown>
  created_at: string
}

export interface AuditListResponse {
  entries: AuditEntry[]
}

// --- endpoints -------------------------------------------------------------

export const api = {
  health: () => get<HealthResponse>('/health'),
  createSession: () => post<{ token: string; display_name: string | null; created: boolean }>('/session'),

  missions: () => get<MissionListResponse>('/missions'),
  daily: () => get<RiddlePayload>('/missions/daily'),
  mission: (slug: string) => get<MissionPayload>(`/missions/${slug}`),
  /**
   * Start the mission over. An unfinished mission replays the same telling;
   * a solved one moves on to its next telling, so nothing repeats.
   */
  restart: (slug: string) => post<MissionPayload>(`/missions/${slug}/restart`),

  submitRiddle: (slug: string, answer: string, idempotencyKey?: string) =>
    post<RiddleResponse>(`/missions/${slug}/riddle-attempt`, { answer, idempotency_key: idempotencyKey }),
  advance: (slug: string) => post<AdvanceResponse>(`/missions/${slug}/advance`),
  hint: (slug: string) => post<HintResponse>(`/missions/${slug}/hint`),
  submitDecrypt: (slug: string, answer: string, options: { elapsedSeconds?: number; idempotencyKey?: string } = {}) =>
    post<DecryptResponse>(`/missions/${slug}/decrypt-attempt`, {
      answer,
      elapsed_seconds: options.elapsedSeconds ?? null,
      idempotency_key: options.idempotencyKey ?? null,
    }),
  reveal: (slug: string, reason: 'stuck' | 'finished' = 'stuck') =>
    post<RevealResponse>(`/missions/${slug}/reveal`, { reason }),
  comprehension: (slug: string, choice: number) =>
    post<ComprehensionResponse>(`/missions/${slug}/comprehension`, { choice }),

  progress: () => get<ProgressResponse>('/progress'),
  feedback: (payload: FeedbackPayload) => post<{ saved: boolean; message: string }>('/feedback', payload),
  track: (eventName: string, missionSlug?: string) =>
    post<{ recorded: boolean }>('/analytics', { event_name: eventName, mission_slug: missionSlug }),

  // Home dashboard
  home: () => get<HomeResponse>('/home'),

  // Join / auth
  register: (payload: { display_name: string; email: string; password: string; accepted_terms: boolean }) =>
    post<{ token: string; display_name: string | null; created: boolean }>('/auth/register', payload),
  login: (payload: { email: string; password: string }) =>
    post<{ token: string; display_name: string | null; created: boolean }>('/auth/login', payload),
  me: () => get<ProfileResponse>('/auth/me'),

  // Profile & settings
  profile: () => get<ProfileResponse>('/profile'),
  settings: () => get<SettingsResponse>('/settings'),
  saveSettings: (payload: {
    display_name?: string
    accessibility?: Record<string, boolean>
    privacy?: Record<string, boolean>
    play_style?: Record<string, boolean>
  }) => post<SettingsResponse>('/settings', payload),
  deleteAccount: () => post<{ deleted: boolean; message: string }>('/account/delete', {}),

  // Compete
  leaderboards: (scope: LeaderboardScope = 'week') =>
    get<LeaderboardResponse>(`/compete/leaderboards?scope=${scope}`),
  cup: () => get<CupState>('/compete/cup'),
  enterCup: () => post<{ entered: boolean; week: string; message: string }>('/compete/cup/enter'),

  // Friends & invitations
  friends: () => get<FriendsResponse>('/friends'),
  friendRequest: (display_name: string) =>
    post<ActionResult>('/friends/request', { display_name }),
  friendRespond: (friendship_id: number, action: 'accept' | 'decline') =>
    post<ActionResult>('/friends/respond', { friendship_id, action }),
  duelInvite: (display_name: string) => post<ActionResult>('/invites', { display_name }),
  duelInviteRespond: (invite_id: number, action: 'accept' | 'decline') =>
    post<ActionResult>('/invites/respond', { invite_id, action }),
  block: (display_name: string) => post<ActionResult>('/blocks', { display_name }),

  // Academy
  academy: () => get<AcademyResponse>('/lessons'),
  trackDetail: (slug: string) => get<TrackResponse>(`/lessons/${slug}`),
  lesson: (slug: string, step: number) => get<LessonResponse>(`/lessons/${slug}/${step}`),
  completeLesson: (slug: string, step: number) =>
    post<LessonCompleteResponse>(`/lessons/${slug}/${step}/complete`),

  // Rooms
  createRoom: (mode: 'team_escape' | 'duel' = 'team_escape') =>
    post<RoomState>('/rooms', { mode }),
  joinRoom: (code: string) => post<RoomState>('/rooms/join', { code }),
  room: (code: string) => get<RoomState>(`/rooms/${code}`),
  readyRoom: (code: string, ready: boolean) =>
    post<RoomState>(`/rooms/${code}/ready`, { ready }),
  leaveRoom: (code: string) => post<RoomState>(`/rooms/${code}/leave`),
  startRoom: (code: string) => post<RoomState>(`/rooms/${code}/start`),

  // Admin editor
  adminMissions: () => get<AdminMissionSummary[]>('/admin/missions'),
  adminMission: (id: number) => get<AdminMissionDetail>(`/admin/missions/${id}`),
  createMission: (payload: MissionDraftRequest) =>
    post<AdminMissionDetail>('/admin/missions', payload),
  updateMission: (id: number, payload: MissionDraftRequest) =>
    post<AdminMissionDetail>(`/admin/missions/${id}`, payload),
  verifyMission: (id: number) => post<VerifyResult>(`/admin/missions/${id}/verify`),
  publishMission: (id: number) => post<PublishResult>(`/admin/missions/${id}/publish`),
  retireMission: (id: number) => post<PublishResult>(`/admin/missions/${id}/retire`),
  adminAudit: () => get<AuditListResponse>('/admin/audit'),
}
