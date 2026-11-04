/**
 * Client-side Caesar decoding for the decoder wheel.
 *
 * Mirrors the backend rule: shift each letter back by the given number of
 * places (wrapping Z → A); spaces and punctuation pass through untouched.
 * The server still has the final say on any submitted answer.
 */

const ALPHABET = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'

export function normaliseShift(value: number): number {
  return ((Math.round(value) % 26) + 26) % 26
}

export function decodeCaesar(text: string, shift: number): string {
  const s = normaliseShift(shift)
  return text.replace(/[a-z]/gi, (ch) => {
    const index = ALPHABET.indexOf(ch.toUpperCase())
    if (index === -1) return ch
    const out = ALPHABET[(index - s + 26) % 26]
    return ch === ch.toUpperCase() ? out : out.toLowerCase()
  })
}

/**
 * The inverse of decodeCaesar: shift each letter forward by the given number
 * of places (wrapping Z → A), leaving spaces and punctuation untouched. Used
 * by the cipher lab, where the player can run the tool in either direction.
 */

export function encodeCaesar(text: string, shift: number): string {
  const s = normaliseShift(shift)
  return text.replace(/[a-z]/gi, (ch) => {
    const index = ALPHABET.indexOf(ch.toUpperCase())
    if (index === -1) return ch
    const out = ALPHABET[(index + s) % 26]
    return ch === ch.toUpperCase() ? out : out.toLowerCase()
  })
}
