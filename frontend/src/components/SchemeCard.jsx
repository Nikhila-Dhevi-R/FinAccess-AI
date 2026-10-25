import { CheckCircle, AlertCircle, ExternalLink, ChevronDown, ChevronUp, Volume2 } from 'lucide-react';
import { useState } from 'react';

const LOCALIZED_LABELS = {
  en: {
    match: 'Match',
    needsInfo: 'Needs Information',
    listen: 'Listen',
    speaking: 'Speaking…',
    howToApply: 'How to Apply',
    hideSteps: 'Hide Steps',
    applyNow: 'Apply Now',
    missingNotice: 'Additional requirement:',
  },
  hi: {
    match: 'पात्र (Match)',
    needsInfo: 'अतिरिक्त जानकारी आवश्यक',
    listen: 'सुनें',
    speaking: 'बोल रहा हूँ…',
    howToApply: 'आवेदन के चरण देखें',
    hideSteps: 'चरण छिपाएं',
    applyNow: 'आवेदन करें',
    missingNotice: 'आवश्यक शर्तें:',
  },
  ta: {
    match: 'பொருத்தம் (Match)',
    needsInfo: 'கூடுதல் விவரம் தேவை',
    listen: 'கேளுங்கள்',
    speaking: 'பேசுகிறது…',
    howToApply: 'விண்ணப்பிக்கும் முறை',
    hideSteps: 'மறைக்கவும்',
    applyNow: 'விண்ணப்பிக்கவும்',
    missingNotice: 'தேவையான நிபந்தனை:',
  },
};

export function SchemeCard({ scheme, onApply, onSpeak, isSpeakingThis, language = 'en' }) {
  const [expanded, setExpanded] = useState(false);
  const scorePct = Math.round((scheme.match_score || 0.75) * 100);
  const isNeedsInfo = scheme.status === 'needs_more_info';
  const l = LOCALIZED_LABELS[language] || LOCALIZED_LABELS.en;

  const audioText = `${scheme.name}. ${scheme.benefit_summary}. ${
    isNeedsInfo ? scheme.eligibility_reason : 'You are eligible. '
  } ${
    scheme.application_steps?.length
      ? 'How to apply: ' + scheme.application_steps.join('. ')
      : ''
  }`;

  return (
    <div
      className={`glass-card scheme-card${isNeedsInfo ? ' needs-info' : ''}`}
      style={{
        border: isNeedsInfo ? '1.5px dashed #f59e0b' : '1.5px solid var(--color-border)',
        padding: '24px',
        borderRadius: '16px',
        marginBottom: '20px',
        background: isNeedsInfo ? '#fffbeb' : '#ffffff',
      }}
    >
      <div className="scheme-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '16px' }}>
        <div style={{ flex: 1 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6, flexWrap: 'wrap' }}>
            {scheme.short_name && (
              <span className={`badge ${isNeedsInfo ? 'badge-amber' : 'badge-primary'}`} style={{ fontWeight: 700 }}>
                {scheme.short_name}
              </span>
            )}
            <span
              style={{
                fontSize: 13,
                fontWeight: 700,
                color: isNeedsInfo ? '#d97706' : 'var(--color-primary)',
              }}
            >
              {isNeedsInfo ? `ℹ ${l.needsInfo}` : `✓ ${scorePct}% ${l.match}`}
            </span>
          </div>
          <h3 className="scheme-name" style={{ fontSize: 20, fontWeight: 700, margin: '4px 0 6px', color: '#1e293b' }}>
            {scheme.name}
          </h3>
          {scheme.ministry && (
            <div className="scheme-ministry" style={{ fontSize: 13, color: '#64748b', marginBottom: 10 }}>
              {scheme.ministry}
            </div>
          )}
        </div>

        {/* Listen Button */}
        {onSpeak && (
          <button
            type="button"
            className="btn btn-ghost"
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 6,
              background: isSpeakingThis ? '#dbeafe' : '#f1f5f9',
              color: isSpeakingThis ? '#1d4ed8' : '#334155',
              padding: '10px 16px',
              borderRadius: '24px',
              fontWeight: 700,
              fontSize: 14,
              border: 'none',
              cursor: 'pointer',
              flexShrink: 0,
            }}
            onClick={() => onSpeak(audioText)}
            aria-label={`Listen to ${scheme.name}`}
          >
            <Volume2 size={18} />
            <span>{isSpeakingThis ? l.speaking : l.listen}</span>
          </button>
        )}
      </div>

      <div
        className="scheme-benefit"
        style={{
          fontSize: 16,
          lineHeight: 1.5,
          color: '#334155',
          margin: '12px 0',
          fontWeight: 500,
          background: '#f8fafc',
          padding: '14px',
          borderRadius: '10px',
        }}
      >
        💰 {scheme.benefit_summary}
      </div>

      <div
        className="scheme-eligibility"
        style={{
          display: 'flex',
          alignItems: 'flex-start',
          gap: 10,
          fontSize: 14,
          color: isNeedsInfo ? '#92400e' : '#166534',
          background: isNeedsInfo ? '#fef3c7' : '#f0fdf4',
          padding: '10px 14px',
          borderRadius: '10px',
          marginBottom: 16,
        }}
      >
        {isNeedsInfo ? (
          <AlertCircle size={18} style={{ flexShrink: 0, marginTop: 2, color: '#d97706' }} />
        ) : (
          <CheckCircle size={18} style={{ flexShrink: 0, marginTop: 2, color: '#16a34a' }} />
        )}
        <span>{scheme.eligibility_reason}</span>
      </div>

      {expanded && scheme.application_steps?.length > 0 && (
        <div style={{ marginBottom: 16, animation: 'fade-in 0.3s ease', background: '#f8fafc', padding: 16, borderRadius: 12 }}>
          <div
            style={{
              fontSize: 14,
              fontWeight: 700,
              color: '#334155',
              marginBottom: 10,
            }}
          >
            📋 {l.howToApply}:
          </div>
          <ol style={{ paddingLeft: 20, margin: 0, fontSize: 14, lineHeight: 1.6, color: '#475569' }}>
            {scheme.application_steps.map((step, i) => (
              <li key={i} style={{ marginBottom: 6 }}>
                {step}
              </li>
            ))}
          </ol>
        </div>
      )}

      <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', marginTop: 12 }}>
        <button
          type="button"
          className="btn btn-ghost"
          style={{ fontSize: 14, padding: '10px 18px', fontWeight: 600 }}
          onClick={() => setExpanded((e) => !e)}
        >
          {expanded ? (
            <>
              <ChevronUp size={16} /> {l.hideSteps}
            </>
          ) : (
            <>
              <ChevronDown size={16} /> {l.howToApply}
            </>
          )}
        </button>
        {onApply && (
          <button
            type="button"
            className="btn btn-primary"
            style={{ fontSize: 14, padding: '10px 22px', fontWeight: 700 }}
            onClick={() => onApply(scheme)}
          >
            <ExternalLink size={16} /> {l.applyNow}
          </button>
        )}
      </div>
    </div>
  );
}
