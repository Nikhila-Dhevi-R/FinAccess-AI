import { useEffect, useMemo, useState } from 'react';
import { AUTH_TOKEN_KEY, getCurrentAccount, loginAccount, signupAccount } from '../api/client';
import { AuthContext } from './context';

const USER_KEY = 'finaccess_auth_user';
const APP_SESSION_KEY = 'finaccess_session_id';

function readStorage(key, fallback = null) {
  try {
    return sessionStorage.getItem(key) || fallback;
  } catch {
    return fallback;
  }
}

function writeStorage(key, value) {
  try {
    if (value === null) sessionStorage.removeItem(key);
    else sessionStorage.setItem(key, value);
  } catch {
    // Keep the in-memory auth state usable when storage is blocked.
  }
}

function getErrorMessage(error, fallback = 'We could not complete authentication. Please try again.') {
  return error?.response?.data?.detail?.message || error?.message || fallback;
}

export function AuthProvider({ children }) {
  const [token, setToken] = useState(() => readStorage(AUTH_TOKEN_KEY));
  const [user, setUser] = useState(() => {
    const saved = readStorage(USER_KEY);
    try {
      return saved ? JSON.parse(saved) : null;
    } catch {
      return null;
    }
  });
  const [loading, setLoading] = useState(() => Boolean(readStorage(AUTH_TOKEN_KEY)));
  const [error, setError] = useState('');

  useEffect(() => {
    let active = true;
    const existingToken = readStorage(AUTH_TOKEN_KEY);
    if (!existingToken) {
      return () => { active = false; };
    }

    getCurrentAccount()
      .then((account) => {
        if (!active) return;
        setUser(account);
        writeStorage(USER_KEY, JSON.stringify(account));
      })
      .catch(() => {
        if (!active) return;
        writeStorage(AUTH_TOKEN_KEY, null);
        writeStorage(USER_KEY, null);
        writeStorage(APP_SESSION_KEY, null);
        setToken(null);
        setUser(null);
      })
      .finally(() => {
        if (active) setLoading(false);
      });

    return () => { active = false; };
  }, []);

  const signup = async (credentials) => {
    setError('');
    try {
      return await signupAccount(credentials);
    } catch (requestError) {
      const message = getErrorMessage(requestError);
      setError(message);
      throw requestError;
    }
  };

  const login = async (credentials) => {
    setError('');
    setLoading(true);
    try {
      const response = await loginAccount(credentials);
      writeStorage(AUTH_TOKEN_KEY, response.access_token);
      writeStorage(USER_KEY, JSON.stringify(response.user));
      setToken(response.access_token);
      setUser(response.user);
      return response;
    } catch (requestError) {
      const message = getErrorMessage(requestError, 'Username or MPIN is incorrect.');
      setError(message);
      throw requestError;
    } finally {
      setLoading(false);
    }
  };

  const logout = () => {
    writeStorage(AUTH_TOKEN_KEY, null);
    writeStorage(USER_KEY, null);
    writeStorage(APP_SESSION_KEY, null);
    setToken(null);
    setUser(null);
    setError('');
  };

  const value = useMemo(() => ({
    user,
    token,
    loading,
    error,
    isAuthenticated: Boolean(token && user),
    signup,
    login,
    logout,
  }), [user, token, loading, error]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
