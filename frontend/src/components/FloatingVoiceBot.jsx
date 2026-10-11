import { useNavigate, useLocation } from 'react-router-dom';
import { Mic, MessageSquare } from 'lucide-react';
import { useSpeech } from '../hooks/useSpeech';
import { useSession } from '../hooks/useSession';

const BOT_TEXT = {
  en: { open: 'Opening Voice Assistant. Ask me any question about money, banking, forms or schemes.', label: 'Voice chat bot', aria: 'Voice Chat Bot: Speak to get help with banking and government schemes' },
  hi: { open: 'वॉइस सहायक खुल रहा है। पैसे, बैंकिंग, फॉर्म या योजनाओं के बारे में कोई भी सवाल पूछें।', label: 'वॉइस चैट बॉट', aria: 'वॉइस चैट बॉट: बैंकिंग और सरकारी योजनाओं में मदद के लिए बोलें' },
  ta: { open: 'குரல் உதவியாளர் திறக்கிறது. பணம், வங்கி, படிவங்கள் அல்லது திட்டங்கள் பற்றி எந்தக் கேள்வியும் கேளுங்கள்.', label: 'குரல் உரையாடல்', aria: 'குரல் உரையாடல்: வங்கி மற்றும் அரசுத் திட்ட உதவிக்குப் பேசுங்கள்' },
};

export function FloatingVoiceBot() {
  const navigate = useNavigate();
  const location = useLocation();
  const { language } = useSession();
  const { speak } = useSpeech(language);
  const bt = BOT_TEXT[language] || BOT_TEXT.en;

  // If already on guidance page, we don't need to obscure the interface
  const isGuidancePage = location.pathname === '/guidance';

  const handleClick = () => {
    if (!isGuidancePage) {
      speak(bt.open);
      navigate('/guidance');
    }
  };

  return (
    <aside
      className="floating-voice-container"
      aria-label="Voice Assistant Navigation"
    >
      <button
        type="button"
        className={`floating-voice-circle${isGuidancePage ? ' active' : ''}`}
        onClick={handleClick}
        aria-label={bt.aria}
        title={bt.aria}
      >
        <Mic size={36} strokeWidth={2.4} />
      </button>
      <div className="floating-voice-label" aria-hidden="true">
        {bt.label}
      </div>
    </aside>
  );
}
