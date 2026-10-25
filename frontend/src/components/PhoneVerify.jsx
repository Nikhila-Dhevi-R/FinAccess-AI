import { useEffect, useMemo, useState } from 'react';
import { CheckCircle2, MessageSquare, RefreshCw, ShieldCheck } from 'lucide-react';
import { sendOtp, verifyOtp } from '../api/client';
import { useSpeech } from '../hooks/useSpeech';

const TEXTS = {
  en: {
    title: 'Verify your phone before filling the form',
    subtitle: 'We will send one SMS code to keep your form session secure.',
    phone: 'Mobile number',
    phoneHint: 'Enter your 10-digit Indian mobile number',
    send: 'Send code',
    sentTo: 'Code sent to',
    code: 'Verification code',
    codeHint: 'Enter the 6-digit code',
    verify: 'Verify phone',
    resend: 'Resend code',
    wait: 'Resend available in',
    seconds: 's',
    change: 'Use a different number',
    verified: 'Phone verified. You can now upload your form.',
    genericError: 'We could not complete verification. Please try again.',
    sending: 'Sending…',
    checking: 'Checking…',
  },
  hi: {
    title: 'फॉर्म भरने से पहले अपना फोन सत्यापित करें',
    subtitle: 'आपके फॉर्म सत्र को सुरक्षित रखने के लिए एक SMS कोड भेजेंगे।',
    phone: 'मोबाइल नंबर',
    phoneHint: 'अपना 10 अंकों का मोबाइल नंबर दर्ज करें',
    send: 'कोड भेजें',
    sentTo: 'कोड भेजा गया',
    code: 'सत्यापन कोड',
    codeHint: '6 अंकों का कोड दर्ज करें',
    verify: 'फोन सत्यापित करें',
    resend: 'कोड फिर भेजें',
    wait: 'फिर भेजने के लिए',
    seconds: 'सेकंड',
    change: 'दूसरा नंबर इस्तेमाल करें',
    verified: 'फोन सत्यापित है। अब आप फॉर्म अपलोड कर सकते हैं।',
    genericError: 'सत्यापन पूरा नहीं हुआ। कृपया फिर कोशिश करें।',
    sending: 'भेज रहे हैं…',
    checking: 'जाँच रहे हैं…',
  },
  ta: {
    title: 'படிவத்தை நிரப்புவதற்கு முன் உங்கள் தொலைபேசியைச் சரிபார்க்கவும்',
    subtitle: 'உங்கள் படிவ அமர்வைப் பாதுகாக்க ஒரு SMS குறியீட்டை அனுப்புவோம்.',
    phone: 'மொபைல் எண்',
    phoneHint: '10 இலக்க இந்திய மொபைல் எண்ணை உள்ளிடவும்',
    send: 'குறியீட்டை அனுப்பவும்',
    sentTo: 'குறியீடு அனுப்பப்பட்டது',
    code: 'சரிபார்ப்பு குறியீடு',
    codeHint: '6 இலக்க குறியீட்டை உள்ளிடவும்',
    verify: 'தொலைபேசியைச் சரிபார்க்கவும்',
    resend: 'குறியீட்டை மீண்டும் அனுப்பவும்',
    wait: 'மீண்டும் அனுப்ப',
    seconds: 'விநாடிகள்',
    change: 'வேறு எண்ணைப் பயன்படுத்தவும்',
    verified: 'தொலைபேசி சரிபார்க்கப்பட்டது. இப்போது படிவத்தைப் பதிவேற்றலாம்.',
    genericError: 'சரிபார்ப்பு முடியவில்லை. மீண்டும் முயற்சிக்கவும்.',
    sending: 'அனுப்புகிறது…',
    checking: 'சரிபார்க்கிறது…',
  },
};

function getLanguage(language) {
  const base = (language || 'en').split('-')[0];
  return TEXTS[base] ? base : 'en';
}

function getErrorMessage(error, fallback) {
  return error?.response?.data?.detail?.message || error?.message || fallback;
}

export function PhoneVerify({ sessionId, language = 'en', onVerified, onError, onSkip }) {
  const lang = getLanguage(language);
  const t = useMemo(() => TEXTS[lang], [lang]);
  const { speak = () => {} } = useSpeech(lang);
  const [phone, setPhone] = useState('');
  const [code, setCode] = useState('');
  const [request, setRequest] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [resendIn, setResendIn] = useState(0);
  const verified = request?.verified === true;

  useEffect(() => {
    if (resendIn <= 0) return undefined;
    const timer = window.setInterval(() => setResendIn((value) => Math.max(0, value - 1)), 1000);
    return () => window.clearInterval(timer);
  }, [resendIn]);

function getSpokenPhoneMessage(lang, maskedPhone) {
  const digits = (maskedPhone || '').replace(/\D/g, '');
  const last4 = digits.slice(-4);
  const spaced = last4 ? last4.split('').join(' ') : '';
  if (lang === 'hi') {
    return last4
      ? `सत्यापन कोड आपके मोबाइल नंबर पर भेजा गया है, जिसके अंत में ${spaced} है।`
      : 'सत्यापन कोड आपके मोबाइल नंबर पर भेज दिया गया है।';
  }
  if (lang === 'ta') {
    return last4
      ? `${spaced} என்ற எண்ணில் முடியும் உங்கள் மொபைலுக்கு சரிபார்ப்பு குறியீடு அனுப்பப்பட்டது.`
      : 'உங்கள் மொபைல் எண்ணிற்கு சரிபார்ப்பு குறியீடு அனுப்பப்பட்டது.';
  }
  return last4
    ? `Verification code sent to your number ending in ${spaced}.`
    : 'Verification code sent to your mobile number.';
}

  const handleSend = async (event) => {
    event?.preventDefault();
    if (!phone.trim() || busy) return;
    setBusy(true);
    setError('');
    try {
      const result = await sendOtp(sessionId, phone.trim(), language);
      setRequest(result);
      if (result.dev_code) {
        setCode(result.dev_code);
      } else {
        setCode('');
      }
      setResendIn(result.resend_after_seconds || 30);
      speak(getSpokenPhoneMessage(lang, result.masked_phone || phone));
    } catch (requestError) {
      const message = getErrorMessage(requestError, t.genericError);
      setError(message);
      onError?.(requestError);
    } finally {
      setBusy(false);
    }
  };

  const handleVerify = async (event) => {
    event?.preventDefault();
    if (!request?.otp_id || code.length !== (request.code_length || 6) || busy) return;
    setBusy(true);
    setError('');
    try {
      const result = await verifyOtp(sessionId, request.otp_id, code);
      setRequest({ ...request, ...result, verified: true });
      speak(t.verified);
      onVerified?.(result);
    } catch (requestError) {
      const message = getErrorMessage(requestError, t.genericError);
      setError(message);
      onError?.(requestError);
    } finally {
      setBusy(false);
    }
  };

  if (verified) {
    return (
      <section className="glass-card otp-verification-panel otp-card" style={{ maxWidth: 560, margin: '0 auto', padding: 28, textAlign: 'center' }}>
        <CheckCircle2 size={46} color="#16a34a" aria-hidden="true" />
        <h2 className="otp-title" style={{ margin: '12px 0 6px', color: '#0f172a', fontSize: 22 }}>{t.verified}</h2>
      </section>
    );
  }

  return (
    <section className="glass-card otp-verification-panel otp-card" style={{ maxWidth: 560, margin: '0 auto', padding: 28 }}>
      <div style={{ display: 'flex', gap: 12, alignItems: 'flex-start', marginBottom: 20 }}>
        <ShieldCheck size={34} color="#2563eb" aria-hidden="true" />
        <div>
          <h2 className="otp-title" style={{ margin: 0, color: '#0f172a', fontSize: 23 }}>{t.title}</h2>
          <p className="otp-subtitle" style={{ margin: '6px 0 0', color: '#334155', lineHeight: 1.5 }}>{t.subtitle}</p>
        </div>
      </div>

      {!request ? (
        <form onSubmit={handleSend}>
          <label className="otp-label" htmlFor="otp-phone" style={{ display: 'block', color: '#0f172a', fontWeight: 700, marginBottom: 6 }}>{t.phone}</label>
          <input
            id="otp-phone"
            type="tel"
            inputMode="numeric"
            autoComplete="tel"
            value={phone}
            onChange={(event) => setPhone(event.target.value.replace(/[^0-9+ -]/g, '').slice(0, 16))}
            placeholder={t.phoneHint}
            className="otp-input"
            style={{ width: '100%', padding: '12px 14px', borderRadius: 12, border: '1px solid #94a3b8', color: '#0f172a', fontSize: 16, boxSizing: 'border-box' }}
          />
          <button type="submit" className="btn btn-primary otp-primary-button" disabled={busy || !phone.trim()} style={{ marginTop: 14, width: '100%' }}>
            <MessageSquare size={17} /> {busy ? t.sending : t.send}
          </button>
          {onSkip && (
            <div style={{ marginTop: 16, textAlign: 'center' }}>
              <button
                type="button"
                className="btn btn-ghost btn-sm"
                onClick={onSkip}
                style={{ color: '#64748b', fontSize: 13, textDecoration: 'underline', cursor: 'pointer' }}
              >
                Skip verification & proceed to form
              </button>
            </div>
          )}
        </form>
      ) : (
        <form onSubmit={handleVerify}>
          <p className="otp-destination" style={{ margin: '0 0 14px', color: '#0f172a', fontWeight: 700 }}>{t.sentTo} {request.masked_phone}</p>
          {request.dev_code && (
            <div
              style={{
                marginBottom: 16,
                padding: '10px 14px',
                background: '#f0fdf4',
                border: '1px solid #86efac',
                borderRadius: 10,
                fontSize: 14,
                color: '#15803d',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
              }}
            >
              <span>
                💡 <strong>Demo Code:</strong> {request.dev_code}
              </span>
              <button
                type="button"
                className="btn btn-ghost btn-sm"
                style={{ color: '#16a34a', fontWeight: 700, padding: '4px 8px' }}
                onClick={() => setCode(request.dev_code)}
              >
                Fill {request.dev_code}
              </button>
            </div>
          )}
          <label className="otp-label" htmlFor="otp-code" style={{ display: 'block', color: '#0f172a', fontWeight: 700, marginBottom: 6 }}>{t.code}</label>
          <input
            id="otp-code"
            type="text"
            inputMode="numeric"
            pattern={`[0-9]{${request.code_length || 6}}`}
            autoComplete="one-time-code"
            maxLength={request.code_length || 6}
            value={code}
            onChange={(event) => setCode(event.target.value.replace(/\D/g, '').slice(0, request.code_length || 6))}
            placeholder={t.codeHint}
            className="otp-input otp-code-input"
            style={{ width: '100%', padding: '12px 14px', borderRadius: 12, border: '1px solid #94a3b8', color: '#0f172a', fontSize: 22, letterSpacing: 6, textAlign: 'center', boxSizing: 'border-box' }}
          />
          <button type="submit" className="btn btn-primary otp-primary-button" disabled={busy || code.length !== (request.code_length || 6)} style={{ marginTop: 14, width: '100%' }}>
            <ShieldCheck size={17} /> {busy ? t.checking : t.verify}
          </button>
          <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, marginTop: 14, alignItems: 'center' }}>
            <button type="button" className="btn btn-ghost btn-sm otp-secondary-button" onClick={() => { setRequest(null); setError(''); setCode(''); }}>
              {t.change}
            </button>
            <button type="button" className="btn btn-ghost btn-sm otp-secondary-button" disabled={busy || resendIn > 0} onClick={handleSend}>
              <RefreshCw size={15} /> {resendIn > 0 ? `${t.wait} ${resendIn}${t.seconds}` : t.resend}
            </button>
          </div>
          {onSkip && (
            <div style={{ marginTop: 16, textAlign: 'center' }}>
              <button
                type="button"
                className="btn btn-ghost btn-sm"
                onClick={onSkip}
                style={{ color: '#64748b', fontSize: 13, textDecoration: 'underline', cursor: 'pointer' }}
              >
                Skip verification & proceed to form
              </button>
            </div>
          )}
        </form>
      )}

      {error && (
        <div style={{ marginTop: 14 }}>
          <p className="otp-error" role="alert" aria-live="polite" style={{ margin: '0 0 10px', color: '#b91c1c', fontWeight: 700 }}>{error}</p>
          {onSkip && (
            <button
              type="button"
              className="btn btn-secondary btn-sm"
              onClick={onSkip}
              style={{ width: '100%', padding: '10px 14px', borderRadius: 10, fontSize: 14 }}
            >
              Continue to Form Upload →
            </button>
          )}
        </div>
      )}
    </section>
  );
}
