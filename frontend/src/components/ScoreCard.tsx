import type { ScoreBreakdown } from '../lib/api'

interface ScoreCardProps {
  score: ScoreBreakdown
  /** Bonus granted by completing the comprehension check. */
  comprehensionAwarded?: boolean
}

/**
 * Scores are computed on the server and rendered here purely for display.
 * Every value is labelled in words, so nothing depends on colour alone.
 */
export function ScoreCard({ score, comprehensionAwarded = false }: ScoreCardProps) {
  const comprehension = comprehensionAwarded ? 5 : score.comprehension_bonus

  return (
    <dl className="score-grid" data-testid="score-card">
      <div>
        <dt>Correct decryption</dt>
        <dd>{score.solve_points} pts</dd>
      </div>
      <div>
        <dt>No-hint bonus</dt>
        <dd>{score.no_hint_bonus} pts</dd>
      </div>
      <div>
        <dt>Time bonus</dt>
        <dd>{score.time_bonus} pts</dd>
      </div>
      <div>
        <dt>Comprehension</dt>
        <dd>{comprehension} pts</dd>
      </div>
      <div className="score-total">
        <dt>Total earned</dt>
        <dd>
          {score.total + comprehension} <span className="muted">/ 100</span>
        </dd>
      </div>
    </dl>
  )
}
