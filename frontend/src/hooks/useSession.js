/**
 * useSession — manages session lifecycle (stored in sessionStorage)
 *
 * Session id and language live in one shared store, so changing the language anywhere
 * (navbar, voice assistant) switches the whole site at once — every page re-renders.
 */

import { useState, useSyncExternalStore } from 'react';
import { createSession } from '../api/client';

function readStorage(key, fallback) {
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
    // storage blocked (private mode) — the in-memory store still works
  }
}

let shared = {
  sessionId: readStorage('finaccess_session_id', null),
  language: readStorage('finaccess_language', 'en'),
};
const listeners = new Set();

function update(patch) {
  shared = { ...shared, ...patch };
  listeners.forEach((listener) => listener());
}

function subscribe(listener) {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

const getSnapshot = () => shared;

if (typeof document !== 'undefined') document.documentElement.lang = shared.language;

export function setSiteLanguage(lang) {
  if (lang === shared.language) return;
  writeStorage('finaccess_language', lang);
  // whatever was being read aloud was in the old language
  try {
    window.speechSynthesis?.cancel();
  } catch {
    // ignore
  }
  if (typeof document !== 'undefined') document.documentElement.lang = lang;
  update({ language: lang });
}

export function useSession() {
  const { sessionId, language } = useSyncExternalStore(subscribe, getSnapshot);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const startSession = async (lang = 'en') => {
    setLoading(true);
    setError(null);
    try {
      const session = await createSession(lang);
      writeStorage('finaccess_session_id', session.id);
      update({ sessionId: session.id });
      setSiteLanguage(lang);
      return session;
    } catch (e) {
      setError(e.message);
      throw e;
    } finally {
      setLoading(false);
    }
  };

  const changeLanguage = (lang) => setSiteLanguage(lang);

  const clearSession = () => {
    writeStorage('finaccess_session_id', null);
    update({ sessionId: null });
  };

  return { sessionId, language, loading, error, startSession, changeLanguage, clearSession };
}
