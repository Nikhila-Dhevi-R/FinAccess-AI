import { useState, useCallback, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Landmark,
  Volume2,
  RefreshCw,
  AlertCircle,
  CheckCircle2,
  ArrowRight,
  Filter,
  Phone,
  Globe,
  FileCheck,
  ChevronDown,
  ChevronUp,
  Sparkles,
  Search,
  Mic,
  X,
  ArrowLeft,
  Pencil,
} from 'lucide-react';
import { VoiceButton } from '../components/VoiceButton';
import { useSpeech } from '../hooks/useSpeech';
import { useSession } from '../hooks/useSession';
import { fetchSchemeGroups, fetchSchemes, fetchSchemeFilters, matchSchemes } from '../api/client';
import { playListenChime, playSuccessChime } from '../utils/audioCue';

const UI_TEXT = {
  en: {
    badge: '🏛 Central & State Government Welfare Schemes',
    title: 'Find Schemes for You & Your Family',
    subtitle: 'Browse all 8 welfare categories or answer 5 simple voice questions to discover benefits you can receive.',
    tabWizard: '🎙 "What Can I Get?" Voice Wizard',
    tabBrowse: '📂 Browse by 8 Categories',
    step: 'Question',
    of: 'of',
    matchedTitle: 'Directly Matched Schemes',
    needsInfoTitle: 'Schemes Requiring Office Verification / Additional Details',
    repeatBtn: 'Repeat Question',
    skipBtn: 'Skip',
    restartBtn: 'Check Again / Reset',
    listeningHint: 'Tap mic or say your answer:',
    readingNotice: 'Finding your eligible schemes from central database…',
    noSchemes: 'No direct matches found. Please visit your nearest Common Service Centre (CSC) or Gram Panchayat.',
    stateTopUp: 'State Top-up Reminder: Additional state bonus or subsidy may apply in your state.',
    howToApply: 'How & Where to Apply',
    docsNeeded: 'Documents Needed',
    helpline: 'Helpline',
    officialPortal: 'Official Website',
    voiceReaderGuide: 'Say Next, Repeat, Back, or Stop to control scheme audio.',
    searchPlaceholder: 'Search: e.g. pension, farmer loan, girl education, ghar…',
    searchMic: 'Speak to search',
    whoFor: 'Who is it for?',
    whatNeed: 'What do you need?',
    category: 'Category',
    allCategories: 'All categories',
    clearAll: 'Clear filters',
    whoCanGet: 'Who can get it:',
    backBtn: 'Back',
    keepBtn: 'Keep answer',
    yourAnswers: 'Your answers',
    changeBtn: 'Change',
    notAnswered: 'Not answered',
    yourAnswerNow: 'Your answer:',
    showDetails: 'How to Apply & Documents',
    hideDetails: 'Hide Details',
    resultsCount: (n) => `${n} scheme${n === 1 ? '' : 's'} found`,
    noResults: 'No scheme matches these choices. Try removing a filter or searching with a simpler word.',
  },
  hi: {
    badge: '🏛 केंद्र एवं राज्य सरकारी कल्याणकारी योजनाएं',
    title: 'अपने और अपने परिवार के लिए सरकारी योजनाएं खोजें',
    subtitle: 'सभी 8 श्रेणियों में देखें या 5 सरल सवालों के बोलकर जवाब देकर अपनी योजनाएं जानें।',
    tabWizard: '🎙 "मुझे क्या मिल सकता है?" वॉइस विज़ार्ड',
    tabBrowse: '📂 8 श्रेणियों के अनुसार देखें',
    step: 'प्रश्न',
    of: 'का',
    matchedTitle: 'सीधे पात्र योजनाएं (Direct Match)',
    needsInfoTitle: 'दफ्तर सत्यापन / अतिरिक्त जानकारी आवश्यक योजनाएं',
    repeatBtn: 'सवाल दोबारा सुनें',
    skipBtn: 'छोड़ें',
    restartBtn: 'दोबारा जांचें / रीसेट',
    listeningHint: 'माइक दबाकर बोलकर जवाब दें:',
    readingNotice: 'योजनाओं की पात्रता जांची जा रही है…',
    noSchemes: 'सीधा कोई मैच नहीं मिला। कृपया नजदीकी सीएससी या ग्राम पंचायत केंद्र पर संपर्क करें।',
    stateTopUp: 'राज्य टॉप-अप: आपके राज्य में अतिरिक्त बोनस या सब्सिडी भी मिल सकती है।',
    howToApply: 'आवेदन कैसे और कहाँ करें',
    docsNeeded: 'जरूरी दस्तावेज',
    helpline: 'हेल्पलाइन',
    officialPortal: 'आधिकारिक पोर्टल',
    voiceReaderGuide: 'ऑडियो नियंत्रित करने के लिए आगे, दोबारा, पीछे या रुको बोलें।',
    searchPlaceholder: 'खोजें: जैसे पेंशन, किसान लोन, बेटी की पढ़ाई, घर…',
    searchMic: 'बोलकर खोजें',
    whoFor: 'यह किसके लिए है?',
    whatNeed: 'आपको क्या चाहिए?',
    category: 'श्रेणी',
    allCategories: 'सभी श्रेणियां',
    clearAll: 'फ़िल्टर हटाएं',
    whoCanGet: 'कौन ले सकता है:',
    backBtn: 'पीछे',
    keepBtn: 'यही उत्तर रखें',
    yourAnswers: 'आपके उत्तर',
    changeBtn: 'बदलें',
    notAnswered: 'जवाब नहीं दिया',
    yourAnswerNow: 'आपका उत्तर:',
    showDetails: 'आवेदन कैसे करें और दस्तावेज़',
    hideDetails: 'विवरण छिपाएं',
    resultsCount: (n) => `${n} योजनाएं मिलीं`,
    noResults: 'इन विकल्पों से कोई योजना नहीं मिली। कोई फ़िल्टर हटाकर या आसान शब्द से खोजें।',
  },
  ta: {
    badge: '🏛 மத்திய மற்றும் மாநில அரசு நலத்திட்டங்கள்',
    title: 'உங்களுக்கும் உங்கள் குடும்பத்திற்குமான அரசு திட்டங்கள்',
    subtitle: '8 பிரிவுகளில் திட்டங்களை காண்க அல்லது 5 எளிய குரல் கேள்விகளுக்கு பதிலளித்து தகுதியை அறியவும்.',
    tabWizard: '🎙 "எனக்கு என்ன கிடைக்கும்?" குரல் வழிகாட்டி',
    tabBrowse: '📂 8 பிரிவுகளின் கீழ் காண்க',
    step: 'கேள்வி',
    of: 'ல்',
    matchedTitle: 'நேரடி தகுதி வாய்ந்த திட்டங்கள் (Direct Match)',
    needsInfoTitle: 'அலுவலக சரிபார்ப்பு தேவைப்படும் திட்டங்கள்',
    repeatBtn: 'மீண்டும் கேட்க',
    skipBtn: 'தவிர்க்க',
    restartBtn: 'மீண்டும் சரிபார்க்க',
    listeningHint: 'மைக் அழுத்தி உங்கள் பதிலை சொல்லுங்கள்:',
    readingNotice: 'திட்டங்கள் சரிபார்க்கப்படுகின்றன…',
    noSchemes: 'நேரடி திட்டங்கள் கிடைக்கவில்லை. கிராம சேவை மையத்தை (CSC) அணுகவும்.',
    stateTopUp: 'மாநில கூடுதல் உதவி: உங்கள் மாநிலத்தில் கூடுதல் போனஸ் அல்லது மானியம் கிடைக்கலாம்.',
    howToApply: 'விண்ணப்பிக்கும் முறை',
    docsNeeded: 'தேவையான ஆவணங்கள்',
    helpline: 'உதவி எண்',
    officialPortal: 'அதிகாரப்பூர்வ இணையதளம்',
    voiceReaderGuide: 'அடுத்து, மீண்டும், பின்னால், நிறுத்து என குரல் கட்டளைகள் மூலம் இயக்கலாம்.',
    searchPlaceholder: 'தேடுங்கள்: எ.கா. ஓய்வூதியம், விவசாயக் கடன், பெண் கல்வி, வீடு…',
    searchMic: 'பேசி தேடுங்கள்',
    whoFor: 'இது யாருக்கு?',
    whatNeed: 'உங்களுக்கு என்ன தேவை?',
    category: 'வகை',
    allCategories: 'அனைத்து வகைகள்',
    clearAll: 'வடிகட்டிகளை நீக்கு',
    whoCanGet: 'யார் பெறலாம்:',
    backBtn: 'பின்செல்',
    keepBtn: 'இந்தப் பதிலை வைத்துக்கொள்',
    yourAnswers: 'உங்கள் பதில்கள்',
    changeBtn: 'மாற்று',
    notAnswered: 'பதில் இல்லை',
    yourAnswerNow: 'உங்கள் பதில்:',
    showDetails: 'விண்ணப்பிக்கும் முறை & ஆவணங்கள்',
    hideDetails: 'விவரங்களை மறை',
    resultsCount: (n) => `${n} திட்டங்கள் கிடைத்தன`,
    noResults: 'இந்த தேர்வுகளுக்கு திட்டம் இல்லை. ஒரு வடிகட்டியை நீக்கவும் அல்லது எளிய சொல்லில் தேடவும்.',
  },
};

const PROFILE_KEY = {
  occupation: 'occupation',
  gender: 'gender',
  age: 'age',
  bank_account: 'has_bank_account',
  bpl_card: 'is_bpl_or_low_income',
};

const SHORT_NAMES = {
  occupation: { en: 'Work', hi: 'काम', ta: 'வேலை' },
  gender: { en: 'Gender', hi: 'लिंग', ta: 'பாலினம்' },
  age: { en: 'Age', hi: 'उम्र', ta: 'வயது' },
  bank_account: { en: 'Bank account', hi: 'बैंक खाता', ta: 'வங்கிக் கணக்கு' },
  bpl_card: { en: 'BPL / ration card', hi: 'बीपीएल / राशन कार्ड', ta: 'BPL / குடும்ப அட்டை' },
};

// Spoken navigation in the question wizard
const BACK_WORDS = ['back', 'go back', 'previous', 'peeche', 'piche', 'wapas', 'पीछे', 'वापस', 'पिछला', 'பின்னால்', 'பின்செல்', 'முந்தைய'];
const SKIP_WORDS = ['skip', 'next', 'chhodo', 'chodo', 'aage', 'छोड़ें', 'छोड़ो', 'अगला', 'आगे', 'தவிர்', 'தவிர்க்க', 'அடுத்து'];

function wizardCommand(text) {
  const clean = (text || '').toLowerCase().replace(/[.,!?।]/g, '').trim();
  if (BACK_WORDS.includes(clean)) return 'back';
  if (SKIP_WORDS.includes(clean)) return 'skip';
  return null;
}

function answerLabel(question, value) {
  if (value === undefined || value === null) return null;
  const opt = question.options.find((o) => o.value === value);
  if (opt) return opt.label;
  return String(value); // e.g. an age spoken as a number
}

const WIZARD_QUESTIONS = [
  {
    id: 'occupation',
    text: {
      en: 'What is your main work or occupation? Farmer, laborer, small business, student, or unemployed?',
      hi: 'आप क्या काम करते हैं? किसान, मज़दूर, छोटा व्यापार, छात्र या कोई काम नहीं?',
      ta: 'நீங்கள் என்ன வேலை செய்கிறீர்கள்? விவசாயி, கூலித் தொழிலாளி, வியாபாரம், மாணவர் அல்லது வேலையில்லை?',
    },
    options: [
      { label: '🌾 Farmer (किसान / விவசாயி)', value: 'farmer' },
      { label: '🔨 Daily Wage Laborer (मज़दूर / கூலி)', value: 'laborer' },
      { label: '💼 Small Business / Self-Employed (व्यापार)', value: 'self_employed' },
      { label: '🎓 Student / Youth (छात्र / மாணவர்)', value: 'student' },
      { label: '🏠 Homemaker / Unemployed (गृहणी / குடும்பத்தலைவி)', value: 'unemployed' },
    ],
  },
  {
    id: 'gender',
    text: {
      en: 'What is your gender? Female, male, or other?',
      hi: 'आपका लिंग क्या है? महिला, पुरुष, या अन्य?',
      ta: 'உங்கள் பாலினம் என்ன? பெண், ஆண், அல்லது மற்றவையா?',
    },
    options: [
      { label: '👩 Female (महिला / பெண்)', value: 'female' },
      { label: '👨 Male (पुरुष / ஆண்)', value: 'male' },
      { label: '⚧ Other (अन्य / மற்றவை)', value: 'other' },
    ],
  },
  {
    id: 'age',
    text: {
      en: 'What is your age? For example 25, 45, or 65?',
      hi: 'आपकी उम्र कितनी है? जैसे 25, 45, या 65 वर्ष?',
      ta: 'உங்கள் வயது என்ன? உதாரணத்திற்கு 25, 45, அல்லது 65?',
    },
    options: [
      { label: '👧 Below 18 (18 से कम)', value: 16 },
      { label: '👩 18 - 59 Working Age (18 से 59 वर्ष)', value: 35 },
      { label: '👵 60+ Senior Citizen (60+ वरिष्ठ नागरिक)', value: 65 },
    ],
  },
  {
    id: 'bank_account',
    text: {
      en: 'Do you have an active bank account for direct welfare cash transfers? Yes or no?',
      hi: 'क्या आपका बैंक खाता है ताकि सरकारी पैसा सीधे मिल सके? हाँ या नहीं?',
      ta: 'அரசு உதவித்தொகை நேரடியாக வர வங்கி கணக்கு உள்ளதா? ஆம் அல்லது இல்லை?',
    },
    options: [
      { label: '✓ Yes, I have bank account (हाँ / ஆம்)', value: true },
      { label: '✗ No bank account yet (नहीं / இல்லை)', value: false },
    ],
  },
  {
    id: 'bpl_card',
    text: {
      en: 'Do you have a BPL or Priority Ration Card? Yes or no?',
      hi: 'क्या आपके पास बीपीएल या राशन कार्ड है? हाँ या नहीं?',
      ta: 'உங்களிடம் பிபிஎல் (BPL) அல்லது குடும்ப அட்டை உள்ளதா? ஆம் அல்லது இல்லை?',
    },
    options: [
      { label: '✓ Yes, have BPL Ration Card (हाँ / ஆம்)', value: true },
      { label: '✗ No (नहीं / இல்லை)', value: false },
    ],
  },
];

export default function Schemes() {
  const { language } = useSession();
  const lang = language === 'hi' || language === 'ta' ? language : 'en';
  const t = UI_TEXT[lang];

  const { speak, listen, stopListening, isListening, isSpeaking, stopSpeaking, transcript, error: speechError } = useSpeech(lang);

  const [activeTab, setActiveTab] = useState('wizard'); // wizard | browse
  const [stepIndex, setStepIndex] = useState(0);
  const [profile, setProfile] = useState({});
  const [phase, setPhase] = useState('question'); // question | results | loading
  const [matchedSchemes, setMatchedSchemes] = useState([]);
  const [needsInfoSchemes, setNeedsInfoSchemes] = useState([]);
  const [groups, setGroups] = useState([]);
  const [selectedGroup, setSelectedGroup] = useState(null);
  const [browseSchemes, setBrowseSchemes] = useState([]);
  const [filterOptions, setFilterOptions] = useState({ audiences: [], needs: [] });
  const [audience, setAudience] = useState(null);
  const [need, setNeed] = useState(null);
  const [searchText, setSearchText] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const [browseLoading, setBrowseLoading] = useState(false);
  const [expandedId, setExpandedId] = useState(null);
  const [speakingSchemeId, setSpeakingSchemeId] = useState(null);
  const [returnToResults, setReturnToResults] = useState(false); // editing one answer from the results page

  // Load 8 Scheme Groups on Mount
  useEffect(() => {
    fetchSchemeGroups(lang)
      .then((data) => {
        setGroups(data);
        if (data.length > 0 && !selectedGroup) {
          setSelectedGroup(data[0].id);
        }
      })
      .catch((err) => console.warn('Could not load scheme groups:', err));
  }, [lang]);

  // Load "Who is it for?" / "What do you need?" options in the current language
  useEffect(() => {
    fetchSchemeFilters(lang)
      .then((data) => setFilterOptions(data))
      .catch((err) => console.warn('Could not load scheme filters:', err));
  }, [lang]);

  // Wait until typing pauses before searching
  useEffect(() => {
    const timer = setTimeout(() => setSearchQuery(searchText.trim()), 350);
    return () => clearTimeout(timer);
  }, [searchText]);

  const hasFinderFilters = Boolean(audience || need || searchQuery);

  // Load Schemes when category / audience / need / search changes
  useEffect(() => {
    if (activeTab !== 'browse' || !(selectedGroup || hasFinderFilters)) return undefined;
    let cancelled = false;
    setBrowseLoading(true);
    fetchSchemes(selectedGroup, lang, { audience, need, q: searchQuery })
      .then((data) => { if (!cancelled) setBrowseSchemes(data); })
      .catch((err) => console.warn('Could not load schemes:', err))
      .finally(() => { if (!cancelled) setBrowseLoading(false); });
    return () => { cancelled = true; };
  }, [activeTab, selectedGroup, lang, audience, need, searchQuery, hasFinderFilters]);

  // Picking who / what searches across every category
  const pickAudience = (id) => { setAudience((cur) => (cur === id ? null : id)); setSelectedGroup(null); };
  const pickNeed = (id) => { setNeed((cur) => (cur === id ? null : id)); setSelectedGroup(null); };
  const clearFinder = () => {
    setAudience(null);
    setNeed(null);
    setSearchText('');
    setSearchQuery('');
    if (groups.length > 0) setSelectedGroup(groups[0].id);
  };

  const handleVoiceSearch = async () => {
    stopSpeaking();
    playListenChime();
    try {
      const text = await listen();
      if (text && text.trim()) {
        setSearchText(text.trim());
        setSearchQuery(text.trim());
        setSelectedGroup(null);
      }
    } catch (err) {
      console.warn('Voice search failed:', err);
    }
  };

  // Read wizard question aloud when step changes
  useEffect(() => {
    if (activeTab === 'wizard' && phase === 'question') {
      const q = WIZARD_QUESTIONS[stepIndex];
      if (q) {
        speak(q.text[lang]);
      }
    }
  }, [stepIndex, phase, activeTab, lang]);

  // Execute deterministic 5-point match
  const executeMatch = useCallback(
    async (finalProfile) => {
      setPhase('loading');
      try {
        const res = await matchSchemes(finalProfile, lang);
        setMatchedSchemes(res.matched_schemes || []);
        setNeedsInfoSchemes(res.needs_more_info_schemes || []);
        setPhase('results');
        playSuccessChime();
        if (res.explanation_audio_text) {
          speak(res.explanation_audio_text);
        }
      } catch (err) {
        console.warn('Match request failed:', err);
        setPhase('results');
      }
    },
    [lang, speak]
  );

  const advance = (updated) => {
    if (returnToResults) {
      setReturnToResults(false);
      executeMatch(updated);
    } else if (stepIndex + 1 < WIZARD_QUESTIONS.length) {
      setStepIndex(stepIndex + 1);
    } else {
      executeMatch(updated);
    }
  };

  const handleBack = () => {
    stopSpeaking();
    if (stepIndex > 0) setStepIndex(stepIndex - 1);
  };

  // Skip = don't use this answer
  const handleSkip = () => {
    stopSpeaking();
    const updated = { ...profile };
    delete updated[PROFILE_KEY[WIZARD_QUESTIONS[stepIndex].id]];
    setProfile(updated);
    advance(updated);
  };

  const editAnswer = (idx) => {
    stopSpeaking();
    setReturnToResults(true);
    setStepIndex(idx);
    setPhase('question');
  };

  // Voice Question Answer Handler
  const handleVoiceAnswer = async () => {
    try {
      playListenChime();
      const text = await listen();
      if (!text || !text.trim()) return;

      const command = wizardCommand(text);
      if (command === 'back') {
        handleBack();
        return;
      }
      if (command === 'skip') {
        handleSkip();
        return;
      }

      const lower = text.toLowerCase();
      let updated = { ...profile };

      if (stepIndex === 0) {
        if (lower.includes('farm') || lower.includes('kisan') || lower.includes('khet') || lower.includes('விவசாயி')) {
          updated.occupation = 'farmer';
        } else if (lower.includes('labour') || lower.includes('mazdoor') || lower.includes('coolie') || lower.includes('கூலி')) {
          updated.occupation = 'laborer';
        } else if (lower.includes('business') || lower.includes('dukaan') || lower.includes('vyapar') || lower.includes('வியாபாரம்')) {
          updated.occupation = 'self_employed';
        } else if (lower.includes('student') || lower.includes('padhai') || lower.includes('छात्र') || lower.includes('மாணவர்')) {
          updated.occupation = 'student';
        } else {
          updated.occupation = 'unemployed';
        }
      } else if (stepIndex === 1) {
        if (lower.includes('female') || lower.includes('woman') || lower.includes('mahila') || lower.includes('aurat') || lower.includes('பெண்')) {
          updated.gender = 'female';
        } else if (lower.includes('other') || lower.includes('trans')) {
          updated.gender = 'other';
        } else {
          updated.gender = 'male';
        }
      } else if (stepIndex === 2) {
        const numMatch = lower.match(/\d+/);
        if (numMatch) {
          updated.age = parseInt(numMatch[0], 10);
        } else if (lower.includes('senior') || lower.includes('old') || lower.includes('बुजुर्ग') || lower.includes('मुதிய')) {
          updated.age = 65;
        } else {
          updated.age = 35;
        }
      } else if (stepIndex === 3) {
        if (lower.includes('no') || lower.includes('nahi') || lower.includes('illai') || lower.includes('இல்லை')) {
          updated.has_bank_account = false;
        } else {
          updated.has_bank_account = true;
        }
      } else if (stepIndex === 4) {
        if (lower.includes('yes') || lower.includes('haan') || lower.includes('aama') || lower.includes('ஆம்') || lower.includes('rashan') || lower.includes('bpl')) {
          updated.is_bpl_or_low_income = true;
        } else {
          updated.is_bpl_or_low_income = false;
        }
      }

      setProfile(updated);
      playSuccessChime();
      advance(updated);
    } catch (err) {
      console.warn('Voice answer error:', err);
    }
  };

  const handleOptionSelect = async (val) => {
    let updated = { ...profile };
    const qId = WIZARD_QUESTIONS[stepIndex].id;

    if (qId === 'occupation') updated.occupation = val;
    else if (qId === 'gender') updated.gender = val;
    else if (qId === 'age') updated.age = val;
    else if (qId === 'bank_account') updated.has_bank_account = val;
    else if (qId === 'bpl_card') updated.is_bpl_or_low_income = val;

    setProfile(updated);
    advance(updated);
  };

  const handleSpeakScheme = (scheme) => {
    if (isSpeaking && speakingSchemeId === scheme.scheme_id) {
      stopSpeaking();
      setSpeakingSchemeId(null);
      return;
    }
    setSpeakingSchemeId(scheme.scheme_id);
    const textToSpeak = scheme.tts_audio_text || `${scheme.name}. ${scheme.benefit_summary}. ${scheme.who_can_get}`;
    speak(textToSpeak, () => setSpeakingSchemeId(null));
  };

  const handleReset = () => {
    setReturnToResults(false);
    setProfile({});
    setStepIndex(0);
    setPhase('question');
    setMatchedSchemes([]);
    setNeedsInfoSchemes([]);
  };

  return (
    <div className="container" style={{ paddingBottom: 60, maxWidth: 960, margin: '0 auto' }}>
      {/* Header */}
      <div className="page-header" style={{ textAlign: 'center', marginBottom: 24 }}>
        <div className="badge badge-amber" style={{ marginBottom: 10, fontSize: 13, padding: '6px 16px' }}>
          {t.badge}
        </div>
        <h1 className="page-title" style={{ fontSize: 32, fontWeight: 900, color: '#0f172a' }}>
          {t.title}
        </h1>
        <p style={{ fontSize: 16, maxWidth: 680, margin: '8px auto 20px', color: '#475569', lineHeight: 1.4 }}>
          {t.subtitle}
        </p>

        {/* Tab Switcher */}
        <div style={{ display: 'inline-flex', gap: 8, background: '#f1f5f9', padding: '6px', borderRadius: 30, border: '1.5px solid #cbd5e1' }}>
          <button
            type="button"
            onClick={() => setActiveTab('wizard')}
            style={{
              padding: '10px 24px',
              borderRadius: 24,
              border: 'none',
              background: activeTab === 'wizard' ? '#0284c7' : 'transparent',
              color: activeTab === 'wizard' ? '#ffffff' : '#334155',
              fontSize: 15,
              fontWeight: 800,
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: 8,
              transition: 'all 0.2s ease',
            }}
          >
            <Sparkles size={18} /> {t.tabWizard}
          </button>
          <button
            type="button"
            onClick={() => setActiveTab('browse')}
            style={{
              padding: '10px 24px',
              borderRadius: 24,
              border: 'none',
              background: activeTab === 'browse' ? '#0284c7' : 'transparent',
              color: activeTab === 'browse' ? '#ffffff' : '#334155',
              fontSize: 15,
              fontWeight: 800,
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: 8,
              transition: 'all 0.2s ease',
            }}
          >
            <Filter size={18} /> {t.tabBrowse}
          </button>
        </div>
      </div>

      {/* ── TAB 1: 5-POINT VOICE WIZARD ── */}
      {activeTab === 'wizard' && (
        <div>
          {phase === 'loading' && (
            <div style={{ textAlign: 'center', padding: '60px 20px' }}>
              <div className="loader" style={{ width: 52, height: 52, margin: '0 auto 20px', borderWidth: 4 }} />
              <h2 style={{ fontSize: 22, fontWeight: 800, color: '#0f172a' }}>{t.readingNotice}</h2>
            </div>
          )}

          {phase === 'question' && (
            <motion.div initial={{ opacity: 0, y: 15 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.3 }}>
              <div
                className="glass-card question-panel"
                style={{
                  padding: '36px 28px',
                  borderRadius: 24,
                  border: '2px solid #e2e8f0',
                  background: '#ffffff',
                  boxShadow: '0 8px 30px rgba(0,0,0,0.06)',
                  textAlign: 'center',
                  maxWidth: 680,
                  margin: '0 auto',
                }}
              >
                <div style={{ fontSize: 13, fontWeight: 800, color: '#0284c7', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 8 }}>
                  {t.step} {stepIndex + 1} {t.of} {WIZARD_QUESTIONS.length}
                </div>

                <h2 style={{ fontSize: 24, fontWeight: 800, margin: '8px 0 20px', color: '#1e293b', lineHeight: 1.4 }}>
                  {WIZARD_QUESTIONS[stepIndex].text[lang]}
                </h2>

                {/* Real-time speech transcript box */}
                <div
                  style={{
                    minHeight: 52,
                    fontSize: 16,
                    fontWeight: 600,
                    margin: '16px auto',
                    maxWidth: 500,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    background: transcript ? '#eff6ff' : '#f8fafc',
                    border: transcript ? '2px solid #3b82f6' : '1.5px dashed #cbd5e1',
                    borderRadius: 14,
                    padding: '10px 16px',
                    color: transcript ? '#1e3a8a' : '#94a3b8',
                  }}
                >
                  {transcript || t.listeningHint}
                </div>

                {/* Big Voice Button */}
                <VoiceButton
                  isListening={isListening}
                  isSpeaking={isSpeaking}
                  onClick={isListening ? stopListening : handleVoiceAnswer}
                  language={lang}
                  size="large"
                  error={speechError}
                />

                {/* Answer already given (came back with Back or Change) */}
                {answerLabel(WIZARD_QUESTIONS[stepIndex], profile[PROFILE_KEY[WIZARD_QUESTIONS[stepIndex].id]]) && (
                  <div style={{ marginTop: 18, fontSize: 15, color: '#14532d', background: '#f0fdf4', border: '1.5px solid #86efac', borderRadius: 12, padding: '8px 14px', display: 'inline-block' }}>
                    {t.yourAnswerNow} <strong>{answerLabel(WIZARD_QUESTIONS[stepIndex], profile[PROFILE_KEY[WIZARD_QUESTIONS[stepIndex].id]])}</strong>
                  </div>
                )}

                {/* Tap-able Large Option Buttons */}
                <div style={{ marginTop: 24, display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 12 }}>
                  {WIZARD_QUESTIONS[stepIndex].options.map((opt, idx) => {
                    const chosen = profile[PROFILE_KEY[WIZARD_QUESTIONS[stepIndex].id]] === opt.value;
                    return (
                    <button
                      key={idx}
                      type="button"
                      aria-pressed={chosen}
                      onClick={() => handleOptionSelect(opt.value)}
                      style={{
                        padding: '14px 16px',
                        fontSize: 15,
                        fontWeight: 700,
                        borderRadius: 14,
                        border: chosen ? '2px solid #16a34a' : '1.5px solid #cbd5e1',
                        background: chosen ? '#dcfce7' : '#f8fafc',
                        color: '#1e293b',
                        cursor: 'pointer',
                        transition: 'transform 0.1s ease',
                      }}
                      onMouseEnter={(e) => (e.currentTarget.style.transform = 'scale(1.02)')}
                      onMouseLeave={(e) => (e.currentTarget.style.transform = 'scale(1)')}
                    >
                      {chosen ? '✓ ' : ''}{opt.label}
                    </button>
                    );
                  })}
                </div>

                {/* Controls */}
                <div style={{ display: 'flex', gap: 12, justifyContent: 'center', marginTop: 24, flexWrap: 'wrap' }}>
                  <button
                    type="button"
                    className="btn btn-ghost"
                    style={{ fontSize: 13, padding: '8px 18px', borderRadius: 20 }}
                    onClick={handleBack}
                    disabled={stepIndex === 0}
                  >
                    <ArrowLeft size={15} /> {t.backBtn}
                  </button>
                  <button
                    type="button"
                    className="btn btn-ghost"
                    style={{ fontSize: 13, padding: '8px 18px', borderRadius: 20 }}
                    onClick={() => speak(WIZARD_QUESTIONS[stepIndex].text[lang])}
                  >
                    <Volume2 size={15} /> {t.repeatBtn}
                  </button>
                  <button
                    type="button"
                    className="btn btn-ghost"
                    style={{ fontSize: 13, padding: '8px 18px', borderRadius: 20 }}
                    onClick={handleSkip}
                  >
                    {t.skipBtn} →
                  </button>
                  {profile[PROFILE_KEY[WIZARD_QUESTIONS[stepIndex].id]] !== undefined && (
                    <button
                      type="button"
                      className="btn btn-ghost"
                      style={{ fontSize: 13, padding: '8px 18px', borderRadius: 20, color: '#15803d' }}
                      onClick={() => advance(profile)}
                    >
                      <CheckCircle2 size={15} /> {t.keepBtn} →
                    </button>
                  )}
                </div>
              </div>
            </motion.div>
          )}

          {phase === 'results' && (
            <motion.div initial={{ opacity: 0, y: 15 }} animate={{ opacity: 1, y: 0 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24, flexWrap: 'wrap', gap: 12 }}>
                <div>
                  <h2 style={{ fontSize: 26, fontWeight: 900, margin: 0, color: '#0f172a' }}>
                    ✓ {matchedSchemes.length} {t.matchedTitle}
                  </h2>
                  <div style={{ fontSize: 13, color: '#64748b', marginTop: 4 }}>
                    {t.voiceReaderGuide}
                  </div>
                </div>
                <button
                  type="button"
                  className="btn btn-primary"
                  style={{ fontSize: 14, padding: '10px 24px', borderRadius: 24, fontWeight: 800 }}
                  onClick={handleReset}
                >
                  <RefreshCw size={16} /> {t.restartBtn}
                </button>
              </div>

              {/* Your answers — check and change */}
              <div className="wizard-answers" style={{ background: '#f8fafc', border: '1.5px solid #e2e8f0', borderRadius: 16, padding: '14px 18px', marginBottom: 24 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8, gap: 10, flexWrap: 'wrap' }}>
                  <strong style={{ fontSize: 16, color: '#0f172a' }}>{t.yourAnswers}</strong>
                  <button
                    type="button"
                    className="btn btn-ghost"
                    style={{ fontSize: 13, padding: '6px 14px', borderRadius: 20 }}
                    onClick={() => { stopSpeaking(); setReturnToResults(false); setStepIndex(WIZARD_QUESTIONS.length - 1); setPhase('question'); }}
                  >
                    <ArrowLeft size={15} /> {t.backBtn}
                  </button>
                </div>
                {WIZARD_QUESTIONS.map((q, idx) => {
                  const label = answerLabel(q, profile[PROFILE_KEY[q.id]]);
                  return (
                    <div key={q.id} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 10, padding: '6px 0', borderTop: idx ? '1px solid #e2e8f0' : 'none' }}>
                      <div style={{ fontSize: 14, color: '#334155' }}>
                        <span style={{ fontWeight: 700 }}>{SHORT_NAMES[q.id][lang]}:</span>{' '}
                        <span style={{ color: label ? '#0f172a' : '#94a3b8' }}>{label || t.notAnswered}</span>
                      </div>
                      <button
                        type="button"
                        data-edit={q.id}
                        onClick={() => editAnswer(idx)}
                        style={{ display: 'inline-flex', alignItems: 'center', gap: 4, border: '1.5px solid #cbd5e1', background: '#ffffff', borderRadius: 10, padding: '4px 10px', fontSize: 13, fontWeight: 700, cursor: 'pointer', color: '#0284c7' }}
                      >
                        <Pencil size={13} /> {t.changeBtn}
                      </button>
                    </div>
                  );
                })}
              </div>

              {/* Directly Matched Cards */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: 18, marginBottom: 36 }}>
                {matchedSchemes.map((scheme) => (
                  <SchemeDetailCard
                    key={scheme.scheme_id}
                    scheme={scheme}
                    lang={lang}
                    t={t}
                    isSpeaking={isSpeaking && speakingSchemeId === scheme.scheme_id}
                    onSpeak={() => handleSpeakScheme(scheme)}
                    isExpanded={expandedId === scheme.scheme_id}
                    onToggleExpand={() => setExpandedId(expandedId === scheme.scheme_id ? null : scheme.scheme_id)}
                  />
                ))}
              </div>

              {/* Schemes Requiring Office Verification */}
              {needsInfoSchemes.length > 0 && (
                <div style={{ marginTop: 32 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 18 }}>
                    <AlertCircle size={22} style={{ color: '#d97706' }} />
                    <h3 style={{ fontSize: 22, fontWeight: 800, margin: 0, color: '#92400e' }}>
                      {t.needsInfoTitle} ({needsInfoSchemes.length})
                    </h3>
                  </div>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 18 }}>
                    {needsInfoSchemes.map((scheme) => (
                      <SchemeDetailCard
                        key={scheme.scheme_id}
                        scheme={scheme}
                        lang={lang}
                        t={t}
                        isSpeaking={isSpeaking && speakingSchemeId === scheme.scheme_id}
                        onSpeak={() => handleSpeakScheme(scheme)}
                        isExpanded={expandedId === scheme.scheme_id}
                        onToggleExpand={() => setExpandedId(expandedId === scheme.scheme_id ? null : scheme.scheme_id)}
                      />
                    ))}
                  </div>
                </div>
              )}
            </motion.div>
          )}
        </div>
      )}

      {/* ── TAB 2: BROWSE BY 8 CATEGORIES ── */}
      {activeTab === 'browse' && (
        <div>
          {/* Search (type or speak, in any of the 3 languages) */}
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 10, marginBottom: 18 }}>
            <div style={{ position: 'relative', flex: '1 1 260px' }}>
              <Search size={20} style={{ position: 'absolute', left: 14, top: '50%', transform: 'translateY(-50%)', color: '#64748b' }} />
              <input
                type="text"
                value={searchText}
                onChange={(e) => { setSearchText(e.target.value); if (e.target.value.trim()) setSelectedGroup(null); }}
                placeholder={t.searchPlaceholder}
                aria-label={t.searchPlaceholder}
                style={{
                  width: '100%', boxSizing: 'border-box', padding: '14px 40px 14px 44px', fontSize: 16,
                  borderRadius: 14, border: '1.5px solid #cbd5e1', background: '#ffffff', color: '#0f172a',
                }}
              />
              {searchText && (
                <button
                  type="button"
                  onClick={() => { setSearchText(''); setSearchQuery(''); }}
                  aria-label={t.clearAll}
                  style={{ position: 'absolute', right: 10, top: '50%', transform: 'translateY(-50%)', border: 'none', background: 'none', cursor: 'pointer', color: '#64748b' }}
                >
                  <X size={18} />
                </button>
              )}
            </div>
            <button
              type="button"
              onClick={handleVoiceSearch}
              title={t.searchMic}
              aria-label={t.searchMic}
              style={{
                display: 'flex', alignItems: 'center', gap: 8, padding: '12px 18px', borderRadius: 14, border: 'none',
                background: isListening ? '#dc2626' : '#0284c7', color: '#ffffff', fontWeight: 800, fontSize: 14, cursor: 'pointer',
              }}
            >
              <Mic size={20} />
              <span>{isListening ? (transcript || '…') : t.searchMic}</span>
            </button>
          </div>

          {/* Who is it for? / What do you need? */}
          {[
            { key: 'who', title: t.whoFor, options: filterOptions.audiences, value: audience, pick: pickAudience, color: '#7c3aed' },
            { key: 'what', title: t.whatNeed, options: filterOptions.needs, value: need, pick: pickNeed, color: '#059669' },
          ].map((row) => (
            <div key={row.key} style={{ marginBottom: 16 }}>
              <div style={{ fontSize: 14, fontWeight: 800, color: '#334155', marginBottom: 8 }}>{row.title}</div>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
                {row.options.filter((o) => o.count > 0).map((o) => {
                  const isSel = row.value === o.id;
                  return (
                    <button
                      key={o.id}
                      type="button"
                      data-filter={`${row.key}:${o.id}`}
                      onClick={() => row.pick(o.id)}
                      aria-pressed={isSel}
                      style={{
                        padding: '8px 14px', borderRadius: 999, fontSize: 14, fontWeight: 700, cursor: 'pointer',
                        border: isSel ? `2px solid ${row.color}` : '1.5px solid #cbd5e1',
                        background: isSel ? row.color : '#ffffff', color: isSel ? '#ffffff' : '#1e293b',
                      }}
                    >
                      {o.icon} {o.label} <span style={{ opacity: 0.7, fontWeight: 600 }}>({o.count})</span>
                    </button>
                  );
                })}
              </div>
            </div>
          ))}

          {/* 8 Category Pills */}
          <div style={{ fontSize: 14, fontWeight: 800, color: '#334155', marginBottom: 8 }}>{t.category}</div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 12, marginBottom: 20 }}>
            {hasFinderFilters && (
              <button
                type="button"
                onClick={() => setSelectedGroup(null)}
                style={{
                  padding: '14px 16px', borderRadius: 16, fontSize: 16, fontWeight: 800, textAlign: 'left', cursor: 'pointer',
                  border: !selectedGroup ? '2px solid #0284c7' : '1.5px solid #cbd5e1',
                  background: !selectedGroup ? '#0284c7' : '#ffffff', color: !selectedGroup ? '#ffffff' : '#1e293b',
                }}
              >
                {t.allCategories}
              </button>
            )}
            {groups.map((g) => {
              const isSel = selectedGroup === g.id;
              return (
                <button
                  key={g.id}
                  type="button"
                  onClick={() => setSelectedGroup(hasFinderFilters && isSel ? null : g.id)}
                  style={{
                    padding: '14px 16px',
                    borderRadius: 16,
                    border: isSel ? '2px solid #0284c7' : '1.5px solid #cbd5e1',
                    background: isSel ? '#0284c7' : '#ffffff',
                    color: isSel ? '#ffffff' : '#1e293b',
                    fontSize: 14,
                    fontWeight: 800,
                    textAlign: 'left',
                    cursor: 'pointer',
                    boxShadow: isSel ? '0 4px 14px rgba(2, 132, 199, 0.3)' : '0 2px 8px rgba(0,0,0,0.03)',
                    transition: 'all 0.15s ease',
                  }}
                >
                  <div style={{ fontSize: 16, marginBottom: 4 }}>{g.icon} {g.title || g.name}</div>
                  <div style={{ fontSize: 12, opacity: isSel ? 0.9 : 0.65 }}>
                    {g.description}
                  </div>
                </button>
              );
            })}
          </div>

          {/* Results count + clear */}
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 10, marginBottom: 14 }}>
            <div className="scheme-results-count" style={{ fontSize: 15, fontWeight: 800, color: '#0f172a' }}>
              {browseLoading ? '…' : t.resultsCount(browseSchemes.length)}
            </div>
            {hasFinderFilters && (
              <button
                type="button"
                onClick={clearFinder}
                style={{ display: 'flex', alignItems: 'center', gap: 6, border: '1.5px solid #cbd5e1', background: '#ffffff', borderRadius: 10, padding: '6px 12px', fontWeight: 700, cursor: 'pointer', color: '#334155' }}
              >
                <X size={16} /> {t.clearAll}
              </button>
            )}
          </div>
          {!browseLoading && browseSchemes.length === 0 && (
            <div style={{ padding: 20, borderRadius: 16, background: '#fff7ed', border: '1.5px solid #fed7aa', color: '#9a3412', fontWeight: 600, marginBottom: 18 }}>
              {t.noResults}
            </div>
          )}

          {/* Schemes in Selected Category */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 18 }}>
            {browseSchemes.map((scheme) => (
              <SchemeDetailCard
                key={scheme.scheme_id}
                scheme={scheme}
                lang={lang}
                t={t}
                isSpeaking={isSpeaking && speakingSchemeId === scheme.scheme_id}
                onSpeak={() => handleSpeakScheme(scheme)}
                isExpanded={expandedId === scheme.scheme_id}
                onToggleExpand={() => setExpandedId(expandedId === scheme.scheme_id ? null : scheme.scheme_id)}
              />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

/**
 * Individual Scheme Detail Card Component
 */
function SchemeDetailCard({ scheme, lang, t, isSpeaking, onSpeak, isExpanded, onToggleExpand }) {
  const isNeedsInfo = scheme.status === 'needs_more_info';

  return (
    <div
      className="glass-card"
      style={{
        padding: '24px',
        borderRadius: 20,
        border: isNeedsInfo ? '2px dashed #f59e0b' : '1.5px solid #cbd5e1',
        background: isNeedsInfo ? '#fffdf5' : '#ffffff',
        boxShadow: '0 4px 18px rgba(0,0,0,0.04)',
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 16, flexWrap: 'wrap' }}>
        <div style={{ flex: 1, minWidth: 260 }}>
          <div style={{ display: 'flex', gap: 8, alignItems: 'center', marginBottom: 6, flexWrap: 'wrap' }}>
            {scheme.short_name && (
              <span className="badge badge-primary" style={{ fontWeight: 800, fontSize: 12 }}>
                {scheme.short_name}
              </span>
            )}
            <span style={{ fontSize: 12, fontWeight: 700, color: '#64748b' }}>
              {scheme.ministry}
            </span>
          </div>

          <h3 style={{ fontSize: 22, fontWeight: 800, margin: '2px 0 8px', color: '#0f172a' }}>
            {scheme.name}
          </h3>
        </div>

        {/* Listen Button */}
        <button
          type="button"
          onClick={onSpeak}
          style={{
            background: isSpeaking ? '#fee2e2' : '#f1f5f9',
            color: isSpeaking ? '#dc2626' : '#0284c7',
            border: '1.5px solid #cbd5e1',
            borderRadius: 24,
            padding: '10px 18px',
            fontSize: 14,
            fontWeight: 800,
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: 6,
          }}
        >
          <Volume2 size={18} />
          <span>{isSpeaking ? 'Stop' : '🔊 ' + t.repeatBtn}</span>
        </button>
      </div>

      {/* Benefit Amount Callout Box */}
      <div
        style={{
          fontSize: 16,
          fontWeight: 700,
          color: '#15803d',
          background: '#f0fdf4',
          border: '1.5px solid #bbf7d0',
          padding: '12px 18px',
          borderRadius: 14,
          margin: '14px 0 10px',
        }}
      >
        💰 {scheme.benefit_summary}
      </div>

      {/* State Top-up Reminder */}
      {scheme.state_top_up_note && (
        <div
          style={{
            fontSize: 13,
            fontWeight: 600,
            color: '#b45309',
            background: '#fef3c7',
            padding: '8px 14px',
            borderRadius: 10,
            marginBottom: 12,
          }}
        >
          📌 {scheme.state_top_up_note}
        </div>
      )}

      {/* Who Can Get It */}
      <div style={{ fontSize: 14, color: '#334155', marginBottom: 12 }}>
        <strong>{t.whoCanGet || 'Who can get it:'}</strong> {scheme.who_can_get}
      </div>

      {/* Expandable How to Apply, Documents & Helplines */}
      {isExpanded && (
        <div style={{ background: '#f8fafc', padding: 18, borderRadius: 14, marginTop: 14, border: '1px solid #e2e8f0' }}>
          {/* How to Apply */}
          <div style={{ marginBottom: 14 }}>
            <div style={{ fontSize: 14, fontWeight: 800, color: '#1e293b', marginBottom: 6 }}>
              📍 {t.howToApply}:
            </div>
            <p style={{ fontSize: 14, color: '#475569', margin: 0, lineHeight: 1.5 }}>
              {scheme.how_to_apply}
            </p>
          </div>

          {/* Documents Needed */}
          {scheme.documents_needed && scheme.documents_needed.length > 0 && (
            <div style={{ marginBottom: 14 }}>
              <div style={{ fontSize: 14, fontWeight: 800, color: '#1e293b', marginBottom: 6 }}>
                📄 {t.docsNeeded}:
              </div>
              <ul style={{ margin: 0, paddingLeft: 20, fontSize: 14, color: '#475569', lineHeight: 1.5 }}>
                {scheme.documents_needed.map((doc, i) => (
                  <li key={i}>{doc}</li>
                ))}
              </ul>
            </div>
          )}

          {/* Contact & Links */}
          <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap', paddingTop: 10, borderTop: '1px solid #e2e8f0' }}>
            {scheme.helpline && (
              <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 13, fontWeight: 700, color: '#0284c7' }}>
                <Phone size={14} /> {t.helpline}: {scheme.helpline}
              </div>
            )}
            {scheme.website && (
              <a
                href={scheme.website}
                target="_blank"
                rel="noreferrer"
                style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 13, fontWeight: 700, color: '#059669', textDecoration: 'none' }}
              >
                <Globe size={14} /> {t.officialPortal}
              </a>
            )}
          </div>
        </div>
      )}

      {/* Expand / Collapse Button */}
      <div style={{ marginTop: 12 }}>
        <button
          type="button"
          onClick={onToggleExpand}
          style={{
            background: 'transparent',
            border: 'none',
            color: '#0284c7',
            fontSize: 14,
            fontWeight: 800,
            cursor: 'pointer',
            display: 'inline-flex',
            alignItems: 'center',
            gap: 4,
            padding: 0,
          }}
        >
          {isExpanded ? (
            <>
              <ChevronUp size={16} /> {t.hideDetails || 'Hide Details'}
            </>
          ) : (
            <>
              <ChevronDown size={16} /> {t.showDetails || 'How to Apply & Documents'}
            </>
          )}
        </button>
      </div>
    </div>
  );
}
