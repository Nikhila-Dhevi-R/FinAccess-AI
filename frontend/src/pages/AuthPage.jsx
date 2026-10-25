import { useState } from 'react';
import { ArrowRight, KeyRound, LockKeyhole, Mail, ShieldCheck, UserRound } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';

const INITIAL_FORM = {
  username: '',
  email: '',
  mpin: '',
  mpinConfirmation: '',
};

function onlyDigits(value) {
  return value.replace(/\D/g, '').slice(0, 6);
}

export default function AuthPage() {
  const navigate = useNavigate();
  const { loading, error: authError, signup, login } = useAuth();
  const [mode, setMode] = useState('login');
  const [form, setForm] = useState(INITIAL_FORM);
  const [formError, setFormError] = useState('');
  const [success, setSuccess] = useState('');

  const isSignup = mode === 'signup';
  const setField = (field, value) => setForm((current) => ({ ...current, [field]: value }));

  const changeMode = (nextMode) => {
    setMode(nextMode);
    setFormError('');
    setSuccess('');
    setForm((current) => ({ ...current, mpin: '', mpinConfirmation: '' }));
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    setFormError('');
    setSuccess('');

    if (!form.username.trim()) {
      setFormError('Enter your username.');
      return;
    }
    if (form.mpin.length !== 6) {
      setFormError('MPIN must contain exactly 6 digits.');
      return;
    }

    if (isSignup) {
      if (!form.email.trim()) {
        setFormError('Enter your email address.');
        return;
      }
      if (form.mpin !== form.mpinConfirmation) {
        setFormError('The MPIN entries do not match.');
        return;
      }
      try {
        await signup({
          username: form.username.trim(),
          email: form.email.trim(),
          mpin: form.mpin,
          mpinConfirmation: form.mpinConfirmation,
        });
        setMode('login');
        setForm((current) => ({ ...current, email: '', mpin: '', mpinConfirmation: '' }));
        setSuccess('Account created. Log in with your username and MPIN.');
      } catch {
        // The provider exposes a safe user-facing error.
      }
      return;
    }

    try {
      await login({ username: form.username.trim(), mpin: form.mpin });
      navigate('/');
    } catch {
      // The provider exposes a safe user-facing error.
    }
  };

  return (
    <main className="auth-page">
      <section className="auth-card" aria-labelledby="auth-title">
        <div className="auth-card-glow" aria-hidden="true" />
        <div className="auth-card-header">
          <div className="auth-brand-mark" aria-hidden="true"><ShieldCheck size={26} /></div>
          <div>
            <p className="auth-eyebrow">FinAccess AI</p>
            <p className="auth-kicker">Secure access for your financial journey</p>
          </div>
        </div>

        <div className="auth-copy">
          <h1 id="auth-title">{isSignup ? 'Create your account' : 'Welcome back'}</h1>
          <p>{isSignup ? 'Set up your account to access voice-guided banking support.' : 'Log in to continue to your secure FinAccess workspace.'}</p>
        </div>

        <div className="auth-mode-switch" role="tablist" aria-label="Authentication mode">
          <button type="button" role="tab" aria-selected={!isSignup} className={!isSignup ? 'is-active' : ''} onClick={() => changeMode('login')}>Log in</button>
          <button type="button" role="tab" aria-selected={isSignup} className={isSignup ? 'is-active' : ''} onClick={() => changeMode('signup')}>Create account</button>
        </div>

        <form className="auth-form" onSubmit={handleSubmit} noValidate>
          <label className="auth-label" htmlFor="auth-username"><UserRound size={17} aria-hidden="true" /> Username</label>
          <input className="auth-input" id="auth-username" type="text" autoComplete="username" value={form.username} onChange={(event) => setField('username', event.target.value)} placeholder="Choose a username" />

          {isSignup && (
            <>
              <label className="auth-label" htmlFor="auth-email"><Mail size={17} aria-hidden="true" /> Email address</label>
              <input className="auth-input" id="auth-email" type="email" autoComplete="email" value={form.email} onChange={(event) => setField('email', event.target.value)} placeholder="you@example.com" />
            </>
          )}

          <label className="auth-label" htmlFor="auth-mpin"><KeyRound size={17} aria-hidden="true" /> {isSignup ? 'Create MPIN' : 'MPIN'}</label>
          <input className="auth-input auth-mpin-input" id="auth-mpin" type="password" inputMode="numeric" autoComplete={isSignup ? 'new-password' : 'current-password'} maxLength={6} value={form.mpin} onChange={(event) => setField('mpin', onlyDigits(event.target.value))} placeholder="Enter 6 digits" />

          {isSignup && (
            <>
              <label className="auth-label" htmlFor="auth-mpin-confirmation"><LockKeyhole size={17} aria-hidden="true" /> Re-enter MPIN</label>
              <input className="auth-input auth-mpin-input" id="auth-mpin-confirmation" type="password" inputMode="numeric" autoComplete="new-password" maxLength={6} value={form.mpinConfirmation} onChange={(event) => setField('mpinConfirmation', onlyDigits(event.target.value))} placeholder="Enter the same 6 digits" />
            </>
          )}

          {(formError || authError) && <p className="auth-message auth-message-error" role="alert">{formError || authError}</p>}
          {success && <p className="auth-message auth-message-success" role="status">{success}</p>}

          <button className="btn btn-primary auth-primary-button" type="submit" disabled={loading}>
            {loading ? 'Please wait…' : isSignup ? 'Sign up' : 'Log in'}
            <ArrowRight size={18} aria-hidden="true" />
          </button>
        </form>

        <p className="auth-footer-copy">
          {isSignup ? 'Already have an account?' : 'New to FinAccess AI?'}{' '}
          <button type="button" className="auth-link-button" onClick={() => changeMode(isSignup ? 'login' : 'signup')}>
            {isSignup ? 'Log in' : 'Create account'}
          </button>
        </p>
      </section>
    </main>
  );
}
