import { useRef, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Shield, ShieldAlert, ShieldCheck, AlertTriangle,
  PhoneCall, ExternalLink, Volume2, Sparkles, Mic, ScanText,
} from 'lucide-react';
import { PhotoMessageCheck } from '../components/PhotoMessageCheck';
import { VoiceButton } from '../components/VoiceButton';
import { useSpeech } from '../hooks/useSpeech';
import { useSession } from '../hooks/useSession';
import { checkFraud } from '../api/client';
import { playListenChime, playSuccessChime, playRetryChime } from '../utils/audioCue';

// ─── Sample preset messages ───────────────────────────────────────────────────
const DEMO_MESSAGES = [
  {
    title: '🚨 Fake SBI KYC Scam',
    text: 'Dear SBI user, your KYC is expired. Your account will be blocked within 24 hours. Click http://bit.ly/sbi-kyc-update to verify now or share OTP with agent.',
  },
  {
    title: '⚠️ Fake Lottery / Prize',
    text: 'Congratulations! You have won Rs 50,000 lottery in lucky draw. Immediately call +919876543210 to claim your reward before it expires.',
  },
  {
    title: '⚠️ Remote Access Trap',
    text: 'Bank Alert: Technical glitch detected in your mobile banking. Install TeamViewer QuickSupport immediately to avoid deduction.',
  },
  {
    title: '✅ Legitimate Bank SMS',
    text: 'Your transaction of Rs. 450 at ATM was successful. Available balance in A/C XX1234 is Rs. 14,210. ATMSBI.',
  },
];

// ─── Labels by language ───────────────────────────────────────────────────────
const T = {
  en: {
    badge: 'AI Scam & Fraud Shield',
    title: 'Check Suspicious Messages',
    subtitle: 'Received a SMS, WhatsApp message, or call? Paste it or read it aloud. We check for fake KYC, phishing links, lottery scams, and OTP fraud.',
    sampleLabel: 'Test with sample messages:',
    label: 'Message Content to Verify:',
    placeholder: 'Paste SMS, WhatsApp message, or email here... (or tap Speak to dictate)',
    speak: 'Tap & Speak the Message',
    listening: 'Listening...',
    analyze: 'Analyze Safety',
    analyzing: 'Analyzing...',
    clear: 'Clear',
    result: { fraud: 'Dangerous Scam / Fraud', suspicious: 'Suspicious Warning', safe: 'No Obvious Scam Signs' },
    fraudLikelihood: 'Fraud Likelihood',
    redFlags: 'Detected Red Flags:',
    action: 'Recommended Action:',
    replay: 'Play Voice Warning',
    replaying: 'Playing...',
    helpline: 'National Cyber Crime Helpline:',
    report: 'Report on CyberCrime Portal',
    reviewTitle: 'Please check the text we read from your photo',
    reviewBody: 'Reading text from a photo can make mistakes. Compare it with the message on your phone and correct anything that is wrong. The result is based on this text.',
    staleNote: 'You changed the text. Tap "Analyze Safety" to update the result before relying on it.',
  },
  hi: {
    badge: 'AI धोखाधड़ी सुरक्षा',
    title: 'संदिग्ध संदेश जाँचें',
    subtitle: 'कोई SMS, WhatsApp संदेश या कॉल आया? यहाँ पेस्ट करें या बोलकर बताएं। हम नकली KYC, फ़िशिंग, लॉटरी घोटाले और OTP धोखाधड़ी की जाँच करते हैं।',
    sampleLabel: 'नमूना संदेशों से जाँचें:',
    label: 'जाँचने के लिए संदेश:',
    placeholder: 'SMS, WhatsApp संदेश या ईमेल यहाँ पेस्ट करें... (या बोलकर बताएं)',
    speak: 'बोलकर संदेश बताएं',
    listening: 'सुन रहा हूँ...',
    analyze: 'सुरक्षा जाँच करें',
    analyzing: 'जाँच हो रही है...',
    clear: 'साफ करें',
    result: { fraud: 'खतरनाक धोखाधड़ी', suspicious: 'संदिग्ध चेतावनी', safe: 'कोई स्पष्ट धोखाधड़ी संकेत नहीं' },
    fraudLikelihood: 'धोखाधड़ी की संभावना',
    redFlags: 'पहचाने गए खतरे:',
    action: 'अनुशंसित कार्रवाई:',
    replay: 'आवाज़ चेतावनी सुनें',
    replaying: 'बोल रहा हूँ...',
    helpline: 'राष्ट्रीय साइबर अपराध हेल्पलाइन:',
    report: 'CyberCrime पोर्टल पर रिपोर्ट करें',
    reviewTitle: 'कृपया फोटो से पढ़ा गया टेक्स्ट जाँचें',
    reviewBody: 'फोटो से टेक्स्ट पढ़ने में गलतियाँ हो सकती हैं। इसे अपने फोन के संदेश से मिलाएं और जो गलत हो उसे ठीक करें। परिणाम इसी टेक्स्ट पर आधारित है।',
    staleNote: 'आपने टेक्स्ट बदला है। परिणाम पर भरोसा करने से पहले "सुरक्षा जाँच करें" दबाकर परिणाम अपडेट करें।',
  },
  ta: {
    badge: 'AI மோசடி பாதுகாப்பு',
    title: 'சந்தேகமான செய்திகளை சரிபார்க்கவும்',
    subtitle: 'SMS, WhatsApp செய்தி அல்லது அழைப்பு வந்ததா? இங்கே ஒட்டுங்கள் அல்லது பேசி சொல்லுங்கள். நகலி KYC, ஃபிஷிங், லாட்டரி மோசடிகளை சரிபார்க்கிறோம்.',
    sampleLabel: 'மாதிரி செய்திகளை சோதிக்கவும்:',
    label: 'சரிபார்க்க செய்தி:',
    placeholder: 'SMS, WhatsApp செய்தியை இங்கே ஒட்டுங்கள்... (அல்லது பேசுங்கள்)',
    speak: 'பேசி செய்தி சொல்லுங்கள்',
    listening: 'கேட்கிறேன்...',
    analyze: 'பாதுகாப்பை சரிபார்க்கவும்',
    analyzing: 'சரிபார்க்கிறேன்...',
    clear: 'அழிக்கவும்',
    result: { fraud: 'ஆபத்தான மோசடி', suspicious: 'சந்தேக எச்சரிக்கை', safe: 'மோசடி அறிகுறிகள் தென்படவில்லை' },
    fraudLikelihood: 'மோசடி வாய்ப்பு',
    redFlags: 'கண்டறியப்பட்ட ஆபத்துகள்:',
    action: 'பரிந்துரைக்கப்பட்ட நடவடிக்கை:',
    replay: 'குரல் எச்சரிக்கை கேளுங்கள்',
    replaying: 'பேசுகிறேன்...',
    helpline: 'தேசிய சைபர் குற்ற உதவி எண்:',
    report: 'CyberCrime போர்டலில் புகார் செய்யுங்கள்',
    reviewTitle: 'புகைப்படத்திலிருந்து படித்த உரையைச் சரிபார்க்கவும்',
    reviewBody: 'புகைப்படத்திலிருந்து உரையைப் படிக்கும்போது பிழைகள் வரலாம். உங்கள் தொலைபேசியில் உள்ள செய்தியுடன் ஒப்பிட்டு, தவறுகளைத் திருத்தவும். முடிவு இந்த உரையை அடிப்படையாகக் கொண்டது.',
    staleNote: 'நீங்கள் உரையை மாற்றியுள்ளீர்கள். முடிவை நம்புவதற்கு முன் "பாதுகாப்பை சரிபார்க்கவும்" அழுத்தி முடிவைப் புதுப்பிக்கவும்.',
  },
};

export default function FraudCheck() {
  const { sessionId, language } = useSession();
  const { speak, listen, stopListening, isListening, isSpeaking, error: speechError } = useSpeech(language);

  const [messageText, setMessageText] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [analyzedText, setAnalyzedText] = useState('');   // the text the current result was computed from
  const [fromPhoto, setFromPhoto] = useState(false);       // text was read from a photo and needs review
  const textareaRef = useRef(null);

  const t = T[language] || T.en;
  const resultIsStale = Boolean(result) && messageText.trim() !== analyzedText.trim();

  const handleAnalyze = async (customText) => {
    const textToAnalyze = (customText !== undefined ? customText : messageText).trim();
    if (!textToAnalyze) return;

    if (customText !== undefined) {
      setMessageText(customText);
    }

    setLoading(true);
    setResult(null);
    setAnalyzedText(textToAnalyze);

    try {
      const data = await checkFraud(sessionId || 'guest-session', textToAnalyze, language);
      setResult(data);
      if (data.classification === 'fraud') {
        playRetryChime();
      } else if (data.classification === 'safe') {
        playSuccessChime();
      }
      if (data.explanation_audio_text) {
        speak(data.explanation_audio_text);
      }
    } catch (err) {
      console.warn('Fraud check API error — local fallback:', err);
      const lower = textToAnalyze.toLowerCase();
      const hasOtp = lower.includes('otp') || lower.includes('pin');
      const hasBlock = lower.includes('block') || lower.includes('suspend') || lower.includes('kyc');
      const hasLink = lower.includes('http') || lower.includes('bit.ly') || lower.includes('click');
      const hasLottery = lower.includes('won') || lower.includes('prize') || lower.includes('lottery') || lower.includes('congratulations');

      let classification = 'suspicious';
      let riskLevel = 'medium';
      let confidence = 0.35;
      let indicators = ['The full fraud checker is unavailable, so this message could not be verified'];

      if ((hasOtp && hasBlock) || (hasBlock && hasLink)) {
        classification = 'fraud';
        riskLevel = 'critical';
        confidence = 0.96;
        if (hasOtp) indicators.push('Asks for OTP / PIN — Banks never ask for this');
        if (hasBlock) indicators.push('Threatens account suspension or block');
        if (hasLink) indicators.push('Contains suspicious external link');
      } else if (hasBlock || hasLink || hasLottery) {
        classification = 'suspicious';
        riskLevel = 'medium';
        confidence = 0.67;
        if (hasLottery) indicators.push('Prize or lottery claim — common fraud tactic');
        if (hasLink) indicators.push('Suspicious link detected');
        if (hasBlock) indicators.push('Urgent / threatening language');
      }

      const fraudText =
        language === 'hi'
          ? 'चेतावनी! यह संदेश धोखाधड़ी के लक्षण दिखाता है। किसी भी लिंक पर क्लिक न करें और न ही जानकारी साझा करें।'
          : language === 'ta'
          ? 'எச்சரிக்கை! இந்த செய்தியில் மோசடியின் அறிகுறிகள் உள்ளன. எந்த இணைப்பிலும் கிளிக் செய்யாதீர்கள்.'
          : 'Warning! This message shows signs of fraud. Do not reply or click any links.';

      const safeText =
        language === 'hi'
          ? 'कोई स्पष्ट धोखाधड़ी संकेत नहीं मिला, लेकिन भेजने वाले की पुष्टि नहीं हुई। आधिकारिक नंबर या ऐप से जाँचें।'
          : language === 'ta'
          ? 'மோசடி அறிகுறிகள் தெரியவில்லை; ஆனால் அனுப்புநர் சரிபார்க்கப்படவில்லை. அதிகாரப்பூர்வ எண் அல்லது செயலியில் சரிபார்க்கவும்.'
          : 'No known scam indicators were detected. This does not verify the sender or links. Never share your OTP or PIN with anyone.';

      const suspiciousText =
        language === 'hi'
          ? 'इस संदेश की पुष्टि नहीं हो सकी। कोई जवाब देने या भुगतान करने से पहले अपने बैंक से आधिकारिक नंबर पर संपर्क करें।'
          : language === 'ta'
          ? 'இந்த செய்தியை சரிபார்க்க முடியவில்லை. பதிலளிப்பதற்கு அல்லது பணம் செலுத்துவதற்கு முன் அதிகாரப்பூர்வ எண்ணில் வங்கியைத் தொடர்புகொள்ளுங்கள்.'
          : 'This message could not be verified. Check with the organization using its official number before replying or paying.';
      const explanation = classification === 'fraud' ? fraudText : classification === 'suspicious' ? suspiciousText : safeText;

      const fallbackResult = {
        classification,
        risk_level: riskLevel,
        confidence,
        explanation,
        explanation_audio_text: explanation,
        fraud_indicators: indicators,
        advice:
          language === 'hi'
            ? 'कभी भी OTP या पासवर्ड साझा न करें। धोखाधड़ी की शिकायत के लिए 1930 पर कॉल करें।'
            : language === 'ta'
            ? 'ஒருபோதும் OTP அல்லது கடவுச்சொல்லை பகிர்ந்துகொள்ளாதீர்கள். 1930 என்ற எண்ணில் அழைக்கவும்.'
            : 'Never share your OTP or password. If scammed, call National Cyber Crime Helpline at 1930.',
      };

      setResult(fallbackResult);
      if (classification === 'fraud') playRetryChime();
      else if (classification === 'safe') playSuccessChime();
      speak(fallbackResult.explanation_audio_text);
    } finally {
      setLoading(false);
    }
  };

  // Text read from a photo: show it for review alongside the result it produced
  const handlePhotoResult = (data) => {
    setMessageText(data.extracted_text || '');
    setAnalyzedText(data.extracted_text || '');
    setFromPhoto(true);
    setResult(data);
    if (data.classification === 'fraud') playRetryChime();
    else if (data.classification === 'safe') playSuccessChime();
    if (data.explanation_audio_text) speak(data.explanation_audio_text);
    setTimeout(() => textareaRef.current?.scrollIntoView({ behavior: 'smooth', block: 'center' }), 100);
  };

  const focusTyping = () => {
    textareaRef.current?.focus();
    textareaRef.current?.scrollIntoView({ behavior: 'smooth', block: 'center' });
  };

  const handleVoiceInput = async () => {
    try {
      playListenChime();
      const heard = await listen();
      if (heard && heard.trim()) {
        setMessageText(heard.trim());
        handleAnalyze(heard.trim());
      }
    } catch (e) {
      console.warn('Speech error:', e);
    }
  };

  return (
    <div className="container" style={{ padding: 'var(--space-6) 0 var(--space-8)' }}>
      {/* Header */}
      <div className="page-header" style={{ textAlign: 'center', maxWidth: 700, margin: '0 auto var(--space-6)' }}>
        <div className="badge badge-amber" style={{ marginBottom: 'var(--space-2)' }}>
          <Shield size={13} style={{ marginRight: 6 }} /> {t.badge}
        </div>
        <h1 className="page-title">{t.title}</h1>
        <p className="page-subtitle">{t.subtitle}</p>
      </div>

      {/* Big voice CTA for low-literacy users */}
      <div style={{ textAlign: 'center', marginBottom: 'var(--space-5)' }}>
        <button
          onClick={handleVoiceInput}
          disabled={isListening || loading}
          style={{
            background: isListening ? 'var(--color-red)' : '#d97706',
            color: '#fff',
            border: 'none',
            borderRadius: 'var(--radius-full)',
            padding: '18px 40px',
            fontSize: 17,
            fontWeight: 700,
            cursor: isListening ? 'not-allowed' : 'pointer',
            display: 'inline-flex',
            alignItems: 'center',
            gap: 12,
            boxShadow: '0 6px 24px rgba(0,0,0,0.25)',
            transition: 'all 0.2s',
            animation: isListening ? 'pulse 1s infinite' : 'none',
          }}
        >
          <Mic size={22} />
          {isListening ? t.listening : t.speak}
        </button>
        <p style={{ fontSize: 13, color: 'var(--color-text-secondary)', marginTop: 8 }}>
          {language === 'hi' ? 'या नीचे संदेश पेस्ट करें' : language === 'ta' ? 'அல்லது கீழே செய்தியை ஒட்டுங்கள்' : 'or paste a message below'}
        </p>
      </div>

      <div style={{ maxWidth: 840, margin: '0 auto' }}>
        {/* Photo of a message the customer chooses to show */}
        <PhotoMessageCheck
          language={language}
          sessionId={sessionId}
          disabled={loading || isListening}
          onResult={handlePhotoResult}
          onTypeInstead={focusTyping}
        />

        {/* Sample Presets */}
        <div style={{ marginBottom: 'var(--space-5)' }}>
          <p style={{ fontSize: 13, color: 'var(--color-text-secondary)', marginBottom: 8, display: 'flex', alignItems: 'center', gap: 6 }}>
            <Sparkles size={14} color="var(--color-amber)" /> {t.sampleLabel}
          </p>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(190px, 1fr))', gap: 10 }}>
            {DEMO_MESSAGES.map((demo, idx) => (
              <button
                key={idx}
                onClick={() => handleAnalyze(demo.text)}
                className="btn btn-secondary fraud-sample-button"
                style={{
                  textAlign: 'left',
                  padding: '10px 14px',
                  borderRadius: 'var(--radius-md)',
                  fontSize: 12.5,
                  display: 'flex',
                  flexDirection: 'column',
                  gap: 4,
                  cursor: 'pointer',
                  border: '1px solid var(--color-border)',
                }}
              >
                <strong style={{ color: 'var(--color-text-primary)' }}>{demo.title}</strong>
                <span style={{ fontSize: 11, color: 'var(--color-text-secondary)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  {demo.text}
                </span>
              </button>
            ))}
          </div>
        </div>

        {/* Textarea Input */}
        <div
          className="glass-card"
          style={{
            padding: 'var(--space-5)',
            borderRadius: 'var(--radius-xl)',
            border: '1px solid var(--color-border)',
            marginBottom: 'var(--space-6)',
          }}
        >
          {fromPhoto && (
            <div
              role="note"
              style={{
                display: 'flex',
                gap: 10,
                padding: '12px 14px',
                marginBottom: 12,
                background: 'var(--color-amber-dim)',
                border: '1.5px solid var(--color-amber-border)',
                borderRadius: 'var(--radius-md)',
                color: 'var(--color-text-primary)',
              }}
            >
              <ScanText size={20} color="var(--color-amber)" style={{ flexShrink: 0, marginTop: 2 }} />
              <div>
                <strong style={{ display: 'block', fontSize: 15, marginBottom: 2 }}>{t.reviewTitle}</strong>
                <span style={{ fontSize: 14, lineHeight: 1.5 }}>{t.reviewBody}</span>
              </div>
            </div>
          )}
          <label htmlFor="fraud-message-text" style={{ display: 'block', fontSize: 14, fontWeight: 600, marginBottom: 8, color: 'var(--color-text-primary)' }}>
            {t.label}
          </label>
          <textarea
            id="fraud-message-text"
            ref={textareaRef}
            className="input-field"
            rows={fromPhoto ? 6 : 4}
            value={messageText}
            onChange={(e) => setMessageText(e.target.value)}
            placeholder={t.placeholder}
            style={{
              width: '100%',
              padding: 'var(--space-4)',
              background: 'var(--color-bg-subtle)',
              border: '1.5px solid var(--color-border)',
              borderRadius: 'var(--radius-md)',
              color: 'var(--color-text-primary)',
              fontSize: 14.5,
              resize: 'vertical',
              marginBottom: 'var(--space-4)',
            }}
          />

          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 12 }}>
            <VoiceButton
              isListening={isListening}
              isSpeaking={isSpeaking}
              onClick={isListening ? stopListening : handleVoiceInput}
              language={language}
              size="small"
              error={speechError}
              label={isListening ? t.listening : t.speak}
            />

            <div style={{ display: 'flex', gap: 10 }}>
              {messageText && (
                <button
                  className="btn btn-secondary"
                  onClick={() => { setMessageText(''); setResult(null); setAnalyzedText(''); setFromPhoto(false); }}
                >
                  {t.clear}
                </button>
              )}
              <button
                className="btn btn-primary"
                onClick={() => handleAnalyze()}
                disabled={!messageText.trim() || loading}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 8,
                  padding: '12px 24px',
                  borderRadius: 'var(--radius-full)',
                  background: '#d97706',
                }}
              >
                {loading ? (
                  <>
                    <div className="loader" style={{ width: 16, height: 16 }} />
                    <span>{t.analyzing}</span>
                  </>
                ) : (
                  <>
                    <Shield size={16} />
                    <span>{t.analyze}</span>
                  </>
                )}
              </button>
            </div>
          </div>
        </div>

        {resultIsStale && (
          <div
            role="status"
            style={{
              padding: '12px 16px',
              marginBottom: 12,
              background: 'var(--color-amber-dim)',
              border: '1.5px solid var(--color-amber-border)',
              borderRadius: 'var(--radius-md)',
              fontSize: 15,
              fontWeight: 600,
              color: 'var(--color-amber)',
            }}
          >
            ⚠ {t.staleNote}
          </div>
        )}

        {/* Results */}
        <AnimatePresence>
          {result && (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              className={`fraud-result ${result.classification}`}
              style={{
                borderRadius: 'var(--radius-xl)',
                padding: 'var(--space-6)',
                border: '1px solid var(--color-border)',
                opacity: resultIsStale ? 0.45 : 1,
                transition: 'opacity 0.2s',
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: 16, marginBottom: 16 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                  {result.classification === 'fraud' && <ShieldAlert size={40} color="var(--color-red)" />}
                  {result.classification === 'suspicious' && <AlertTriangle size={40} color="var(--color-amber)" />}
                  {result.classification === 'safe' && <ShieldCheck size={40} color="var(--color-green)" />}
                  <div>
                    <h2 style={{ fontSize: 22, fontWeight: 800, textTransform: 'uppercase', margin: 0, letterSpacing: '0.03em' }}>
                      {t.result[result.classification] || result.classification}
                    </h2>
                    {result.scam_type && (
                      <div style={{ fontSize: 16, fontWeight: 700, margin: '2px 0 4px' }}>{result.scam_type}</div>
                    )}
                    <span style={{ fontSize: 13, opacity: 0.8 }}>
                      Risk: <strong>{result.risk_level?.toUpperCase()}</strong> • Confidence: <strong>{Math.round((result.confidence || 0.8) * 100)}%</strong>
                    </span>
                  </div>
                </div>

                <button
                  onClick={() => speak(result.explanation_audio_text || result.explanation)}
                  className="btn btn-secondary btn-sm"
                  style={{ display: 'flex', alignItems: 'center', gap: 6, borderRadius: 'var(--radius-full)' }}
                >
                  <Volume2 size={15} />
                  <span>{isSpeaking ? t.replaying : t.replay}</span>
                </button>
              </div>

              {/* Confidence meter */}
              <div style={{ marginBottom: 20 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, marginBottom: 4 }}>
                  <span>{t.fraudLikelihood}</span>
                  <span>{Math.round((result.confidence || 0.8) * 100)}%</span>
                </div>
                <div style={{ height: 10, background: 'var(--color-border)', borderRadius: 5, overflow: 'hidden' }}>
                  <motion.div
                    initial={{ width: 0 }}
                    animate={{ width: `${Math.round((result.confidence || 0.8) * 100)}%` }}
                    transition={{ duration: 0.6, ease: 'easeOut' }}
                    style={{
                      height: '100%',
                      background: result.classification === 'fraud'
                        ? 'var(--color-red)'
                        : result.classification === 'suspicious'
                        ? 'var(--color-amber)'
                        : 'var(--color-green)',
                    }}
                  />
                </div>
              </div>

              {/* Explanation */}
              <p style={{ fontSize: 15, lineHeight: 1.65, marginBottom: 16 }}>{result.explanation}</p>

              {/* Red flags */}
              {result.fraud_indicators && result.fraud_indicators.length > 0 && (
                <div style={{ marginBottom: 20 }}>
                  <h4 className="fraud-indicators-title" style={{ fontSize: 13, fontWeight: 700, textTransform: 'uppercase', marginBottom: 8 }}>{t.redFlags}</h4>
                  <div className="fraud-indicators">
                    {result.fraud_indicators.map((ind, i) => (
                      <div key={i} className="fraud-indicator">
                        <AlertTriangle size={15} color="var(--color-red)" style={{ marginTop: 2, flexShrink: 0 }} />
                        <span>{ind}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Advice */}
              <div
                className="fraud-advice"
                style={{
                  padding: 'var(--space-4)',
                  borderRadius: 'var(--radius-md)',
                  marginBottom: 20,
                }}
              >
                <h4 className="fraud-advice-title" style={{ fontSize: 13, fontWeight: 700, marginBottom: 4 }}>{t.action}</h4>
                <p className="fraud-advice-copy" style={{ margin: 0, fontSize: 14 }}>{result.advice}</p>
              </div>

              {/* Emergency contacts */}
              <div
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  flexWrap: 'wrap',
                  gap: 12,
                  paddingTop: 16,
                  borderTop: '1px solid var(--color-border)',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 13 }}>
                  <PhoneCall size={16} color="var(--color-amber)" />
                  <span>
                    {t.helpline} <strong style={{ color: 'var(--color-amber)', fontSize: 16 }}>1930</strong> (Toll Free)
                  </span>
                </div>
                <a
                  href="https://cybercrime.gov.in"
                  target="_blank"
                  rel="noreferrer"
                  className="btn btn-sm btn-secondary"
                  style={{ display: 'flex', alignItems: 'center', gap: 5, borderRadius: 'var(--radius-full)' }}
                >
                  <span>{t.report}</span>
                  <ExternalLink size={12} />
                </a>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}
