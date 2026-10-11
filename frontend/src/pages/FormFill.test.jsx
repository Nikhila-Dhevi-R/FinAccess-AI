import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, test, vi } from 'vitest';
import FormFill from './FormFill';
import { getOtpStatus, uploadForm, getNextField, submitFieldAnswer } from '../api/client';
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
  ChallengePrompt: () => <div data-testid="randomized-challenge">Randomized phrase challenge</div>,
}));
vi.mock('../components/PhoneVerify', () => ({
  PhoneVerify: ({ onVerified }) => (
    <div data-testid="phone-verify">
      <button type="button" onClick={() => onVerified({ verified: true })}>Verify SMS</button>
    </div>
  ),
}));

vi.mock('../api/client', () => ({
  getOtpStatus: vi.fn(),
  uploadForm: vi.fn(),
  getNextField: vi.fn(),
  submitFieldAnswer: vi.fn(),
  createChallenge: vi.fn(),
  skipFormField: vi.fn(),
  finalizeForm: vi.fn(),
  resolveBackendUrl: vi.fn((path) => path),
  fetchDemoTemplate: vi.fn(),
  createSession: vi.fn(),
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
});

describe('FormFill SMS gate', () => {
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

  test('keeps the randomized phrase challenge after upload and field answer', async () => {
    const user = userEvent.setup();
    getOtpStatus.mockResolvedValue({ session_id: 'session-1', verified: true, masked_phone: '+91 XXXXXX3218' });
    uploadForm.mockResolvedValue({ form_id: 'form-1', fields, total_fields: 3 });
    getNextField.mockResolvedValue({
      field: { ...fields[2], status: 'asked' },
      progress: { completed: 0, total: 3, percentage: 0 },
      question_audio_text: fields[2].question_text,
      is_complete: false,
    });
    submitFieldAnswer.mockResolvedValue({
      validation_passed: true,
      interpreted_value: 'Ram Kumar',
      readback_text: 'I heard Ram Kumar',
      nonce_id: 'nonce-1',
      challenge_digits: '1 2 3 4',
      challenge_phrase: 'one two three four',
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

    expect(await screen.findByTestId('randomized-challenge')).toBeInTheDocument();
    expect(screen.queryByTestId('phone-verify')).not.toBeInTheDocument();
    expect(screen.queryByText(/otpconfirmationmodal/i)).not.toBeInTheDocument();
  });
});
