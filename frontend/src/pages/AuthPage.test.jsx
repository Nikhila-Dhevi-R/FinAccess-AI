import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, test, vi } from 'vitest';
import AuthPage from './AuthPage';
import { useAuth } from '../hooks/useAuth';

const navigate = vi.fn();
const signup = vi.fn();
const login = vi.fn();

vi.mock('../hooks/useAuth', () => ({ useAuth: vi.fn() }));
vi.mock('react-router-dom', () => ({ useNavigate: () => navigate }));

beforeEach(() => {
  vi.clearAllMocks();
  useAuth.mockReturnValue({ loading: false, error: '', signup, login });
  signup.mockResolvedValue({ id: 'user-1', username: 'nisha', email: 'nisha@example.com' });
  login.mockResolvedValue({ access_token: 'token-1', user: { username: 'nisha' } });
});

describe('AuthPage', () => {
  test('starts in login mode with only username and MPIN', () => {
    render(<AuthPage />);

    expect(screen.getByRole('heading', { name: /welcome back/i })).toBeInTheDocument();
    expect(screen.getByLabelText(/^username$/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/^mpin$/i)).toBeInTheDocument();
    expect(screen.queryByLabelText(/email/i)).not.toBeInTheDocument();
    expect(screen.queryByLabelText(/phone/i)).not.toBeInTheDocument();
  });

  test('shows signup fields without a phone input and filters MPIN to six digits', async () => {
    const user = userEvent.setup();
    render(<AuthPage />);
    await user.click(screen.getByRole('button', { name: /create account/i }));

    expect(screen.getByRole('heading', { name: /create your account/i })).toBeInTheDocument();
    expect(screen.getByLabelText(/email/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/create mpin/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/re-enter mpin/i)).toBeInTheDocument();
    expect(screen.queryByLabelText(/phone/i)).not.toBeInTheDocument();

    const mpin = screen.getByLabelText(/create mpin/i);
    await user.type(mpin, '12a3456789');
    expect(mpin).toHaveValue('123456');
  });

  test('shows MPIN mismatch without submitting signup', async () => {
    const user = userEvent.setup();
    render(<AuthPage />);
    await user.click(screen.getByRole('button', { name: /create account/i }));
    await user.type(screen.getByLabelText(/^username$/i), 'nisha');
    await user.type(screen.getByLabelText(/email/i), 'nisha@example.com');
    await user.type(screen.getByLabelText(/create mpin/i), '123456');
    await user.type(screen.getByLabelText(/re-enter mpin/i), '654321');
    await user.click(screen.getByRole('button', { name: /^sign up$/i }));

    expect(await screen.findByRole('alert')).toHaveTextContent(/do not match/i);
    expect(signup).not.toHaveBeenCalled();
  });

  test('submits signup, switches to login, and logs in', async () => {
    const user = userEvent.setup();
    render(<AuthPage />);
    await user.click(screen.getByRole('button', { name: /create account/i }));
    await user.type(screen.getByLabelText(/^username$/i), 'nisha');
    await user.type(screen.getByLabelText(/email/i), 'nisha@example.com');
    await user.type(screen.getByLabelText(/create mpin/i), '123456');
    await user.type(screen.getByLabelText(/re-enter mpin/i), '123456');
    await user.click(screen.getByRole('button', { name: /^sign up$/i }));

    await waitFor(() => expect(signup).toHaveBeenCalledWith({
      username: 'nisha',
      email: 'nisha@example.com',
      mpin: '123456',
      mpinConfirmation: '123456',
    }));
    expect(await screen.findByText(/account created/i)).toBeInTheDocument();

    await user.type(screen.getByLabelText(/^mpin$/i), '123456');
    await user.click(screen.getByRole('button', { name: /^log in$/i }));
    await waitFor(() => expect(login).toHaveBeenCalledWith({ username: 'nisha', mpin: '123456' }));
    expect(navigate).toHaveBeenCalledWith('/');
  });
});
