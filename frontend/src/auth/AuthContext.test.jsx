import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, test, vi } from 'vitest';
import { AuthProvider } from './AuthContext';
import { useAuth } from '../hooks/useAuth';
import { getCurrentAccount, loginAccount, signupAccount } from '../api/client';

vi.mock('../api/client', () => ({
  AUTH_TOKEN_KEY: 'finaccess_auth_token',
  getCurrentAccount: vi.fn(),
  loginAccount: vi.fn(),
  signupAccount: vi.fn(),
}));

function Probe() {
  const { user, loading, error, isAuthenticated, signup, login, logout } = useAuth();
  return (
    <div>
      <span data-testid="loading">{String(loading)}</span>
      <span data-testid="authenticated">{String(isAuthenticated)}</span>
      <span data-testid="user">{user?.username || ''}</span>
      <span data-testid="error">{error || ''}</span>
      <button type="button" onClick={() => signup({ username: 'new_user', email: 'new@example.com', mpin: '123456', mpinConfirmation: '123456' })}>Signup</button>
      <button type="button" onClick={() => login({ username: 'new_user', mpin: '123456' })}>Login</button>
      <button type="button" onClick={logout}>Logout</button>
    </div>
  );
}

beforeEach(() => {
  sessionStorage.clear();
  vi.clearAllMocks();
  getCurrentAccount.mockResolvedValue(null);
});

describe('AuthProvider', () => {
  test('sends signup credentials without a phone number and does not store an MPIN', async () => {
    const user = userEvent.setup();
    signupAccount.mockResolvedValue({ id: 'user-1', username: 'new_user', email: 'new@example.com' });

    render(<AuthProvider><Probe /></AuthProvider>);
    await user.click(screen.getByRole('button', { name: 'Signup' }));

    await waitFor(() => expect(signupAccount).toHaveBeenCalledWith({
      username: 'new_user',
      email: 'new@example.com',
      mpin: '123456',
      mpinConfirmation: '123456',
    }));
    expect(sessionStorage.getItem('finaccess_auth_token')).toBeNull();
    expect(sessionStorage.getItem('finaccess_mpin')).toBeNull();
  });

  test('persists login token and restores the account on refresh', async () => {
    const user = userEvent.setup();
    const account = { id: 'user-2', username: 'new_user', email: 'new@example.com' };
    loginAccount.mockResolvedValue({ access_token: 'token-2', token_type: 'bearer', user: account });

    const { unmount } = render(<AuthProvider><Probe /></AuthProvider>);
    await user.click(screen.getByRole('button', { name: 'Login' }));
    expect(await screen.findByTestId('user')).toHaveTextContent('new_user');
    expect(sessionStorage.getItem('finaccess_auth_token')).toBe('token-2');

    unmount();
    getCurrentAccount.mockResolvedValue(account);
    render(<AuthProvider><Probe /></AuthProvider>);
    expect(await screen.findByTestId('authenticated')).toHaveTextContent('true');
    expect(screen.getByTestId('user')).toHaveTextContent('new_user');
  });

  test('clears account and app session storage on logout or invalid token', async () => {
    const user = userEvent.setup();
    sessionStorage.setItem('finaccess_auth_token', 'bad-token');
    sessionStorage.setItem('finaccess_session_id', 'session-1');
    getCurrentAccount.mockRejectedValue(new Error('invalid token'));

    render(<AuthProvider><Probe /></AuthProvider>);
    await waitFor(() => expect(sessionStorage.getItem('finaccess_auth_token')).toBeNull());
    expect(sessionStorage.getItem('finaccess_session_id')).toBeNull();

    loginAccount.mockResolvedValue({
      access_token: 'token-3',
      token_type: 'bearer',
      user: { id: 'user-3', username: 'logout_user', email: 'logout@example.com' },
    });
    await user.click(screen.getByRole('button', { name: 'Login' }));
    await user.click(screen.getByRole('button', { name: 'Logout' }));
    expect(screen.getByTestId('authenticated')).toHaveTextContent('false');
    expect(sessionStorage.getItem('finaccess_auth_token')).toBeNull();
  });
});
