import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { StrictMode } from 'react';
import { beforeEach, describe, expect, test, vi } from 'vitest';
import FormFill from './FormFill';
import { createSession, getOtpStatus, uploadForm, getNextField, submitFieldAnswer, createChallenge, finalizeForm } from '../api/client';
import { useSession } from '../hooks/useSession';

vi.mock('../hooks/useSession', () => ({ useSession: vi.fn() }));

vi.mock('../hooks/useSpeech', () => ({
  useSpeech: () => ({
    speak: vi.fn(),
    listen: vi.fn().mockResolvedValue(''),
    stopListening: vi.fn(),
    isListening: false,
    isSpeaking: false,
    stopSpeaking: vi.fn(),
    transcript: '',
    setTranscript: vi.fn(),
    error: null,
    clearError: vi.fn(),
  }),
}));

vi.mock('../components/VoiceButton', () => ({ VoiceButton: () => <button type="button">Voice</button> }));
vi.mock('../components/ChallengePrompt', () => ({
  ChallengePrompt: ({ onSuccess }) => (
    <div data-testid="randomized-challenge">
      <button type="button" onClick={() => onSuccess?.()}>Complete Challenge</button>
    </div>
  ),
}));
vi.mock('../components/PhoneVerify', () => ({
  PhoneVerify: ({ onVerified }) => (
    <div data-testid="phone-verify">
      <button type="button" onClick={() => onVerified({ verified: true })}>Verify SMS</button>
    </div>
  ),
}));

vi.mock('../api/client', () => ({
  createSession: vi.fn(),
  getOtpStatus: vi.fn(),
  uploadForm: vi.fn(),
  getNextField: vi.fn(),
  submitFieldAnswer: vi.fn(),
  createChallenge: vi.fn(),
  skipFormField: vi.fn(),
  finalizeForm: vi.fn(),
  resolveBackendUrl: vi.fn((path) => path),
  fetchDemoTemplate: vi.fn(),
}));

const fields = [
  { id: 'field-1', label: 'First', status: 'pending', question_text: 'What is the first answer?' },
  { id: 'field-2', label: 'Second', status: 'pending', question_text: 'What is the second answer?' },
  { id: 'field-3', label: 'Third', status: 'pending', question_text: 'What is the third answer?' },
];

beforeEach(() => {
  vi.clearAllMocks();
  useSession.mockReturnValue({
    sessionId: null,
    language: 'en',
    startSession: vi.fn().mockResolvedValue({ id: 'session-1' }),
  });
  getOtpStatus.mockResolvedValue({ session_id: 'session-1', verified: false, masked_phone: null });
  createSession.mockResolvedValue({ id: 'session-1' });
});

describe('FormFill SMS gate', () => {
  test('starts a fresh session so a page refresh requires phone verification again', async () => {
    useSession.mockReturnValue({
      sessionId: 'previously-verified-session',
      language: 'en',
      startSession: vi.fn(),
    });
    createSession.mockResolvedValue({ id: 'fresh-session' });
    getOtpStatus.mockResolvedValue({ session_id: 'fresh-session', verified: false, masked_phone: null });

    render(<StrictMode><FormFill /></StrictMode>);

    expect(await screen.findByTestId('phone-verify')).toBeInTheDocument();
    expect(createSession).toHaveBeenCalledWith('en');
    expect(getOtpStatus).toHaveBeenCalledWith('fresh-session');
  });

  test('shows phone verification before any form-upload controls for an unverified session', async () => {
    render(<FormFill />);

    expect(await screen.findByTestId('phone-verify')).toBeInTheDocument();
    expect(screen.queryByText(/choose form document/i)).not.toBeInTheDocument();
    expect(getOtpStatus).toHaveBeenCalledWith('session-1');
  });

  test('shows the existing upload phase after a verified session status', async () => {
    getOtpStatus.mockResolvedValue({ session_id: 'session-1', verified: true, masked_phone: '+91 XXXXXX3217' });

    render(<FormFill />);

    expect(await screen.findByText(/choose form document/i)).toBeInTheDocument();
    expect(screen.queryByTestId('phone-verify')).not.toBeInTheDocument();
  });

  test('shows the randomized phrase challenge only before final submission', async () => {
    const user = userEvent.setup();
    getOtpStatus.mockResolvedValue({ session_id: 'session-1', verified: true, masked_phone: '+91 XXXXXX3218' });
    uploadForm.mockResolvedValue({ form_id: 'form-1', fields, total_fields: 3 });
    getNextField
      .mockResolvedValueOnce({
        field: { ...fields[2], status: 'asked' },
        progress: { completed: 0, total: 3, percentage: 0 },
        question_audio_text: fields[2].question_text,
        is_complete: false,
      })
      .mockResolvedValueOnce({
        field: null,
        progress: { completed: 3, total: 3, percentage: 100 },
        question_audio_text: 'All questions complete',
        is_complete: true,
      });
    submitFieldAnswer.mockResolvedValue({
      validation_passed: true,
      interpreted_value: 'Ram Kumar',
      readback_text: 'I heard Ram Kumar',
      nonce_id: 'nonce-1',
      challenge_digits: '1 2 3 4',
      challenge_phrase: 'one two three four',
    });
    createChallenge.mockResolvedValue({
      nonce_id: 'final-nonce-1',
      challenge_digits: '5 6 7 8',
      challenge_phrase: 'five six seven eight',
      challenge_audio_text: 'To confirm, please say the 4 digits: 5, 6, 7, 8',
    });

    render(<FormFill />);
    await screen.findByText(/choose form document/i);
    const fileInput = document.querySelector('input[type="file"]');
    fireEvent.change(fileInput, { target: { files: [new File(['form'], 'form.pdf', { type: 'application/pdf' })] } });
    await waitFor(() => expect(uploadForm).toHaveBeenCalled());
    await waitFor(() => expect(screen.getByText(fields[2].question_text)).toBeInTheDocument(), { timeout: 3000 });

    await user.type(screen.getByPlaceholderText(/or type answer here/i), 'Ram Kumar');
    await user.click(screen.getByRole('button', { name: /^submit$/i }));
    await waitFor(() => expect(screen.getAllByText(/correct/i).length).toBeGreaterThan(0));
    const confirmButton = screen.getAllByRole('button').find((button) => /correct/i.test(button.textContent));
    await user.click(confirmButton);

    expect(screen.queryByTestId('randomized-challenge')).not.toBeInTheDocument();
    expect(await screen.findByText(/form review/i, {}, { timeout: 3500 })).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: /authorize.*generate pdf/i }));
    expect(createChallenge).toHaveBeenCalledWith('session-1', 'submit_form', 'form-1');
    expect(await screen.findByTestId('randomized-challenge')).toBeInTheDocument();
    expect(screen.queryByTestId('phone-verify')).not.toBeInTheDocument();
    expect(screen.queryByText(/otpconfirmationmodal/i)).not.toBeInTheDocument();
  }, 15000);

  test('allows filling another form after completing one, cleanly resetting state and download URL', async () => {
    const user = userEvent.setup();
    getOtpStatus.mockResolvedValue({ session_id: 'session-1', verified: true, masked_phone: '+91 XXXXXX3219' });
    uploadForm.mockResolvedValueOnce({ form_id: 'form-1', fields, total_fields: 3 });
    finalizeForm.mockResolvedValueOnce({ form_id: 'form-1', pdf_url: '/forms/form-1/download' });
    getNextField.mockResolvedValueOnce({
      field: null,
      progress: { completed: 3, total: 3, percentage: 100 },
      question_audio_text: 'Complete',
      is_complete: true,
    });

    render(<FormFill />);
    await screen.findByText(/choose form document/i);
    const fileInput = document.querySelector('input[type="file"]');
    fireEvent.change(fileInput, { target: { files: [new File(['form1'], 'form1.pdf', { type: 'application/pdf' })] } });

    // Review & summary screen appears
    expect(await screen.findByText(/form review/i, {}, { timeout: 3500 })).toBeInTheDocument();

    // Click Fill Another Form button
    // To get download URL, finalize first
    createChallenge.mockResolvedValueOnce({
      nonce_id: 'final-nonce-1',
      challenge_digits: '1 1 1 1',
      challenge_phrase: 'one one one one',
      challenge_audio_text: '1 1 1 1',
    });
    await user.click(screen.getByRole('button', { name: /authorize.*generate pdf/i }));
    // In test mock ChallengePrompt calls onSuccess
    const challenge = await screen.findByTestId('randomized-challenge');
    expect(challenge).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: /complete challenge/i }));

    // Now PDF ready screen shows download button and Fill Another Form button
    expect(await screen.findByRole('link', { name: /download/i })).toBeInTheDocument();
    const fillAnotherBtn = screen.getByRole('button', { name: /fill another form/i });
    expect(fillAnotherBtn).toBeInTheDocument();

    // Clicking Fill Another Form returns to upload phase
    await user.click(fillAnotherBtn);
    expect(await screen.findByText(/choose form document/i)).toBeInTheDocument();
    expect(screen.queryByRole('link', { name: /download/i })).not.toBeInTheDocument();
  }, 15000);
});
