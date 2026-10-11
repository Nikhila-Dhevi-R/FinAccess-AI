import { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { MessageCircle, Send, Volume2, Sparkles, CornerDownLeft, RotateCcw } from 'lucide-react';
import { VoiceButton } from '../components/VoiceButton';
import { useSpeech } from '../hooks/useSpeech';
import { useSession } from '../hooks/useSession';
import { askGuidance } from '../api/client';
import { playListenChime, playSuccessChime } from '../utils/audioCue';

// ─── Multilingual quick questions ────────────────────────────────────────────
const QUICK_QUESTIONS = {
  en: [
    'How do I open a bank account?',
    'What is PMJDY and its benefits?',
    'What is an EMI on a loan?',
    'How does UPI payment work?',
    'Tell me about PM accident insurance',
    'What should I do if someone asks for my OTP?',
  ],
  hi: [
    'बैंक खाता कैसे खोलें?',
    'PMJDY योजना क्या है?',
    'EMI क्या होता है?',
    'UPI पेमेंट कैसे काम करता है?',
    'दुर्घटना बीमा के बारे में बताएं',
    'OTP किसे नहीं देना चाहिए?',
  ],
  ta: [
    'வங்கி கணக்கு எப்படி திறப்பது?',
    'PMJDY திட்டம் என்ன?',
    'EMI என்றால் என்ன?',
    'UPI பணம் எப்படி செலுத்துவது?',
    'விபத்து காப்பீடு பற்றி சொல்லுங்கள்',
    'OTP யாரிடம் கொடுக்கக்கூடாது?',
  ],
};

const WELCOME = {
  en: "Namaste! I am your FinAccess Financial Guide. Ask me anything about banking, loans, savings, government schemes, or safety tips — by speaking or typing.",
  hi: "नमस्ते! मैं आपका FinAccess वित्तीय सलाहकार हूँ। बैंकिंग, लोन, सरकारी योजनाओं के बारे में बोलकर या लिखकर पूछें।",
  ta: "வணக்கம்! நான் உங்கள் FinAccess நிதி வழிகாட்டி. வங்கி, கடன், அரசு திட்டங்கள் பற்றி பேசியோ தட்டச்சு செய்தோ கேளுங்கள்.",
};

const CHAT_TEXT = {
  en: { you: 'You', newChat: 'New chat', kept: 'This conversation stays on this device until you close the tab or start a new chat.', speaking: 'Speaking...', listen: 'Listen' },
  hi: { you: 'आप', newChat: 'नई बातचीत', kept: 'यह बातचीत टैब बंद करने या नई बातचीत शुरू करने तक इसी डिवाइस पर रहती है।', speaking: 'बोल रहा हूँ...', listen: 'सुनें' },
  ta: { you: 'நீங்கள்', newChat: 'புதிய உரையாடல்', kept: 'தாவலை மூடும் வரை அல்லது புதிய உரையாடல் தொடங்கும் வரை இந்த உரையாடல் இந்தச் சாதனத்தில் இருக்கும்.', speaking: 'பேசுகிறது...', listen: 'கேளுங்கள்' },
};

// Category badge shown on each answer
const CATEGORY_LABELS = {
  banking: ['Bank account', 'बैंक खाता', 'வங்கிக் கணக்கு'],
  cards: ['ATM & cards', 'एटीएम और कार्ड', 'ஏடிஎம் & அட்டைகள்'],
  payments: ['Payments & UPI', 'भुगतान और UPI', 'பணப் பரிமாற்றம் & UPI'],
  savings: ['Savings', 'बचत', 'சேமிப்பு'],
  loans: ['Loans', 'लोन', 'கடன்'],
  insurance: ['Insurance', 'बीमा', 'காப்பீடு'],
  pension: ['Pension', 'पेंशन', 'ஓய்வூதியம்'],
  schemes: ['Govt schemes', 'सरकारी योजना', 'அரசுத் திட்டம்'],
  safety: ['Safety', 'सुरक्षा', 'பாதுகாப்பு'],
  complaints: ['Complaints', 'शिकायत', 'புகார்'],
  documents: ['Documents', 'दस्तावेज़', 'ஆவணங்கள்'],
  tax: ['Tax', 'टैक्स', 'வரி'],
  app: ['Using this app', 'इस ऐप का उपयोग', 'இந்தச் செயலி'],
  calculator: ['Calculator', 'हिसाब', 'கணக்கீடு'],
};
const LANG_POS = { en: 0, hi: 1, ta: 2 };

// The conversation is kept for this browser tab (survives page changes and reloads, cleared when the tab closes)
const CHAT_STORAGE_KEY = 'finaccess_chat_v2';

function loadChat() {
  try {
    const saved = JSON.parse(sessionStorage.getItem(CHAT_STORAGE_KEY) || 'null');
    if (saved && Array.isArray(saved.messages) && saved.messages.length) return saved;
  } catch {
    // ignore unreadable storage
  }
  return null;
}

function saveChat(messages, context) {
  try {
    sessionStorage.setItem(CHAT_STORAGE_KEY, JSON.stringify({ messages: messages.slice(-60), context }));
  } catch {
    // storage full or blocked — the chat still works in memory
  }
}

function buildInitialMessage(lang) {
  return {
    id: 'init-1',
    role: 'bot',
    text: WELCOME[lang] || WELCOME.en,
    audioText: WELCOME[lang] || WELCOME.en,
    intent: 'welcome',
    followUps: [],
  };
}

export default function Guidance() {
  const { sessionId, language } = useSession();
  const { speak, listen, stopListening, isListening, isSpeaking, transcript, setTranscript, error: speechError } = useSpeech(language);

  const ct = CHAT_TEXT[language] || CHAT_TEXT.en;
  const [restored] = useState(() => loadChat());
  const [messages, setMessages] = useState(() => restored?.messages || [buildInitialMessage(language)]);
  const [chatContext, setChatContext] = useState(() => restored?.context || {});
  const [inputText, setInputText] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [hasSpokenWelcome, setHasSpokenWelcome] = useState(Boolean(restored && restored.messages.length > 1));
  const chatEndRef = useRef(null);

  // Keep the conversation for this tab
  useEffect(() => {
    saveChat(messages, chatContext);
  }, [messages, chatContext]);

  // Site language changed before anything was asked: greet in the new language
  useEffect(() => {
    setMessages((prev) => (prev.length === 1 && prev[0].intent === 'welcome' ? [buildInitialMessage(language)] : prev));
  }, [language]);

  const startNewChat = () => {
    setMessages([buildInitialMessage(language)]);
    setChatContext({});
    setInputText('');
    setTranscript('');
    speak(WELCOME[language] || WELCOME.en);
  };

  // Speak welcome once on mount (not when returning to an ongoing conversation)
  useEffect(() => {
    if (!hasSpokenWelcome) {
      const timer = setTimeout(() => {
        speak(WELCOME[language] || WELCOME.en);
        setHasSpokenWelcome(true);
      }, 600);
      return () => clearTimeout(timer);
    }
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  const handleSend = async (queryText) => {
    const text = (queryText || inputText || transcript).trim();
    if (!text || isLoading) return;

    setInputText('');
    setTranscript('');

    const userMsg = {
      id: `user-${Date.now()}`,
      role: 'user',
      text,
    };

    setMessages((prev) => [...prev, userMsg]);
    setIsLoading(true);

    try {
      // recent turns, so the guide knows what "yes", "that one" or "what documents?" refer to
      const history = messages
        .filter((m) => m.intent !== 'welcome')
        .slice(-12)
        .map((m) => ({ role: m.role, text: m.text, topic: m.topic || null }));
      const resp = await askGuidance(sessionId || 'guest-session', text, language, history, chatContext);
      const botMsg = {
        id: `bot-${Date.now()}`,
        role: 'bot',
        text: resp.answer,
        audioText: resp.answer_audio_text || resp.answer,
        intent: resp.intent,
        topic: resp.topic || null,
        sources: resp.sources || [],
        followUps: resp.follow_up_suggestions || [],
      };
      setChatContext(resp.context || {});
      setMessages((prev) => [...prev, botMsg]);
      playSuccessChime();
      speak(botMsg.audioText);
    } catch (err) {
      console.warn('Guidance API error — using offline fallback:', err);
      const fallbackMsg = {
        id: `bot-${Date.now()}`,
        role: 'bot',
        text: language === 'hi'
          ? 'बैंकिंग सेवाओं के लिए Aadhaar जैसे KYC दस्तावेज जरूरी हैं। कभी भी अपना OTP या PIN किसी को न दें।'
          : language === 'ta'
          ? 'வங்கி சேவைகளுக்கு Aadhaar போன்ற KYC ஆவணங்கள் தேவை. உங்கள் OTP அல்லது PIN யாரிடமும் கொடுக்காதீர்கள்.'
          : 'For banking services, you need KYC documents like Aadhaar. Never share your OTP or PIN with anyone.',
        audioText: language === 'hi'
          ? 'बैंकिंग के लिए Aadhaar जरूरी है। OTP किसी को न दें।'
          : language === 'ta'
          ? 'வங்கிக்கு Aadhaar தேவை. OTP யாரிடமும் கொடுக்காதீர்கள்.'
          : 'For banking, you need Aadhaar. Never share your OTP.',
        intent: 'general',
        followUps:
          language === 'hi'
            ? ['धोखाधड़ी की शिकायत कैसे करें?', 'खाता खोलने के लिए क्या चाहिए?']
            : ['How do I report a fraud?', 'What documents are needed for a bank account?'],
      };
      setMessages((prev) => [...prev, fallbackMsg]);
      speak(fallbackMsg.audioText);
    } finally {
      setIsLoading(false);
    }
  };

  const handleVoiceInput = async () => {
    try {
      playListenChime();
      const heard = await listen();
      if (heard && heard.trim()) {
        handleSend(heard.trim());
      }
    } catch (e) {
      console.warn('Speech recognition error:', e);
    }
  };

  const qs = QUICK_QUESTIONS[language] || QUICK_QUESTIONS.en;

  return (
    <div className="container" style={{ padding: 'var(--space-6) 0 var(--space-8)' }}>
      {/* Header */}
      <div className="page-header" style={{ textAlign: 'center', maxWidth: 680, margin: '0 auto var(--space-6)' }}>
        <div className="badge badge-teal" style={{ marginBottom: 'var(--space-2)' }}>
          <MessageCircle size={13} style={{ marginRight: 6 }} />
          {language === 'hi' ? 'AI वित्त सलाहकार' : language === 'ta' ? 'AI நிதி வழிகாட்டி' : 'AI Financial Mentor'}
        </div>
        <h1 className="page-title">
          {language === 'hi' ? 'वित्तीय मार्गदर्शन' : language === 'ta' ? 'நிதி வழிகாட்டல்' : 'Financial Guidance & FAQ'}
        </h1>
        <p className="page-subtitle">
          {language === 'hi'
            ? 'अपनी भाषा में बोलकर या लिखकर सवाल पूछें। बैंक, लोन, सरकारी योजनाओं और सुरक्षा के बारे में जानें।'
            : language === 'ta'
            ? 'உங்கள் மொழியில் பேசியோ தட்டச்சு செய்தோ கேளுங்கள். வங்கி, கடன், அரசு திட்டங்கள் பற்றி தெரிந்துகொள்ளுங்கள்.'
            : 'Ask questions in your mother tongue. Speak or type to understand banking, loans, government schemes, and safe money habits.'}
        </p>
      </div>

      {/* Big Voice Button — primary CTA for low-literacy users */}
      <div style={{ textAlign: 'center', marginBottom: 'var(--space-5)' }}>
        <button
          onClick={handleVoiceInput}
          disabled={isListening || isSpeaking}
          style={{
            background: isListening ? 'var(--color-red)' : 'var(--color-primary)',
            color: '#fff',
            border: 'none',
            borderRadius: 'var(--radius-full)',
            padding: '18px 40px',
            fontSize: 18,
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
          <span style={{ fontSize: 28 }}>{isListening ? '🔴' : '🎙️'}</span>
          {isListening
            ? (language === 'hi' ? 'सुन रहा हूँ...' : language === 'ta' ? 'கேட்கிறேன்...' : 'Listening...')
            : (language === 'hi' ? 'बोलकर पूछें' : language === 'ta' ? 'பேசி கேளுங்கள்' : 'Tap & Ask by Voice')}
        </button>
        <p style={{ fontSize: 13, color: 'var(--color-text-secondary)', marginTop: 8 }}>
          {language === 'hi' ? 'या नीचे सवाल चुनें / लिखें' : language === 'ta' ? 'அல்லது கீழே கேள்வி தேர்ந்தெடுங்கள் / தட்டச்சு செய்யுங்கள்' : 'or pick a question below / type'}
        </p>
      </div>

      {/* Quick Prompts */}
      <div style={{ maxWidth: 840, margin: '0 auto var(--space-5)' }}>
        <p style={{ fontSize: 13, color: 'var(--color-text-secondary)', marginBottom: 8, display: 'flex', alignItems: 'center', gap: 6 }}>
          <Sparkles size={14} color="var(--color-teal)" />
          {language === 'hi' ? 'लोकप्रिय सवाल:' : language === 'ta' ? 'பொதுவான கேள்விகள்:' : 'Popular questions:'}
        </p>
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', paddingBottom: 6 }}>
          {qs.map((q, i) => (
            <button
              key={i}
              onClick={() => handleSend(q)}
              disabled={isLoading}
              className="btn btn-secondary btn-sm"
              style={{
                whiteSpace: 'nowrap',
                fontSize: 13,
                borderRadius: 'var(--radius-full)',
                padding: '8px 16px',
                background: 'var(--color-bg-card)',
                border: '1px solid var(--color-border)',
                cursor: 'pointer',
              }}
            >
              {q}
            </button>
          ))}
        </div>
      </div>

      {/* Conversation controls */}
      <div style={{ maxWidth: 840, margin: '0 auto 8px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 12, flexWrap: 'wrap' }}>
        <span style={{ fontSize: 12, color: 'var(--color-text-secondary)' }}>{ct.kept}</span>
        <button
          type="button"
          onClick={startNewChat}
          disabled={isLoading || messages.length <= 1}
          className="btn btn-secondary btn-sm"
          style={{ display: 'inline-flex', alignItems: 'center', gap: 6, borderRadius: 'var(--radius-full)', padding: '6px 14px', fontSize: 13 }}
        >
          <RotateCcw size={14} /> {ct.newChat}
        </button>
      </div>

      {/* Main Chat Box */}
      <div
        className="glass-card"
        style={{
          maxWidth: 840,
          margin: '0 auto',
          display: 'flex',
          flexDirection: 'column',
          height: '520px',
          overflow: 'hidden',
          borderRadius: 'var(--radius-xl)',
          border: '1px solid var(--color-border)',
        }}
      >
        {/* Chat Messages */}
        <div className="chat-area" style={{ flex: 1, padding: 'var(--space-5)', overflowY: 'auto' }}>
          <AnimatePresence initial={false}>
            {messages.map((m) => (
              <motion.div
                key={m.id}
                initial={{ opacity: 0, y: 10, scale: 0.98 }}
                animate={{ opacity: 1, y: 0, scale: 1 }}
                transition={{ duration: 0.2 }}
                className={`chat-msg ${m.role}`}
                style={{
                  maxWidth: '82%',
                  marginBottom: 'var(--space-3)',
                  boxShadow: '0 4px 14px rgba(0,0,0,0.2)',
                }}
              >
                {/* Role header */}
                <div
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    fontSize: 11,
                    fontWeight: 700,
                    textTransform: 'uppercase',
                    letterSpacing: '0.05em',
                    opacity: 0.7,
                    marginBottom: 6,
                  }}
                >
                  <span>{m.role === 'bot' ? '🎙 FinAccess AI' : `👤 ${ct.you}`}</span>
                  {m.intent && CATEGORY_LABELS[m.intent] && (
                    <span className="badge badge-teal" style={{ fontSize: 9, padding: '1px 6px' }}>
                      {CATEGORY_LABELS[m.intent][LANG_POS[language] ?? 0]}
                    </span>
                  )}
                </div>

                {/* Message body */}
                <p style={{ margin: 0, fontSize: 15, lineHeight: 1.65 }}>{m.text}</p>

                {/* TTS replay */}
                {m.role === 'bot' && m.audioText && (
                  <div style={{ marginTop: 10, display: 'flex', alignItems: 'center', gap: 8 }}>
                    <button
                      onClick={() => speak(m.audioText)}
                      className="btn btn-sm btn-secondary"
                      style={{
                        padding: '5px 12px',
                        fontSize: 12,
                        borderRadius: 'var(--radius-full)',
                        display: 'inline-flex',
                        alignItems: 'center',
                        gap: 5,
                      }}
                      title="Listen to this explanation"
                    >
                      <Volume2 size={13} color="var(--color-teal)" />
                      <span>{isSpeaking ? ct.speaking : ct.listen}</span>
                    </button>
                  </div>
                )}

                {/* Follow-up suggestions */}
                {m.followUps && m.followUps.length > 0 && (
                  <div style={{ marginTop: 12, paddingTop: 10, borderTop: '1px solid var(--color-border)' }}>
                    <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--color-text-secondary)', marginBottom: 6, display: 'flex', alignItems: 'center', gap: 4 }}>
                      <CornerDownLeft size={12} />
                      {language === 'hi' ? 'आगे पूछें:' : language === 'ta' ? 'தொடர்ந்து கேளுங்கள்:' : 'Suggested follow-ups:'}
                    </div>
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                      {m.followUps.map((fu, idx) => (
                        <button
                          key={idx}
                          onClick={() => handleSend(fu)}
                          style={{
                            background: 'var(--color-bg-subtle)',
                            border: '1px solid var(--color-border)',
                            borderRadius: 'var(--radius-full)',
                            padding: '5px 14px',
                            fontSize: 12,
                            color: 'var(--color-text-primary)',
                            cursor: 'pointer',
                            transition: 'all 0.2s',
                          }}
                          onMouseEnter={(e) => (e.currentTarget.style.borderColor = 'var(--color-primary)')}
                          onMouseLeave={(e) => (e.currentTarget.style.borderColor = 'var(--color-border)')}
                        >
                          {fu}
                        </button>
                      ))}
                    </div>
                  </div>
                )}
              </motion.div>
            ))}
          </AnimatePresence>

          {isLoading && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="chat-msg bot"
              style={{ display: 'flex', alignItems: 'center', gap: 10 }}
            >
              <div className="loader" style={{ width: 18, height: 18 }} />
              <span style={{ fontSize: 13, color: 'var(--color-text-secondary)' }}>
                {language === 'hi' ? 'FinAccess AI जवाब ढूंढ रहा है...' : language === 'ta' ? 'FinAccess AI பதில் தேடுகிறது...' : 'FinAccess AI is finding answers for you...'}
              </span>
            </motion.div>
          )}

          <div ref={chatEndRef} />
        </div>

        {/* Text Input Bar */}
        <div
          className="chat-input-row"
          style={{
            background: '#FFFFFF',
            borderTop: '1.5px solid var(--color-border)',
            alignItems: 'center',
          }}
        >
          <VoiceButton
            isListening={isListening}
            isSpeaking={isSpeaking}
            onClick={isListening ? stopListening : handleVoiceInput}
            language={language}
            size="small"
            error={speechError}
            label={isListening ? (language === 'hi' ? 'सुन रहा हूँ...' : 'Listening...') : (language === 'hi' ? 'बोलें' : language === 'ta' ? 'பேசுங்கள்' : 'Speak')}
          />

          <input
            type="text"
            className="chat-input"
            value={inputText}
            placeholder={
              language === 'hi'
                ? 'यहाँ अपना सवाल लिखें या बोलें...'
                : language === 'ta'
                ? 'இங்கே கேள்வி தட்டச்சு செய்யுங்கள் அல்லது பேசுங்கள்...'
                : 'Speak or type your financial question here...'
            }
            onChange={(e) => setInputText(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter') handleSend();
            }}
          />

          <button
            className="btn btn-primary"
            onClick={() => handleSend()}
            disabled={!inputText.trim() || isLoading}
            style={{
              padding: '12px 18px',
              borderRadius: 'var(--radius-full)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
          >
            <Send size={16} />
          </button>
        </div>
      </div>
    </div>
  );
}
