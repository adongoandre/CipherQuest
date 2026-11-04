import { fireEvent, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'

import { CipherPage } from '../pages/Cipher'
import { decodeCaesar, encodeCaesar } from '../lib/caesar'

describe('encodeCaesar', () => {
  it('is the inverse of decodeCaesar', () => {
    expect(encodeCaesar('HELLO WORLD', 3)).toBe('KHOOR ZRUOG')
    expect(decodeCaesar('KHOOR ZRUOG', 3)).toBe('HELLO WORLD')
    expect(decodeCaesar(encodeCaesar('HELLO WORLD', 3), 3)).toBe('HELLO WORLD')
    expect(encodeCaesar('Abc xyz', 3)).toBe('Def abc')
    expect(encodeCaesar('the ferry, 3 times', 0)).toBe('the ferry, 3 times')
    expect(decodeCaesar(encodeCaesar('Mixed CASE, punctuation!', 17), 17)).toBe(
      'Mixed CASE, punctuation!',
    )
  })
})

describe('CipherPage', () => {
  it('opens on the reference state: decrypt by 3', () => {
    render(<CipherPage />)

    expect(screen.getByRole('heading', { level: 1, name: /try the caesar cipher/i })).toBeInTheDocument()
    expect(screen.getByLabelText(/source string/i)).toHaveValue('HELLO WORLD')
    expect(screen.getByLabelText(/shift magnitude/i)).toHaveValue('3')
    expect(screen.getByTestId('caesar-input')).toHaveTextContent('HELLO WORLD')
    expect(screen.getByTestId('caesar-translation')).toHaveTextContent('EBIIL TLOIA')
    expect(screen.getByTestId('caesar-rotation')).toHaveTextContent('-3')
    expect(screen.getByRole('button', { name: 'Decrypt' })).toHaveAttribute('aria-pressed', 'true')
    expect(screen.getByRole('button', { name: 'Encrypt' })).toHaveAttribute('aria-pressed', 'false')

    // the inner ring sits three steps clockwise, so X lines up over A
    expect(document.querySelector('.caesar-wheel-disc')).toHaveAttribute('data-rotation', '3')
  })

  it('switches direction with the mode buttons', async () => {
    render(<CipherPage />)

    await userEvent.click(screen.getByRole('button', { name: 'Encrypt' }))

    expect(screen.getByRole('button', { name: 'Encrypt' })).toHaveAttribute('aria-pressed', 'true')
    expect(screen.getByRole('button', { name: 'Decrypt' })).toHaveAttribute('aria-pressed', 'false')
    expect(screen.getByTestId('caesar-translation')).toHaveTextContent('KHOOR ZRUOG')
    expect(screen.getByTestId('caesar-rotation')).toHaveTextContent('3')
    expect(document.querySelector('.caesar-wheel-disc')).toHaveAttribute('data-rotation', '-3')
  })

  it('recomputes when the shift changes', () => {
    render(<CipherPage />)

    fireEvent.change(screen.getByLabelText(/shift magnitude/i), { target: { value: '0' } })
    expect(screen.getByTestId('caesar-translation')).toHaveTextContent('HELLO WORLD')
    expect(screen.getByTestId('caesar-rotation')).toHaveTextContent('0')

    fireEvent.change(screen.getByLabelText(/shift magnitude/i), { target: { value: '13' } })
    expect(screen.getByTestId('caesar-translation')).toHaveTextContent('URYYB JBEYQ')
    expect(screen.getByTestId('caesar-rotation')).toHaveTextContent('-13')
  })

  it('recomputes as the source string is typed', () => {
    render(<CipherPage />)

    fireEvent.change(screen.getByLabelText(/source string/i), { target: { value: 'ABC' } })
    expect(screen.getByTestId('caesar-translation')).toHaveTextContent('XYZ')
  })

  it('shows a placeholder when the source string is emptied', () => {
    render(<CipherPage />)

    fireEvent.change(screen.getByLabelText(/source string/i), { target: { value: '' } })
    expect(screen.getByTestId('caesar-input')).toHaveTextContent('—')
    expect(screen.getByTestId('caesar-translation')).toHaveTextContent('—')
  })
})