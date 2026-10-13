import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, test, vi } from 'vitest';
import { PhoneVerify } from './PhoneVerify';
import { sendOtp, verifyOtp } from '../api/client';

vi.mock('../api/client', () => ({
  sendOtp: vi.fn(),
  verifyOtp: vi.fn(),
}));

vi.mock('../hooks/useSpeech', () => ({
  useSpeech: () => ({ speak: vi.fn() }),
}));

beforeEach(() => {
  vi.clearAllMocks();
});

describe('PhoneVerify', () => {
  test('sends an SMS for the session and verifies a numeric one-time code', async () => {
    const user = userEvent.setup();
    const onVerified = vi.fn();
    sendOtp.mockResolvedValue({
      otp_id: 'otp-1',
      masked_phone: '+91 XXXXXX3215',
      code_length: 6,
      expires_in_seconds: 300,
      resend_after_seconds: 30,
    });
    verifyOtp.mockResolvedValue({ session_id: 'session-1', verified: true, masked_phone: '+91 XXXXXX3215' });

    render(<PhoneVerify sessionId="session-1" language="en" onVerified={onVerified} />);
    await user.type(screen.getByLabelText(/mobile number/i), '9876543215');
    await user.click(screen.getByRole('button', { name: /send code/i }));

    await waitFor(() => expect(sendOtp).toHaveBeenCalledWith('session-1', '9876543215', 'en'));
    expect(await screen.findByText(/sent to \+91 XXXXXX3215/i)).toBeInTheDocument();
    const codeInput = screen.getByLabelText(/verification code/i);
    expect(codeInput).toHaveAttribute('autocomplete', 'one-time-code');
    await user.type(codeInput, '123456');
    await user.click(screen.getByRole('button', { name: /verify phone/i }));

    await waitFor(() => expect(verifyOtp).toHaveBeenCalledWith('session-1', 'otp-1', '123456'));
    expect(onVerified).toHaveBeenCalledWith({ session_id: 'session-1', verified: true, masked_phone: '+91 XXXXXX3215' });
  });

  test('shows recoverable provider errors without exposing provider details', async () => {
    const user = userEvent.setup();
    const onError = vi.fn();
    sendOtp.mockRejectedValue({
      response: { data: { detail: { code: 'twilio_not_configured', message: 'SMS verification is temporarily unavailable.' } } },
    });

    render(<PhoneVerify sessionId="session-1" onError={onError} />);
    await user.type(screen.getByLabelText(/mobile number/i), '9876543216');
    await user.click(screen.getByRole('button', { name: /send code/i }));

    expect(await screen.findByText(/temporarily unavailable/i)).toBeInTheDocument();
    expect(screen.queryByText(/twilio|AC\d|VA\d/i)).not.toBeInTheDocument();
    expect(onError).toHaveBeenCalled();
  });
});
