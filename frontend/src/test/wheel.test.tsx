import { fireEvent, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'

import { CipherWheel } from '../components/CipherWheel'
import { decodeCaesar } from '../lib/caesar'

const CIPHERTEXT = 'Htzsy jfhm mtzw zsynq ymj kjwwd fwwnajx'
const PLAINTEXT = 'Count each hour until the ferry arrives'
const SHIFT = 5

describe('decodeCaesar', () => {
  it('shifts letters back and passes everything else through', () => {
    expect(decodeCaesar(CIPHERTEXT, SHIFT)).toBe(PLAINTEXT)
    expect(decodeCaesar('ABC xyz', 0)).toBe('ABC xyz')
    expect(decodeCaesar('A-1 b!', 1)).toBe('Z-1 a!')
    expect(decodeCaesar('the ferry, 3 times', 26)).toBe('the ferry, 3 times')
  })
})

describe('CipherWheel', () => {
  it('shows the ciphertext as the initial reading', () => {
    render(<CipherWheel ciphertext={CIPHERTEXT} onSubmit={vi.fn()} />)
    expect(screen.getByTestId('wheel-ciphertext')).toHaveTextContent(CIPHERTEXT)
    expect(screen.getByTestId('wheel-reading')).toHaveTextContent(CIPHERTEXT)
    expect(screen.getByLabelText(/turn the wheel/i)).toHaveValue('0')
  })

  it('turns the wheel with the slider and updates the reading', async () => {
    render(<CipherWheel ciphertext={CIPHERTEXT} onSubmit={vi.fn()} />)
    const slider = screen.getByLabelText(/turn the wheel/i)

    fireEvent.change(slider, { target: { value: String(SHIFT) } })
    expect(screen.getByTestId('wheel-reading')).toHaveTextContent(PLAINTEXT)

    // turning away from the key garbles the reading again
    fireEvent.change(slider, { target: { value: '12' } })
    expect(screen.getByTestId('wheel-reading')).not.toHaveTextContent(PLAINTEXT)

    // keyboard control works on the same control
    fireEvent.change(slider, { target: { value: '0' } })
    await userEvent.tab()
    expect(document.activeElement).toBe(slider)
  })

  it('submits exactly what the wheel currently reads', async () => {
    const onSubmit = vi.fn()
    render(<CipherWheel ciphertext={CIPHERTEXT} onSubmit={onSubmit} />)

    // wrong position first
    fireEvent.change(screen.getByLabelText(/turn the wheel/i), { target: { value: '2' } })
    await userEvent.click(screen.getByRole('button', { name: /check this reading/i }))
    expect(onSubmit).toHaveBeenCalledTimes(1)
    expect(onSubmit).toHaveBeenCalledWith(screen.getByTestId('wheel-reading').textContent)

    // aligned to the key, the reading is the plaintext
    fireEvent.change(screen.getByLabelText(/turn the wheel/i), { target: { value: String(SHIFT) } })
    await userEvent.click(screen.getByRole('button', { name: /check this reading/i }))
    expect(onSubmit).toHaveBeenLastCalledWith(PLAINTEXT)
  })

  it('marks the submit button busy', () => {
    render(<CipherWheel ciphertext={CIPHERTEXT} busy onSubmit={vi.fn()} />)
    expect(screen.getByRole('button', { name: /checking/i })).toBeDisabled()
  })
})
