import React from 'react';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, test, vi } from 'vitest';
import { ChallengePrompt } from './ChallengePrompt';
import { respondToChallenge } from '../api/client';

vi.mock('../api/client', () => ({
  respondToChallenge: vi.fn(),
}));

vi.mock('../hooks/useSpeech', () => ({
  useSpeech: () => ({
    speak: vi.fn(),
    stopSpeaking: vi.fn(),
    listen: vi.fn().mockResolvedValue(''),
    stopListening: vi.fn(),
    isListening: false,
    isSpeaking: false,
    transcript: '',
    error: null,
  }),
}));

const nonce = {
  nonce_id: 'nonce-1',
  challenge_digits: '123',
  challenge_phrase: 'Say 1 2 3',
  expires_in_seconds: 30,
};

function renderPrompt(props = {}) {
  return render(
    <ChallengePrompt
      nonce={nonce}
      sessionId="session-1"
      language="en"
      {...props}
    />,
  );
}

async function submitDigits(value = '123') {
  const user = userEvent.setup();
  await user.type(screen.getByPlaceholderText('3 digits'), value);
  await user.click(screen.getByRole('button', { name: 'OK' }));
}

beforeEach(() => {
  vi.clearAllMocks();
});

describe('ChallengePrompt', () => {
  test('wrong nonce response never calls success', async () => {
    const onSuccess = vi.fn();
    const onFailure = vi.fn();
    respondToChallenge.mockResolvedValue({
      success: false,
      action_committed: false,
      message: 'Numbers did not match.',
    });
    renderPrompt({ onSuccess, onFailure });

    await submitDigits('999');

    await waitFor(() => expect(onFailure).toHaveBeenCalledTimes(1));
    expect(onSuccess).not.toHaveBeenCalled();
    expect(screen.queryByText('Voice confirmed successfully!')).not.toBeInTheDocument();
  });

  test('successful committed response triggers success once', async () => {
    const onSuccess = vi.fn();
    respondToChallenge.mockResolvedValue({ success: true, action_committed: true });
    renderPrompt({ onSuccess });

    await submitDigits();

    await waitFor(() => expect(onSuccess).toHaveBeenCalledTimes(1));
    expect(screen.getByText('Voice confirmed successfully!')).toBeInTheDocument();
  });

  test('in-flight guard prevents duplicate validation requests', async () => {
    let resolveRequest;
    respondToChallenge.mockReturnValue(new Promise((resolve) => {
      resolveRequest = resolve;
    }));
    const { container } = renderPrompt();
    const input = screen.getByPlaceholderText('3 digits');
    fireEvent.change(input, { target: { value: '123' } });
    const form = container.querySelector('form');

    fireEvent.submit(form);
    fireEvent.submit(form);

    expect(respondToChallenge).toHaveBeenCalledTimes(1);
    resolveRequest({ success: false, action_committed: false, message: 'No match' });
    await waitFor(() => expect(screen.getByText('No match')).toBeInTheDocument());
  });
});
