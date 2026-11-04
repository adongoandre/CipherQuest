interface DispatchProps {
  /** Labelled plate holding ciphertext (or plaintext) in telegraph type. */
  label: string
  meta?: string
  text: string
  variant?: 'cipher' | 'plain'
}

/**
 * The dispatch plate: the element the product is remembered by.
 * Encrypted text always sits under a brass rail with a wax seal.
 */
export function Dispatch({ label, meta, text, variant = 'cipher' }: DispatchProps) {
  return (
    <div className="dispatch">
      <div className="dispatch-label">
        <span>{label}</span>
        {meta && <span>{meta}</span>}
      </div>
      <p
        className={variant === 'plain' ? 'ciphertext ciphertext-plain' : 'ciphertext'}
        data-testid="dispatch-text"
      >
        {text}
      </p>
    </div>
  )
}
