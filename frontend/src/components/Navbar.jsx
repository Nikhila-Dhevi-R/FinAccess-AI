import { Link, useLocation } from 'react-router-dom';
import { FileText, Landmark, MessageCircle, Shield, Home, Volume2, Globe } from 'lucide-react';
import { useSession } from '../hooks/useSession';
import { useSpeech } from '../hooks/useSpeech';

const NAV_ITEMS = [
  { path: '/', label: 'Home', hiLabel: 'होम', taLabel: 'முகப்பு', icon: <Home size={18} /> },
  { path: '/form-fill', label: '1. Form Fill', hiLabel: '1. फॉर्म भरें', taLabel: '1. படிவம்', icon: <FileText size={18} /> },
  { path: '/schemes', label: '2. Schemes', hiLabel: '2. योजनाएं', taLabel: '2. திட்டங்கள்', icon: <Landmark size={18} /> },
  { path: '/guidance', label: '3. Ask Question', hiLabel: '3. सवाल पूछें', taLabel: '3. கேள்வி', icon: <MessageCircle size={18} /> },
  { path: '/fraud-check', label: '4. Fraud Check', hiLabel: '4. सुरक्षा जांच', taLabel: '4. மோசடி', icon: <Shield size={18} /> },
];

// The one language switch for the whole site
const QUICK_LANGS = [
  { code: 'en', label: 'English', audio: 'You selected English. The whole site is now in English.' },
  { code: 'hi', label: 'हिन्दी', audio: 'आपने हिन्दी चुनी है। पूरी साइट अब हिन्दी में है।' },
  { code: 'ta', label: 'தமிழ்', audio: 'நீங்கள் தமிழைத் தேர்ந்தெடுத்துள்ளீர்கள். முழு தளமும் இப்போது தமிழில் உள்ளது.' },
];

const LANG_TITLE = {
  en: 'Language for the whole site',
  hi: 'पूरी साइट की भाषा',
  ta: 'முழு தளத்தின் மொழி',
};

const STOP_TEXTS = { en: 'Stop', hi: 'रोकें', ta: 'நிறுத்து' };

const REPEAT_TEXTS = {
  en: 'Repeat Audio',
  hi: 'दोबारा सुनें',
  ta: 'மீண்டும் கேட்க',
};

export function Navbar() {
  const location = useLocation();
  const { language, changeLanguage } = useSession();
  const lang = language === 'hi' || language === 'ta' ? language : 'en';
  const { speak, isSpeaking, stopSpeaking } = useSpeech(lang);

  const handleLanguage = (code) => {
    if (code === language) return;
    changeLanguage(code);
    const item = QUICK_LANGS.find((l) => l.code === code);
    // confirm in the newly chosen language and voice
    setTimeout(() => speak(item.audio, null, code), 150);
  };

  const handleNavRepeat = () => {
    if (isSpeaking) {
      stopSpeaking();
      return;
    }
    const currentItem = NAV_ITEMS.find((n) => n.path === location.pathname);
    let msg = '';
    if (location.pathname === '/') {
      msg = lang === 'hi'
        ? 'मुख्य मेनू। फॉर्म भरने के लिए 1, सरकारी योजनाओं के लिए 2, बैंकिंग सवाल के लिए 3, या धोखाधड़ी जांच के लिए 4 चुनें।'
        : lang === 'ta'
        ? 'முதன்மை பட்டியல். படிவம் நிரப்ப 1, அரசு திட்டங்களை பார்க்க 2, வங்கி கேள்வி கேட்க 3, மோசடி சரிபார்க்க 4 தேர்வு செய்யவும்.'
        : 'Main Menu. Choose 1 to Fill a Form, 2 for Schemes, 3 to Ask a Question, or 4 for Fraud Check.';
    } else if (location.pathname === '/form-fill') {
      msg = lang === 'hi' ? 'बोलकर फॉर्म भरें। अपना फॉर्म अपलोड करें और बोलकर जवाब दें।' : lang === 'ta' ? 'குரல் மூலம் படிவம் நிரப்புதல்.' : 'Voice Form Fill. Upload your form and speak your answers.';
    } else if (location.pathname === '/schemes') {
      msg = lang === 'hi' ? 'सरकारी योजनाएं। 3 सरल सवालों के जवाब दें और अपने लिए योजनाएं खोजें।' : lang === 'ta' ? 'அரசு நலத்திட்டங்கள் கண்டறியுங்கள்.' : 'Government Schemes. Find welfare schemes and benefits you can receive.';
    } else if (location.pathname === '/guidance') {
      msg = lang === 'hi' ? 'आवाज़ वित्तीय सलाहकार। बैंकिंग के बारे में कोई भी सवाल पूछें।' : lang === 'ta' ? 'குரல் நிதி வழிகாட்டி.' : 'Voice Financial Guide. Ask any banking or financial questions.';
    } else if (location.pathname === '/fraud-check') {
      msg = lang === 'hi' ? 'धोखाधड़ी जांच। कोई भी संदिग्ध मैसेज यहां जांचें।' : lang === 'ta' ? 'மோசடி செய்தி சரிபார்ப்பு.' : 'Fraud Check. Check any suspicious message or SMS for safety.';
    }
    speak(msg);
  };

  return (
    <nav className="navbar" aria-label="Main Navigation">
      <div className="container navbar-inner" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12, flexWrap: 'wrap' }}>
        <Link to="/" className="navbar-logo" style={{ textDecoration: 'none', display: 'flex', alignItems: 'center', gap: 8 }}>
          <div className="logo-icon" aria-hidden="true" style={{ fontSize: 24 }}>🎙</div>
          <span style={{ fontSize: 20, fontWeight: 900, color: '#0f172a' }}>
            FinAccess <span style={{ color: 'var(--color-primary, #0284c7)' }}>AI</span>
          </span>
        </Link>

        <ul className="navbar-nav" style={{ display: 'flex', gap: 8, listStyle: 'none', margin: 0, padding: 0, flexWrap: 'wrap' }}>
          {NAV_ITEMS.map((item) => {
            const itemLabel = lang === 'hi' ? item.hiLabel : lang === 'ta' ? item.taLabel : item.label;
            return (
              <li key={item.path}>
                <Link
                  to={item.path}
                  className={`nav-link${location.pathname === item.path ? ' active' : ''}`}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: 6,
                    padding: '8px 14px',
                    borderRadius: 20,
                    textDecoration: 'none',
                    fontSize: 14,
                    fontWeight: 700,
                  }}
                >
                  {item.icon}
                  {itemLabel}
                </Link>
              </li>
            );
          })}
        </ul>

        {/* Persistent Repeat Audio & Language Bar */}
        <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
          <button
            type="button"
            onClick={handleNavRepeat}
            title="Repeat Audio Instructions"
            style={{
              background: isSpeaking ? '#fee2e2' : '#f1f5f9',
              color: isSpeaking ? '#dc2626' : '#334155',
              border: '1.5px solid #cbd5e1',
              borderRadius: 20,
              padding: '6px 12px',
              fontSize: 13,
              fontWeight: 700,
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: 5,
            }}
          >
            <Volume2 size={15} />
            <span>{isSpeaking ? STOP_TEXTS[lang] : REPEAT_TEXTS[lang]}</span>
          </button>

          <div
            role="group"
            aria-label={LANG_TITLE[lang]}
            title={LANG_TITLE[lang]}
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: 4,
              background: '#f1f5f9',
              padding: '3px 4px 3px 8px',
              borderRadius: 20,
              border: '1px solid #cbd5e1',
            }}
          >
            <Globe size={15} color="#334155" aria-hidden="true" />
            {QUICK_LANGS.map((l) => (
              <button
                type="button"
                key={l.code}
                lang={l.code}
                aria-pressed={language === l.code}
                onClick={() => handleLanguage(l.code)}
                style={{
                  background: language === l.code ? 'var(--color-primary, #0284c7)' : 'transparent',
                  color: language === l.code ? '#ffffff' : '#334155',
                  border: 'none',
                  borderRadius: 16,
                  padding: '4px 10px',
                  fontSize: 12,
                  fontWeight: 800,
                  cursor: 'pointer',
                  transition: 'all 0.15s ease',
                }}
              >
                {l.label}
              </button>
            ))}
          </div>
        </div>
      </div>
    </nav>
  );
}
