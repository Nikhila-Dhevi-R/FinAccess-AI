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
  const sizeMap = { large: 128, medium: 88, small: 64 };
  const px = sizeMap[size] || 96;
  const baseLang = (language || 'en').split('-')[0];
  const l = LABELS[baseLang] || LABELS.en;

  const displayLabel = label || (isSpeaking ? l.speaking : isListening ? l.listening : error ? 'Tap to retry' : l.idle);

  return (
    <div className={`voice-btn-wrapper voice-btn-wrapper-${size}${isListening ? ' is-listening' : ''}${isSpeaking ? ' is-speaking' : ''}`} style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', margin: '14px 0' }}>
      <div className="voice-btn-outer" style={{ position: 'relative' }}>
        {isListening && (
          <>
            <div className="pulse-ring" />
            <div className="pulse-ring" />
          </>
        )}
        <button
          type="button"
          className={`voice-btn${isListening ? ' recording' : ''}${isSpeaking ? ' speaking' : ''}${error ? ' has-error' : ''}`}
          style={{
            width: px,
            height: px,
            borderRadius: '50%',
            cursor: disabled ? 'not-allowed' : 'pointer',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            border: '4px solid #ffffff',
            background: isListening ? 'linear-gradient(145deg, #dc2626, #991b1b)' : error ? 'linear-gradient(145deg, #d97706, #b45309)' : 'var(--gradient-primary)',
            color: '#ffffff',
            boxShadow: isListening ? '0 12px 32px rgba(185, 28, 28, 0.36)' : error ? '0 12px 32px rgba(180, 83, 9, 0.28)' : '0 12px 30px rgba(30, 58, 138, 0.28)',
            transition: 'all 0.25s ease',
          }}
          onClick={onClick}
          disabled={disabled}
          aria-label={displayLabel}
          aria-pressed={isListening}
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
