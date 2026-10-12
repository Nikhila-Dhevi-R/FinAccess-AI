import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, expect, test, vi } from 'vitest';
import { Navbar } from './Navbar';
import { useAuth } from '../hooks/useAuth';

const logout = vi.fn();

vi.mock('../hooks/useAuth', () => ({ useAuth: vi.fn() }));
vi.mock('../hooks/useSession', () => ({
  useSession: () => ({ language: 'en', changeLanguage: vi.fn() }),
}));
vi.mock('../hooks/useSpeech', () => ({
  useSpeech: () => ({ speak: vi.fn(), isSpeaking: false, stopSpeaking: vi.fn() }),
}));

beforeEach(() => {
  vi.clearAllMocks();
  useAuth.mockReturnValue({ logout });
});

test('exposes a readable logout control that clears the account session', async () => {
  const user = userEvent.setup();
  render(<MemoryRouter><Navbar /></MemoryRouter>);

  await user.click(screen.getByRole('button', { name: /log out/i }));
  expect(logout).toHaveBeenCalledTimes(1);
});
