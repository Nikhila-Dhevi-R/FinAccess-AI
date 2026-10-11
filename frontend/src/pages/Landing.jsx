import { useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { ArrowRight, Volume2, Mic, Play, RotateCcw, ShieldCheck, HelpCircle, FileText, Landmark } from 'lucide-react';
import { useSession } from '../hooks/useSession';
import { useSpeech } from '../hooks/useSpeech';
import { playListenChime, playSuccessChime } from '../utils/audioCue';

const LANGUAGES = [
  { code: 'en', label: 'English', native: 'English', num: '1', audio: 'You selected English.' },
  { code: 'hi', label: 'Hindi', native: 'हिन्दी', num: '2', audio: 'आपने हिन्दी चुनी है।' },
  { code: 'ta', label: 'Tamil', native: 'தமிழ்', num: '3', audio: 'நீங்கள் தமிழை தேர்ந்தெடுத்துள்ளீர்கள்.' },
];

const TRANSLATIONS = {
  en: {
    startVoiceBtn: 'START VOICE ASSISTANT',
    startVoiceSub: 'Tap here to begin spoken assistance (No typing required)',
    welcome: 'Welcome to FinAccess AI. Please choose your language. Say 1 for English.',
    menuAudio: 'Main Menu. Say 1 to Fill a Form, 2 for Government Schemes, 3 to Ask a Banking Question, or 4 for Fraud Check.',
    listeningForLang: 'Listening for language choice (Say 1 English, 2 Hindi, 3 Tamil)…',
    listeningForMenu: 'Listening for menu option (Say 1, 2, 3, or 4)…',
    formFill: {
      num: '1',
      title: 'Form Fill',
      badge: 'Step 1',
      desc: 'Speak to fill any bank, pension, ration card or government form. We extract fields and ask questions by voice.',
      audio: 'Button 1: Form Fill. Upload your form and speak your answers. We will fill and prepare your form for you.',
    },
    govtScheme: {
      num: '2',
      title: 'Govt Schemes',
      badge: 'Step 2',
      desc: 'Find government welfare money, subsidies, and schemes you and your family are eligible to receive.',
      audio: 'Button 2: Government Schemes. Answer 3 simple questions by voice to find schemes you can receive.',
    },
    guidance: {
      num: '3',
      title: 'Ask Banking Question',
      badge: 'Help',
      desc: 'Ask any questions about bank accounts, ATM, loans, or pensions in your language.',
      audio: 'Button 3: Ask a Banking Question. Ask any banking or financial question anytime.',
    },
    fraudCheck: {
      num: '4',
      title: 'Fraud & SMS Check',
      badge: 'Safety',
      desc: 'Got a message or call asking for OTP or money? Check if it is safe or a scam.',
      audio: 'Button 4: Fraud Check. Check if an SMS message is fake or trying to steal your money.',
    },
    listenBtn: 'Listen',
    tapToSpeak: 'Tap to Speak',
    voicePromptTitle: 'Voice Navigation Active',
    subtitle: 'Voice-First Financial Inclusion Platform for India — Speak, Understand, Complete. No reading or typing needed.',
    speakingLangs: 'Speaking language choices…',
    speakingMenu: 'Speaking menu options…',
    heard: 'Heard',
    listeningNow: 'Listening… Speak now',
    speakingNow: 'Speaking…',
  },
  hi: {
    startVoiceBtn: 'आवाज़ सहायक शुरू करें',
    startVoiceSub: 'बोलकर काम शुरू करने के लिए यहाँ दबाएं (लिखने की आवश्यकता नहीं)',
    welcome: 'फिनएक्सेस एआई में आपका स्वागत है। कृपया अपनी भाषा चुनें। अंग्रेज़ी के लिए 1, हिन्दी के लिए 2, या तमिल के लिए 3 बोलें।',
    menuAudio: 'मुख्य मेनू। फॉर्म भरने के लिए 1, सरकारी योजनाओं के लिए 2, बैंकिंग सवाल के लिए 3, या धोखाधड़ी जांच के लिए 4 बोलें।',
    listeningForLang: 'भाषा का चुनाव सुन रहे हैं (अंग्रेज़ी 1, हिन्दी 2, तमिल 3 बोलें)…',
    listeningForMenu: 'मेनू विकल्प सुन रहे हैं (1, 2, 3 या 4 बोलें)…',
    formFill: {
      num: '१',
      title: 'बोलकर फॉर्म भरें',
      badge: 'चरण 1',
      desc: 'बोलकर बैंक, पेंशन या सरकारी फॉर्म भरें। हम फॉर्म से सवाल पढ़कर आपसे पूछेंगे।',
      audio: 'बटन 1: बोलकर फॉर्म भरें। अपना फॉर्म अपलोड करें और बोलकर जवाब दें।',
    },
    govtScheme: {
      num: '२',
      title: 'सरकारी योजनाएं खोजें',
      badge: 'चरण 2',
      desc: 'पीएम किसान, पेंशन, आवास और आपके लिए उपलब्ध सरकारी योजनाओं और पैसों की जानकारी पाएं।',
      audio: 'बटन 2: सरकारी योजनाएं। 3 सरल सवालों के जवाब दें और अपनी योजनाएं जानें।',
    },
    guidance: {
      num: '३',
      title: 'बैंकिंग सवाल पूछें',
      badge: 'मार्गदर्शन',
      desc: 'बैंक खाता, लोन, एटीएम या पेंशन के बारे में कोई भी सवाल अपनी भाषा में पूछें।',
      audio: 'बटन 3: बैंकिंग सवाल पूछें। बैंक, लोन या पेंशन के बारे में कोई भी सवाल पूछें।',
    },
    fraudCheck: {
      num: '४',
      title: 'धोखाधड़ी जांच',
      badge: 'सुरक्षा',
      desc: 'ओटीपी या पैसे मांगने वाला कोई मैसेज आया? तुरंत पता करें कि यह असली है या धोखा।',
      audio: 'बटन 4: धोखाधड़ी जांच। किसी भी संदिग्ध मैसेज की जांच करें।',
    },
    listenBtn: 'सुनें',
    tapToSpeak: 'बोलें',
    voicePromptTitle: 'वॉइस सहायक चालू है',
    subtitle: 'भारत के लिए आवाज़ से चलने वाला वित्तीय सहायक — बोलें, समझें, काम पूरा करें। पढ़ने या लिखने की ज़रूरत नहीं।',
    speakingLangs: 'भाषा के विकल्प बताए जा रहे हैं…',
    speakingMenu: 'मेनू के विकल्प बताए जा रहे हैं…',
    heard: 'सुना गया',
    listeningNow: 'सुन रहे हैं… अब बोलें',
    speakingNow: 'बोल रहे हैं…',
  },
  ta: {
    startVoiceBtn: 'குரல் உதவியாளரைத் தொடங்கு',
    startVoiceSub: 'பேசிப் பயன்படுத்த இங்கே அழுத்தவும் (எழுதத் தேவையில்லை)',
    welcome: 'ஃபின்ஆக்சஸ் ஏஐக்கு நல்வரவு. மொழியைத் தேர்வுசெய்யுங்கள். ஆங்கிலத்திற்கு 1, இந்திக்கு 2, தமிழுக்கு 3 சொல்லுங்கள்.',
    menuAudio: 'முதன்மை பட்டியல். படிவம் நிரப்ப 1, அரசு திட்டங்களை பார்க்க 2, வங்கி கேள்வி கேட்க 3, மோசடி சரிபார்க்க 4 சொல்லுங்கள்.',
    listeningForLang: 'மொழிக்காக கேட்கிறது (ஆங்கிலம் 1, இந்தி 2, தமிழ் 3 சொல்லுங்கள்)…',
    listeningForMenu: 'பட்டியல் தேர்வு கேட்கிறது (1, 2, 3 அல்லது 4 சொல்லுங்கள்)…',
    formFill: {
      num: '1',
      title: 'படிவம் நிரப்புதல்',
      badge: 'படி 1',
      desc: 'பேசியே வங்கி அல்லது அரசு படிவங்களை நிரப்பலாம். நாங்கள் கேள்விகளை குரல் வடிவில் கேட்போம்.',
      audio: 'பொத்தான் 1: படிவம் நிரப்புதல். படிவத்தை பதிவேற்றி பேசி பதிலளிக்கவும்.',
    },
    govtScheme: {
      num: '2',
      title: 'அரசு நலத்திட்டங்கள்',
      badge: 'படி 2',
      desc: 'உங்களுக்கு கிடைக்கக்கூடிய அரசு நிதி உதவிகள் மற்றும் நலத்திட்டங்களை கண்டறியுங்கள்.',
      audio: 'பொத்தான் 2: அரசு திட்டங்கள். 3 எளிய கேள்விகளுக்கு பதிலளித்து தகுதியான திட்டங்களை அறியலாம்.',
    },
    guidance: {
      num: '3',
      title: 'வங்கி கேள்வி கேட்க',
      badge: 'வழிகாட்டி',
      desc: 'வங்கி கணக்கு, கடன், ஏடிஎம் அல்லது ஓய்வூதியம் பற்றிய கேள்விகளை உங்கள் மொழியில் கேளுங்கள்.',
      audio: 'பொத்தான் 3: வங்கி கேள்வி கேட்க. சந்தேகங்களை எப்போது வேண்டுமானாலும் கேட்கலாம்.',
    },
    fraudCheck: {
      num: '4',
      title: 'மோசடி சரிபார்ப்பு',
      badge: 'பாதுகாப்பு',
      desc: 'ஓடிபி அல்லது பணம் கேட்கும் குறுஞ்செய்தி பாதுகாப்பானதா என அறிய இங்கே கிளிக் செய்யவும்.',
      audio: 'பொத்தான் 4: மோசடி சரிபார்ப்பு. போலி குறுஞ்செய்திகளை கண்டறியவும்.',
    },
    listenBtn: 'கேட்க',
    tapToSpeak: 'பேச',
    voicePromptTitle: 'குரல் வழிகாட்டுதல் இயக்கத்தில் உள்ளது',
    subtitle: 'இந்தியாவுக்கான குரல் வழி நிதி உதவியாளர் — பேசுங்கள், புரிந்துகொள்ளுங்கள், முடியுங்கள். படிக்கவோ எழுதவோ தேவையில்லை.',
    speakingLangs: 'மொழி தேர்வுகள் சொல்லப்படுகின்றன…',
    speakingMenu: 'பட்டியல் தேர்வுகள் சொல்லப்படுகின்றன…',
    heard: 'கேட்டது',
    listeningNow: 'கேட்கிறது… இப்போது பேசுங்கள்',
    speakingNow: 'பேசுகிறது…',
  },
};

// Speech recognition returns slightly different spellings for short number
// commands (for example, "moondru" can be transcribed as "moonru"). Keep
// command matching token based so one command cannot match another as a
// substring ("moondru" contains "ondru", Tamil for one).
const VOICE_NUMBER_ALIASES = {
  1: ['1', 'one', 'won', 'wan', 'ek', 'ondru', 'onru', 'onnu', '\u090f\u0915', '\u0b92\u0ba9\u0bcd\u0bb1\u0bc1'],
  2: ['2', 'two', 'too', 'tu', 'tuu', 'do', 'doh', 'tho', 'dho', 'du', 'irandu', 'erandu', 'rendu', '\u0926\u094b', '\u0b87\u0bb0\u0ba3\u0bcd\u0b9f\u0bc1'],
  3: ['3', 'three', 'teen', 'moondru', 'moonu', 'moonru', 'mundru', 'moondroo', '\u0924\u0940\u0928', '\u0bae\u0942\u0ba9\u0bcd\u0bb1\u0bc1'],
  4: ['4', 'four', 'char', 'chaar', 'naangu', 'nangu', '\u091a\u093e\u0930', '\u0ba8\u0bbe\u0b99\u0bcd\u0b95\u0bc1'],
};

const LANGUAGE_ALIASES = {
  en: ['1', 'one', 'english', 'ek', 'ondru', 'onru', '\u090f\u0915', '\u0b92\u0ba9\u0bcd\u0bb1\u0bc1'],
  hi: ['2', 'two', 'too', 'to', 'tu', 'tuu', 'hindi', 'do', 'doh', 'tho', 'dho', 'du', 'irandu', 'erandu', 'rendu', '\u0926\u094b', '\u0b87\u0bb0\u0ba3\u0bcd\u0b9f\u0bc1'],
  ta: ['3', 'three', 'tamil', 'teen', 'moondru', 'moonu', 'moonru', 'mundru', 'moondroo', '\u0924\u0940\u0928', '\u0bae\u0942\u0ba9\u0bcd\u0bb1\u0bc1'],
};

const MENU_ROUTES = {
  1: { path: '/form-fill', keywords: ['form', 'fill', 'application', 'bank form', 'first', '\u092b\u0949\u0930\u094d\u092e', '\u0baa\u0b9f\u0bbf\u0bb5\u0bae\u0bcd'] },
  2: { path: '/schemes', keywords: ['scheme', 'schemes', 'government', 'yojana', 'thittam', 'second', '\u092f\u094b\u091c\u0928\u093e', '\u0ba4\u0bbf\u0b9f\u0bcd\u0b9f\u0bae\u0bcd'] },
  3: { path: '/guidance', keywords: ['question', 'questions', 'bank', 'guidance', 'help', 'third', '\u0938\u0935\u093e\u0932', '\u0b95\u0bc7\u0bb3\u0bcd\u0bb5\u0bbf'] },
  4: { path: '/fraud-check', keywords: ['fraud', 'scam', 'safety', 'fourth', '\u0927\u094b\u0916\u093e', '\u0bae\u0bcb\u0b9a\u0b9f\u0bbf'] },
};

const normalizeVoiceCommand = (value) => String(value || '')
  .normalize('NFKD')
  .toLowerCase()
  .replace(/[^\p{L}\p{M}\p{N}]+/gu, ' ')
  .trim();

const containsVoicePhrase = (normalizedText, phrases) => {
  const paddedText = ` ${normalizedText} `;
  return phrases.some((phrase) => {
    const normalizedPhrase = normalizeVoiceCommand(phrase);
    return normalizedPhrase && paddedText.includes(` ${normalizedPhrase} `);
  });
};

const detectVoiceNumber = (value) => {
  const normalizedText = normalizeVoiceCommand(value);
  if (!normalizedText) return null;

  for (const [number, aliases] of Object.entries(VOICE_NUMBER_ALIASES)) {
    if (containsVoicePhrase(normalizedText, aliases)) return number;
  }
  return null;
};

const detectLanguageChoice = (value) => {
  const normalizedText = normalizeVoiceCommand(value);
  if (!normalizedText) return null;

  // Match the full token/phrase, never a substring. This keeps "moondru"
  // from being interpreted as "ondru" (English option 1).
  for (const language of ['ta', 'hi', 'en']) {
    if (containsVoicePhrase(normalizedText, LANGUAGE_ALIASES[language])) return language;
  }
  return null;
};

const detectMenuPath = (value) => {
  const normalizedText = normalizeVoiceCommand(value);
  if (!normalizedText) return null;

  const spokenNumber = detectVoiceNumber(normalizedText);
  if (spokenNumber && MENU_ROUTES[spokenNumber]) return MENU_ROUTES[spokenNumber].path;

  for (const route of Object.values(MENU_ROUTES)) {
    if (containsVoicePhrase(normalizedText, route.keywords)) return route.path;
  }
  return null;
};

export default function Landing() {
  const { sessionId, language, changeLanguage, startSession } = useSession();
  const [voiceOnboardingState, setVoiceOnboardingState] = useState('idle'); // idle | picking-lang | picking-menu
  const [voiceFeedback, setVoiceFeedback] = useState('');
  const navigate = useNavigate();

  const currentLang = language === 'hi' || language === 'ta' ? language : 'en';
  const t = TRANSLATIONS[currentLang] || TRANSLATIONS.en;

  const { speak, speakParts, listen, isListening, isSpeaking, stopSpeaking, transcript } = useSpeech(currentLang);

  const handleStartCard = async (path) => {
    try {
      if (!sessionId) {
        await startSession(currentLang);
      }
      navigate(path);
    } catch {
      navigate(path);
    }
  };

  const handleReadAloud = (e, text) => {
    e.stopPropagation();
    if (isSpeaking) {
      stopSpeaking();
    } else {
      speak(text);
    }
  };

  // Spec-Compliant Voice Onboarding Workflow
  const startFullVoiceFlow = useCallback(async () => {
    setVoiceOnboardingState('picking-lang');
    setVoiceFeedback(t.speakingLangs);

    // 1. Speak the welcome and the full language choices. Each language is read by its own voice — an
    //    English voice skips Hindi/Tamil script, which made it say only "1 for English … 2 … 3".
    //    The English sentence names all three languages, so nothing is lost if a Hindi/Tamil voice is missing.
    const introParts = [
      { text: TRANSLATIONS.en.welcome, lang: 'en' },
      { text: 'हिन्दी के लिए 2 बोलें।', lang: 'hi', optional: true },
      { text: 'தமிழுக்கு 3 சொல்லுங்கள்.', lang: 'ta', optional: true },
    ];

    speakParts(introParts, async () => {
      // 2. Play turn-taking chime & listen
      playListenChime();
      setVoiceFeedback(t.listeningForLang);

      try {
        const spoken = await listen();
        const chosen = detectLanguageChoice(spoken);

        const selected = chosen || currentLang;
        changeLanguage(selected);
        playSuccessChime();

        const activeT = TRANSLATIONS[selected] || TRANSLATIONS.en;
        const chosenItem = LANGUAGES.find((l) => l.code === selected);
        setVoiceOnboardingState('picking-menu');
        setVoiceFeedback(activeT.speakingMenu);

        // 3. Confirm the language and speak the 4-choice menu — in the chosen language and voice
        speak(`${chosenItem?.audio || ''} ${activeT.menuAudio}`, async () => {
          playListenChime();
          setVoiceFeedback(activeT.listeningForMenu);

          try {
            const menuSpoken = await listen(selected);
            const menuPath = detectMenuPath(menuSpoken);

            if (menuPath) {
              playSuccessChime();
              handleStartCard(menuPath);
            } else {
              setVoiceOnboardingState('idle');
              setVoiceFeedback('');
            }
          } catch {
            setVoiceOnboardingState('idle');
          }
        }, selected);
      } catch {
        setVoiceOnboardingState('idle');
      }
    });
  }, [changeLanguage, currentLang, handleStartCard, listen, speak, speakParts, t]);

  return (
    <div className="sketch-container" style={{ maxWidth: 900, margin: '0 auto', padding: '16px 16px 60px' }}>
      {/* Header section */}
      <header className="sketch-header" style={{ textAlign: 'center', marginBottom: 28 }}>
        <motion.h1
          className="sketch-title"
          initial={{ opacity: 0, y: 15 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4 }}
          style={{ fontSize: 40, fontWeight: 900, letterSpacing: '-0.02em', color: '#0f172a', margin: '0 0 8px' }}
        >
          FinAccess <span style={{ color: 'var(--color-primary, #0284c7)' }}>AI</span>
        </motion.h1>

        <motion.p
          className="sketch-subtitle"
          initial={{ opacity: 0, y: 15 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1, duration: 0.4 }}
          style={{ fontSize: 18, color: '#475569', maxWidth: 640, margin: '0 auto 20px', lineHeight: 1.4 }}
        >
          {t.subtitle}
        </motion.p>

        {/* ── BIG VOICE ONBOARDING START BUTTON ── */}
        <div className="voice-launch-shell">
          <motion.button
            type="button"
            className={`voice-launch-button${isSpeaking || isListening ? ' active' : ''}`}
            whileHover={{ scale: 1.03 }}
            whileTap={{ scale: 0.97 }}
            onClick={startFullVoiceFlow}
            aria-pressed={isListening}
            aria-busy={isSpeaking || isListening}
          >
            <span className="voice-launch-icon" aria-hidden="true">
              <Mic size={30} strokeWidth={2.5} />
            </span>
            <span className="voice-launch-copy">
              <span className="voice-launch-title">{t.startVoiceBtn}</span>
              <span className="voice-launch-subtitle">{t.startVoiceSub}</span>
            </span>
          </motion.button>
        </div>

        {/* Live Voice Status Box */}
        {(voiceOnboardingState !== 'idle' || isSpeaking || isListening) && (
          <motion.div
            className="voice-status-panel"
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            role="status"
            aria-live="polite"
          >
            <div className="loader voice-status-loader" />
            <span>{transcript ? `${t.heard}: "${transcript}"` : voiceFeedback || (isListening ? t.listeningNow : t.speakingNow)}</span>
          </motion.div>
        )}

      </header>

      {/* 4 Prominent Numbered Picture Action Cards */}
      <main className="sketch-cards">
        {/* 1. Form Fill Card */}
        <motion.div
          className="action-card card-1"
          onClick={() => handleStartCard('/form-fill')}
          initial={{ opacity: 0, y: 15 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1, duration: 0.3 }}
          role="button"
          tabIndex={0}
          onKeyDown={(e) => e.key === 'Enter' && handleStartCard('/form-fill')}
          style={{
            padding: '24px 24px',
            borderRadius: 20,
            border: '2.5px solid #cbd5e1',
            background: '#ffffff',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: 18,
            boxShadow: '0 6px 20px rgba(0,0,0,0.06)',
            position: 'relative',
          }}
        >
          <div
            style={{
              width: 52,
              height: 52,
              borderRadius: '50%',
              background: '#0284c7',
              color: '#ffffff',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontSize: 24,
              fontWeight: 900,
              flexShrink: 0,
            }}
          >
            {t.formFill.num}
          </div>

          <div style={{ fontSize: 36, flexShrink: 0 }}>📄</div>

          <div style={{ flex: 1, minWidth: 0 }}>
            <h2 style={{ fontSize: 20, fontWeight: 800, margin: '0 0 4px', color: '#0f172a' }}>
              {t.formFill.title}
            </h2>
            <p style={{ fontSize: 13, color: '#475569', margin: '0 0 8px', lineHeight: 1.4 }}>
              {t.formFill.desc}
            </p>
            <button
              type="button"
              onClick={(e) => handleReadAloud(e, t.formFill.audio)}
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: 5,
                padding: '4px 12px',
                borderRadius: 16,
                fontSize: 12,
                fontWeight: 700,
                border: '1px solid #cbd5e1',
                background: '#f8fafc',
                cursor: 'pointer',
              }}
            >
              <Volume2 size={13} /> 🔊 {t.listenBtn}
            </button>
          </div>

          <div style={{ color: '#0284c7' }}>
            <ArrowRight size={24} />
          </div>
        </motion.div>

        {/* 2. Govt Schemes Card */}
        <motion.div
          className="action-card card-2"
          onClick={() => handleStartCard('/schemes')}
          initial={{ opacity: 0, y: 15 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.15, duration: 0.3 }}
          role="button"
          tabIndex={0}
          onKeyDown={(e) => e.key === 'Enter' && handleStartCard('/schemes')}
          style={{
            padding: '24px 24px',
            borderRadius: 20,
            border: '2.5px solid #cbd5e1',
            background: '#ffffff',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: 18,
            boxShadow: '0 6px 20px rgba(0,0,0,0.06)',
          }}
        >
          <div
            style={{
              width: 52,
              height: 52,
              borderRadius: '50%',
              background: '#d97706',
              color: '#ffffff',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontSize: 24,
              fontWeight: 900,
              flexShrink: 0,
            }}
          >
            {t.govtScheme.num}
          </div>

          <div style={{ fontSize: 36, flexShrink: 0 }}>🏛️</div>

          <div style={{ flex: 1, minWidth: 0 }}>
            <h2 style={{ fontSize: 20, fontWeight: 800, margin: '0 0 4px', color: '#0f172a' }}>
              {t.govtScheme.title}
            </h2>
            <p style={{ fontSize: 13, color: '#475569', margin: '0 0 8px', lineHeight: 1.4 }}>
              {t.govtScheme.desc}
            </p>
            <button
              type="button"
              onClick={(e) => handleReadAloud(e, t.govtScheme.audio)}
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: 5,
                padding: '4px 12px',
                borderRadius: 16,
                fontSize: 12,
                fontWeight: 700,
                border: '1px solid #cbd5e1',
                background: '#f8fafc',
                cursor: 'pointer',
              }}
            >
              <Volume2 size={13} /> 🔊 {t.listenBtn}
            </button>
          </div>

          <div style={{ color: '#d97706' }}>
            <ArrowRight size={24} />
          </div>
        </motion.div>

        {/* 3. Ask Banking Question Card */}
        <motion.div
          className="action-card card-3"
          onClick={() => handleStartCard('/guidance')}
          initial={{ opacity: 0, y: 15 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2, duration: 0.3 }}
          role="button"
          tabIndex={0}
          onKeyDown={(e) => e.key === 'Enter' && handleStartCard('/guidance')}
          style={{
            padding: '24px 24px',
            borderRadius: 20,
            border: '2.5px solid #cbd5e1',
            background: '#ffffff',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: 18,
            boxShadow: '0 6px 20px rgba(0,0,0,0.06)',
          }}
        >
          <div
            style={{
              width: 52,
              height: 52,
              borderRadius: '50%',
              background: '#7c3aed',
              color: '#ffffff',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontSize: 24,
              fontWeight: 900,
              flexShrink: 0,
            }}
          >
            {t.guidance.num}
          </div>

          <div style={{ fontSize: 36, flexShrink: 0 }}>💬</div>

          <div style={{ flex: 1, minWidth: 0 }}>
            <h2 style={{ fontSize: 20, fontWeight: 800, margin: '0 0 4px', color: '#0f172a' }}>
              {t.guidance.title}
            </h2>
            <p style={{ fontSize: 13, color: '#475569', margin: '0 0 8px', lineHeight: 1.4 }}>
              {t.guidance.desc}
            </p>
            <button
              type="button"
              onClick={(e) => handleReadAloud(e, t.guidance.audio)}
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: 5,
                padding: '4px 12px',
                borderRadius: 16,
                fontSize: 12,
                fontWeight: 700,
                border: '1px solid #cbd5e1',
                background: '#f8fafc',
                cursor: 'pointer',
              }}
            >
              <Volume2 size={13} /> 🔊 {t.listenBtn}
            </button>
          </div>

          <div style={{ color: '#7c3aed' }}>
            <ArrowRight size={24} />
          </div>
        </motion.div>

        {/* 4. Fraud & SMS Check Card */}
        <motion.div
          className="action-card card-4"
          onClick={() => handleStartCard('/fraud-check')}
          initial={{ opacity: 0, y: 15 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.25, duration: 0.3 }}
          role="button"
          tabIndex={0}
          onKeyDown={(e) => e.key === 'Enter' && handleStartCard('/fraud-check')}
          style={{
            padding: '24px 24px',
            borderRadius: 20,
            border: '2.5px solid #cbd5e1',
            background: '#ffffff',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: 18,
            boxShadow: '0 6px 20px rgba(0,0,0,0.06)',
          }}
        >
          <div
            style={{
              width: 52,
              height: 52,
              borderRadius: '50%',
              background: '#059669',
              color: '#ffffff',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontSize: 24,
              fontWeight: 900,
              flexShrink: 0,
            }}
          >
            {t.fraudCheck.num}
          </div>

          <div style={{ fontSize: 36, flexShrink: 0 }}>🛡️</div>

          <div style={{ flex: 1, minWidth: 0 }}>
            <h2 style={{ fontSize: 20, fontWeight: 800, margin: '0 0 4px', color: '#0f172a' }}>
              {t.fraudCheck.title}
            </h2>
            <p style={{ fontSize: 13, color: '#475569', margin: '0 0 8px', lineHeight: 1.4 }}>
              {t.fraudCheck.desc}
            </p>
            <button
              type="button"
              onClick={(e) => handleReadAloud(e, t.fraudCheck.audio)}
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: 5,
                padding: '4px 12px',
                borderRadius: 16,
                fontSize: 12,
                fontWeight: 700,
                border: '1px solid #cbd5e1',
                background: '#f8fafc',
                cursor: 'pointer',
              }}
            >
              <Volume2 size={13} /> 🔊 {t.listenBtn}
            </button>
          </div>

          <div style={{ color: '#059669' }}>
            <ArrowRight size={24} />
          </div>
        </motion.div>
      </main>
    </div>
  );
}
