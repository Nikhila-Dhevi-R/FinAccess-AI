/**
 * ChallengePrompt — Replay-Resistant Nonce Voice Verification Component
 * Prompts user to speak or input randomized 4 digits with visual countdown and real-time validation.
 */

import { useState, useEffect, useCallback } from 'react';
import { ShieldCheck, RefreshCw, Volume2, Clock, AlertTriangle } from 'lucide-react';
import { respondToChallenge } from '../api/client';
import { VoiceButton } from './VoiceButton';
import { useSpeech } from '../hooks/useSpeech';

const EXPIRY_SECONDS = 30;

const TEXTS = {
  en: {
    label: 'Voice Security Confirmation',
    sub: 'To prevent replay fraud and confirm it is really you, please say or enter the 4 numbers below:',
    remaining: 's left',
    confirmed: 'Voice confirmed successfully!',
    mismatch: 'Numbers did not match. Please try with new numbers:',
    expired: 'Security challenge expired. Generating new digits...',
    tryAgain: 'Generate New Challenge',
    checking: 'Verifying with secure anti-replay protocol...',
    youSaid: 'You entered / spoke:',
    repeatBtn: 'Repeat Numbers',
    typeOrTap: 'Or enter 4 digits manually:',
  },
  hi: {
    label: 'वॉइस सुरक्षा पुष्टि',
    sub: 'सुरक्षा के लिए और धोखाधड़ी रोकने के लिए, कृपया नीचे दिए गए 4 अंक बोलें या दर्ज करें:',
    remaining: ' सेकंड शेष',
    confirmed: 'सफलतापूर्वक पुष्टि हो गई!',
    mismatch: 'अंक मेल नहीं खाए। कृपया नए अंकों के साथ दोबारा बोलें:',
    expired: 'समय समाप्त हो गया। नए अंक तैयार किए जा रहे हैं...',
    tryAgain: 'नया चैलेंज बनाएं',
    checking: 'सुरक्षित प्रोटोकॉल द्वारा जांच की जा रही है...',
    youSaid: 'आपने कहा/दर्ज किया:',
    repeatBtn: 'अंक दोबारा सुनें',
    typeOrTap: 'या सीधे 4 अंक दर्ज करें:',
  },
  ta: {
    label: 'குரல் பாதுகாப்பு உறுதிப்படுத்தல்',
    sub: 'பாதுகாப்பிற்காக, தயவுசெய்து கீழே உள்ள 4 எண்களை சொல்லுங்கள் அல்லது உள்ளிடவும்:',
    remaining: ' நொடிகள் மீதம்',
    confirmed: 'வெற்றிகரமாக உறுதிப்படுத்தப்பட்டது!',
    mismatch: 'எண்கள் பொருந்தவில்லை. புதிய எண்களுடன் மீண்டும் முயற்சிக்கவும்:',
    expired: 'நேரம் முடிந்தது. புதிய எண்கள் உருவாக்கப்படுகின்றன...',
    tryAgain: 'மீண்டும் முயற்சிக்கவும்',
    checking: 'சரிபார்க்கப்படுகிறது...',
    youSaid: 'நீங்கள் கூறியது:',
    repeatBtn: 'எண்களை மீண்டும் கேட்க',
    typeOrTap: 'அல்லது 4 எண்களை உள்ளிடவும்:',
  },
};

export function ChallengePrompt({ nonce, sessionId, language = 'en', onSuccess, onFailure }) {
  const [timeLeft, setTimeLeft] = useState(EXPIRY_SECONDS);
  const [status, setStatus] = useState('idle'); // idle | listening | validating | success | failed | expired
  const [spokenText, setSpokenText] = useState('');
  const [message, setMessage] = useState('');
  const [newNonce, setNewNonce] = useState(null);
  const [manualInput, setManualInput] = useState('');

  const baseLang = (language || 'en').split('-')[0];
  const lang = baseLang === 'hi' || baseLang === 'ta' ? baseLang : 'en';
  const t = TEXTS[lang] || TEXTS.en;

  const { speak, stopSpeaking, listen, stopListening, isListening, isSpeaking, transcript, error: speechError } = useSpeech(lang);
  const activeNonce = newNonce || nonce;

  // Countdown timer
  useEffect(() => {
    setTimeLeft(EXPIRY_SECONDS);
    const interval = setInterval(() => {
      setTimeLeft((prev) => {
        if (prev <= 1) {
          clearInterval(interval);
          if (status === 'idle') setStatus('expired');
          return 0;
        }
        return prev - 1;
      });
    }, 1000);
    return () => clearInterval(interval);
  }, [activeNonce?.nonce_id, status]);

  // Auto-speak challenge when nonce changes
  useEffect(() => {
    if (activeNonce && status === 'idle') {
      const audioToSpeak = activeNonce.challenge_audio_text || `To confirm, please say: ${activeNonce.challenge_digits}`;
      speak(audioToSpeak);
    }
  }, [activeNonce?.nonce_id]);

  const submitValidation = useCallback(async (inputText) => {
    if (!inputText || !inputText.trim() || !activeNonce) return;
    setStatus('validating');
    setMessage('');
    try {
      const result = await respondToChallenge(activeNonce.nonce_id, sessionId, inputText.trim());
      if (result.success && result.action_committed) {
        setStatus('success');
        speak(t.confirmed);
        onSuccess?.(result);
      } else {
        setStatus('failed');
        setMessage(result.message);
        if (result.new_nonce) {
          setNewNonce(result.new_nonce);
          setTimeLeft(EXPIRY_SECONDS);
          speak(`${t.mismatch} ${result.new_nonce.challenge_digits}`);
        } else {
          speak(`${t.mismatch} ${activeNonce.challenge_digits}`);
        }
        onFailure?.(result);
      }
    } catch (e) {
      setStatus('failed');
      setMessage(e.message || 'Error occurred during validation.');
    }
  }, [activeNonce, sessionId, speak, onSuccess, onFailure, t]);

  const handleListen = useCallback(async () => {
    stopSpeaking();
    setStatus('listening');
    setMessage('');
    try {
      const text = await listen();
      setSpokenText(text);
      if (!text || !text.trim()) {
        setStatus('idle');
        return;
      }
      await submitValidation(text);
    } catch (e) {
      setStatus('failed');
      setMessage(e.message || 'Error occurred');
    }
  }, [listen, stopSpeaking, submitValidation]);

  const handleManualSubmit = (e) => {
    e?.preventDefault();
    if (manualInput.trim()) {
      setSpokenText(manualInput.trim());
      submitValidation(manualInput.trim());
    }
  };

  const timerPct = (timeLeft / EXPIRY_SECONDS) * 100;

  if (status === 'success') {
    return (
      <div
        className="challenge-panel"
        style={{
          borderColor: '#22c55e',
          background: '#f0fdf4',
          textAlign: 'center',
          padding: 28,
          borderRadius: 16,
        }}
      >
        <ShieldCheck size={48} color="#22c55e" style={{ margin: '0 auto 12px' }} />
        <h3 style={{ color: '#15803d', fontSize: 20, fontWeight: 800, margin: 0 }}>
          {t.confirmed}
        </h3>
      </div>
    );
  }

  return (
    <div
      className="challenge-panel"
      style={{
        padding: '24px 20px',
        border: '2px solid #3b82f6',
        borderRadius: 16,
        background: '#ffffff',
        textAlign: 'center',
        maxWidth: 480,
        margin: '0 auto',
      }}
    >
      <div style={{ fontSize: 13, fontWeight: 800, color: '#2563eb', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
        {t.label}
      </div>
      <p style={{ fontSize: 15, color: '#334155', margin: '8px 0 14px', fontWeight: 600 }}>
        {t.sub}
      </p>

      {/* Big Digits Display */}
      <div
        className="challenge-phrase"
        style={{
          fontSize: 44,
          fontWeight: 900,
          color: '#1d4ed8',
          letterSpacing: '14px',
          background: '#eff6ff',
          padding: '10px 20px',
          borderRadius: 14,
          display: 'inline-block',
          margin: '0 auto 10px',
          border: '2px dashed #93c5fd',
        }}
      >
        {activeNonce?.challenge_digits}
      </div>

      <div style={{ fontSize: 14, color: '#64748b', marginBottom: 12, fontWeight: 600 }}>
        {activeNonce?.challenge_phrase}
      </div>

      {/* Timer Bar */}
      <div style={{ height: 8, background: '#e2e8f0', borderRadius: 4, overflow: 'hidden', margin: '10px 0' }}>
        <div
          style={{
            height: '100%',
            width: `${timerPct}%`,
            background: timeLeft < 10 ? '#ef4444' : '#3b82f6',
            transition: 'width 1s linear',
          }}
        />
      </div>
      <div style={{ fontSize: 13, color: '#64748b', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6 }}>
        <Clock size={14} />
        <span>
          {timeLeft}
          {t.remaining}
        </span>
      </div>

      {/* Live / Spoken text */}
      {(transcript || spokenText) && (
        <div
          style={{
            marginTop: 12,
            padding: '8px 14px',
            background: '#f1f5f9',
            borderRadius: 8,
            fontSize: 14,
            color: '#1e293b',
          }}
        >
          {t.youSaid} <strong>{transcript || spokenText}</strong>
        </div>
      )}

      {message && (
        <div style={{ marginTop: 10, color: '#dc2626', fontSize: 13, fontWeight: 600, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6 }}>
          <AlertTriangle size={15} />
          <span>{message}</span>
        </div>
      )}

      {/* Controls */}
      <div style={{ marginTop: 14 }}>
        {status === 'validating' ? (
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, justifyContent: 'center', color: '#2563eb', fontWeight: 600, padding: 12 }}>
            <div className="loader" style={{ width: 22, height: 22, borderWidth: 3 }} />
            {t.checking}
          </div>
        ) : status !== 'expired' ? (
          <div>
            <VoiceButton
              isListening={isListening}
              isSpeaking={isSpeaking}
              onClick={isListening ? stopListening : handleListen}
              language={lang}
              size="medium"
              error={speechError}
            />

            <div style={{ marginTop: 8, display: 'flex', gap: 10, justifyContent: 'center' }}>
              <button
                type="button"
                className="btn btn-ghost btn-sm"
                style={{ fontSize: 13 }}
                onClick={() => speak(activeNonce?.challenge_audio_text || activeNonce?.challenge_digits)}
              >
                <Volume2 size={14} /> {t.repeatBtn}
              </button>
            </div>

            {/* Manual Digits Fallback */}
            <form onSubmit={handleManualSubmit} style={{ marginTop: 14, paddingTop: 12, borderTop: '1px solid #e2e8f0' }}>
              <div style={{ fontSize: 12, color: '#64748b', marginBottom: 6, fontWeight: 600 }}>
                {t.typeOrTap}
              </div>
              <div style={{ display: 'flex', gap: 8, maxWidth: 220, margin: '0 auto' }}>
                <input
                  type="text"
                  maxLength={4}
                  inputMode="numeric"
                  pattern="[0-9]{4}"
                  placeholder="4 digits"
                  value={manualInput}
                  onChange={(e) => setManualInput(e.target.value.replace(/\D/g, '').slice(0, 4))}
                  style={{
                    flex: 1,
                    textAlign: 'center',
                    fontSize: 16,
                    fontWeight: 700,
                    letterSpacing: 4,
                    padding: '6px 10px',
                    borderRadius: 8,
                    border: '1.5px solid #cbd5e1',
                  }}
                />
                <button
                  type="submit"
                  className="btn btn-primary btn-sm"
                  disabled={!manualInput.trim()}
                  style={{ borderRadius: 8, padding: '0 14px' }}
                >
                  OK
                </button>
              </div>
            </form>
          </div>
        ) : (
          <button
            type="button"
            className="btn btn-amber"
            style={{ padding: '10px 20px', borderRadius: 20 }}
            onClick={() => {
              setStatus('idle');
              setTimeLeft(EXPIRY_SECONDS);
            }}
          >
            <RefreshCw size={16} /> {t.tryAgain}
          </button>
        )}
      </div>
    </div>
  );
}
