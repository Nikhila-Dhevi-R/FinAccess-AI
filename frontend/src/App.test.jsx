import { render, screen } from '@testing-library/react';
import { beforeEach, describe, expect, test, vi } from 'vitest';
import App from './App';
import { useAuth } from './hooks/useAuth';

vi.mock('./hooks/useAuth', () => ({ useAuth: vi.fn() }));
vi.mock('./components/Navbar', () => ({ Navbar: () => <div data-testid="navbar">Navigation</div> }));
vi.mock('./components/FloatingVoiceBot', () => ({ FloatingVoiceBot: () => <div data-testid="voice-bot">Voice bot</div> }));
vi.mock('./components/SiteFooter', () => ({ SiteFooter: () => <div data-testid="footer">Footer</div> }));
vi.mock('./pages/AuthPage', () => ({ default: () => <div data-testid="auth-page">Auth page</div> }));
vi.mock('./pages/Landing', () => ({ default: () => <div data-testid="landing-page">Home app</div> }));
vi.mock('./pages/FormFill', () => ({ default: () => <div>Form fill</div> }));
vi.mock('./pages/Schemes', () => ({ default: () => <div>Schemes</div> }));
vi.mock('./pages/Guidance', () => ({ default: () => <div>Guidance</div> }));
vi.mock('./pages/FraudCheck', () => ({ default: () => <div>Fraud check</div> }));

function setAuthState(isAuthenticated) {
  useAuth.mockReturnValue({
    loading: false,
    isAuthenticated,
    user: isAuthenticated ? { username: 'nisha' } : null,
    error: '',
    logout: vi.fn(),
  });
}

beforeEach(() => {
  window.history.pushState({}, '', '/');
  vi.clearAllMocks();
});

describe('App account gate', () => {
  test('redirects unauthenticated visitors to auth without rendering the app shell', async () => {
    setAuthState(false);
    render(<App />);

    expect(await screen.findByTestId('auth-page')).toBeInTheDocument();
    expect(screen.queryByTestId('navbar')).not.toBeInTheDocument();
    expect(window.location.pathname).toBe('/auth');
  });

  test('renders the existing app shell for authenticated visitors', () => {
    setAuthState(true);
    render(<App />);

    expect(screen.getByTestId('navbar')).toBeInTheDocument();
    expect(screen.getByTestId('landing-page')).toBeInTheDocument();
    expect(screen.getByTestId('voice-bot')).toBeInTheDocument();
    expect(screen.getByTestId('footer')).toBeInTheDocument();
  });

  test('redirects authenticated visitors away from the auth page', async () => {
    window.history.pushState({}, '', '/auth');
    setAuthState(true);
    render(<App />);

    expect(await screen.findByTestId('landing-page')).toBeInTheDocument();
    expect(screen.queryByTestId('auth-page')).not.toBeInTheDocument();
    expect(window.location.pathname).toBe('/');
  });
});
