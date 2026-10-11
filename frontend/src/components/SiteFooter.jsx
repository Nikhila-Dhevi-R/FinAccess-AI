import { useSession } from '../hooks/useSession';

const FOOTER_TEXT = {
  en: {
    title: 'FinAccess AI — Simple, Voice-Guided Assistance for Everyone',
    sub: 'Empowering citizens across India with voice-first banking, forms, and welfare schemes.',
  },
  hi: {
    title: 'FinAccess AI — सबके लिए आसान, आवाज़ से चलने वाली सहायता',
    sub: 'आवाज़ से बैंकिंग, फॉर्म और कल्याणकारी योजनाओं के ज़रिए पूरे भारत के नागरिकों को सशक्त बनाना।',
  },
  ta: {
    title: 'FinAccess AI — அனைவருக்கும் எளிய, குரல் வழி உதவி',
    sub: 'குரல் வழி வங்கி, படிவங்கள், நலத்திட்டங்கள் மூலம் இந்தியா முழுவதும் குடிமக்களுக்கு அதிகாரம் அளித்தல்.',
  },
};

export function SiteFooter() {
  const { language } = useSession();
  const ft = FOOTER_TEXT[language] || FOOTER_TEXT.en;
  return (
    <footer
      style={{
        borderTop: '1.5px solid var(--color-border)',
        padding: 'var(--space-5) 0',
        textAlign: 'center',
        color: 'var(--color-text-secondary)',
        fontSize: '14px',
        background: 'var(--color-bg-secondary)',
      }}
    >
      <div className="container">
        <p style={{ margin: 0, fontWeight: 600, color: 'var(--color-text-primary)' }}>{ft.title}</p>
        <p style={{ margin: '4px 0 0', fontSize: '13px', color: 'var(--color-text-muted)' }}>{ft.sub}</p>
      </div>
    </footer>
  );
}
