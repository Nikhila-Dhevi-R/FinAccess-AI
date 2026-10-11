import { Mic, MicOff, Volume2, AlertCircle } from 'lucide-react';

const LABELS = {
  en: {
    speaking: 'Speaking…',
    listening: 'Listening… Tap to finish',
    idle: 'Tap to Speak',
  },
  hi: {
    speaking: 'बोल रहा हूँ…',
    listening: 'सुन रहा हूँ… रोकने के लिए दबाएं',
    idle: 'बोलने के लिए दबाएं',
  },
  ta: {
    speaking: 'பேசுகிறது…',
    listening: 'கேட்கிறது… நிறுத்த அழுத்தவும்',
    idle: 'பேச அழுத்தவும்',
  },
};

export function AudioWaveform({ active }) {
  if (!active) return null;
  return (
    <div className="waveform">
      {[...Array(7)].map((_, i) => (
        <div key={i} className="waveform-bar" style={{ animationDelay: `${i * 0.08}s` }} />
      ))}
    </div>
  );
}

export function VoiceButton({
  isListening,
  isSpeaking,
  onClick,
  disabled,
  size = 'large',
  language = 'en',
  label,
  error,
}) {
  const sizeMap = { large: 96, medium: 68, small: 52 };
  const px = sizeMap[size] || 96;
  const baseLang = (language || 'en').split('-')[0];
  const l = LABELS[baseLang] || LABELS.en;

  const displayLabel = label || (isSpeaking ? l.speaking : isListening ? l.listening : error ? 'Tap to retry' : l.idle);

  return (
    <div className="voice-btn-wrapper" style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', margin: '14px 0' }}>
      <div className="voice-btn-outer" style={{ position: 'relative' }}>
        {isListening && (
          <>
            <div className="pulse-ring" />
            <div className="pulse-ring" />
          </>
        )}
        <button
          type="button"
          className={`voice-btn${isListening ? ' recording' : ''}`}
          style={{
            width: px,
            height: px,
            borderRadius: '50%',
            cursor: disabled ? 'not-allowed' : 'pointer',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            border: isListening ? '4px solid #ef4444' : error ? '3px solid #f59e0b' : '3px solid var(--color-teal, #0d9488)',
            background: isListening ? '#fee2e2' : error ? '#fef3c7' : 'var(--color-bg-primary, #ffffff)',
            color: isListening ? '#b91c1c' : error ? '#b45309' : 'var(--color-teal, #0d9488)',
            boxShadow: isListening ? '0 0 24px rgba(239, 68, 68, 0.4)' : '0 8px 24px rgba(0, 0, 0, 0.12)',
            transition: 'all 0.25s ease',
          }}
          onClick={onClick}
          disabled={disabled}
          aria-label={displayLabel}
          title={error || displayLabel}
        >
          {isSpeaking ? (
            <Volume2 size={px * 0.45} />
          ) : isListening ? (
            <MicOff size={px * 0.45} />
          ) : (
            <Mic size={px * 0.45} />
          )}
        </button>
      </div>

      <span
        className="voice-btn-label"
        style={{
          marginTop: 10,
          fontSize: size === 'small' ? 13 : 15,
          fontWeight: 700,
          color: isListening ? '#b91c1c' : 'var(--color-text-primary, #1e293b)',
          textAlign: 'center',
        }}
      >
        {displayLabel}
      </span>

      {isListening && <AudioWaveform active={isListening} />}

      {error && !isListening && (
        <div
          style={{
            marginTop: 8,
            padding: '6px 12px',
            background: '#fef2f2',
            border: '1px solid #fecaca',
            borderRadius: 8,
            color: '#b91c1c',
            fontSize: 12,
            fontWeight: 600,
            maxWidth: 340,
            textAlign: 'center',
            display: 'flex',
            alignItems: 'center',
            gap: 6,
          }}
        >
          <AlertCircle size={14} style={{ flexShrink: 0 }} />
          <span>{error}</span>
        </div>
      )}
    </div>
  );
}
