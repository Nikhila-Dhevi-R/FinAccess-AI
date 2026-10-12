import { useState, useCallback, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Upload,
  CheckCircle,
  Download,
  Volume2,
  CheckCircle2,
  XCircle,
  ShieldCheck,
  ArrowLeft,
  Edit3,
} from 'lucide-react';
import { VoiceButton } from '../components/VoiceButton';
import { ChallengePrompt } from '../components/ChallengePrompt';
import { PhoneVerify } from '../components/PhoneVerify';
import { useSpeech } from '../hooks/useSpeech';
import { useSession } from '../hooks/useSession';
import {
  uploadForm,
  createSession,
  getNextField,
  skipFormField,
  submitFieldAnswer,
  finalizeForm,
  resolveBackendUrl,
  createChallenge,
  fetchDemoTemplate,
  getOtpStatus,
} from '../api/client';

const UI_STRINGS = {
  en: {
    badge: '📄 Voice Form Fill',
    title: 'Fill Any Form by Speaking',
    subtitle: 'Upload a bank, pension, or welfare form — we extract questions and fill it for you.',
    dropText: 'Drop your form here or click to upload',
    dropSub: 'Supports PDF or scanned images (Bank account, Pension, Ration Card, PM-Kisan)',
    chooseBtn: 'Choose Form Document',
    demoBtn: '🏦 Try Sample Bank Form Demo',
    processingTitle: 'Reading your form with AI…',
    processingSub: 'Extracting fields and layout coordinates from your document',
    fieldsProgress: 'Fields',
    fieldOf: 'Field',
    yourAnswer: 'Your answer will appear here as you speak…',
    repeatBtn: 'Repeat Question',
    skipBtn: 'Skip Field',
    reAnswer: 'Re-answer this question',
    editAnswer: 'Update Value',
    formComplete: 'Form Review & Summary',
    allConfirmed: 'All questions have been answered. Please review before final submission.',
    downloadBtn: 'Download Completed Form PDF',
    generatingBtn: 'Generating PDF…',
    cantHear: "I didn't catch that. Please speak again clearly.",
    confirmSuccess: 'Got it! Moving to the next question.',
    // Green & Red Button labels
    confirmYes: 'Correct — Verify',
    confirmYesSub: 'Confirm answer & repeat security numbers',
    confirmNo: 'Wrong — Try Again',
    confirmNoSub: 'Clear & speak again',
    // Voice optional confirmation
    orSayVoice: 'Or tap mic & say "Yes" / "No"',
    voiceAffirmHint: 'Say "Yes" or "Correct" to confirm, or "No" to retry.',
    // Final Security Challenge
    finalChallengeBadge: '🔐 Final Security Verification',
    finalChallengeTitle: 'Voice Authorization & Submission',
    finalChallengeSub: 'Before generating your filled PDF, repeat these 4 security numbers to authorize submission.',
    proceedToFinalize: 'Authorize & Generate PDF',
    readyToFinalize: 'All 12 fields are confirmed. Click below to complete the one-time security voice verification.',
    reviewFields: 'Back to Field Review',
    interpretedAs: 'I understood:',
    writtenAs: 'Will be written on the form as:',
    backBtn: 'Back',
    currentAnswer: 'Current answer:',
    keepAnswer: 'Keep this answer',
    skippedLabel: 'Skipped — will be left blank',
    leftBlank: (n) => `${n} field${n === 1 ? ' is' : 's are'} skipped and will be left blank. Tap any field in the list to fill or change it.`,
    tapToChange: 'Tap a field in the list to check or change its answer.',
  },
  hi: {
    badge: '📄 बोलकर फॉर्म भरें',
    title: 'बोलकर कोई भी फॉर्म भरें',
    subtitle: 'बैंक, पेंशन या सरकारी फॉर्म अपलोड करें — हम सवाल पूछकर आपके लिए भरेंगे।',
    dropText: 'अपना फॉर्म यहाँ डालें या चुनने के लिए क्लिक करें',
    dropSub: 'पीडीएफ (PDF) या फोटो फॉर्म अपलोड करें (बैंक खाता, पेंशन, राशन कार्ड, पीएम किसान)',
    chooseBtn: 'फॉर्म दस्तावेज़ चुनें',
    demoBtn: '🏦 नमूना बैंक फॉर्म आज़माएं',
    processingTitle: 'दस्तावेज़ पढ़ा जा रहा है…',
    processingSub: 'फॉर्म से फ़ील्ड और सवाल निकाले जा रहे हैं',
    fieldsProgress: 'सवाल',
    fieldOf: 'प्रश्न',
    yourAnswer: 'बोलते ही आपका जवाब यहाँ दिखाई देगा…',
    repeatBtn: 'सवाल दोबारा सुनें',
    skipBtn: 'छोड़ें',
    reAnswer: 'इस सवाल का दोबारा जवाब दें',
    editAnswer: 'उत्तर बदलें',
    formComplete: 'फॉर्म समीक्षा व सारांश',
    allConfirmed: 'सभी प्रश्नों के उत्तर दे दिए गए हैं। अंतिम जमा से पहले समीक्षा करें।',
    downloadBtn: 'भरा हुआ फॉर्म (PDF) डाउनलोड करें',
    generatingBtn: 'पीडीएफ तैयार हो रहा है…',
    cantHear: 'आवाज़ स्पष्ट नहीं आई। कृपया दोबारा बोलें।',
    confirmSuccess: 'बहुत बढ़िया! अगला सवाल पूछते हैं।',
    // Green & Red Button labels
    confirmYes: 'सही — सत्यापित करें',
    confirmYesSub: 'उत्तर की पुष्टि करें और सुरक्षा अंक दोहराएँ',
    confirmNo: 'गलत है — दोबारा बोलें',
    confirmNoSub: 'मिटाएं और फिर से बोलें',
    // Voice optional confirmation
    orSayVoice: 'या माइक दबाकर "हाँ" / "ना" कहें',
    voiceAffirmHint: 'पुष्टि के लिए "हाँ" या "सही" बोलें, दोबारा बोलने के लिए "ना" बोलें।',
    // Final Security Challenge
    finalChallengeBadge: '🔐 अंतिम सुरक्षा सत्यापन',
    finalChallengeTitle: 'वॉइस ऑथराइजेशन एवं सबमिशन',
    finalChallengeSub: 'भरा हुआ PDF बनाने से पहले, सबमिशन की पुष्टि के लिए 4 सुरक्षा अंक बोलें।',
    proceedToFinalize: 'सत्यापित करें और पीडीएफ बनाएं',
    readyToFinalize: 'सभी विवरण भर गए हैं! एक बार के सुरक्षा वॉइस सत्यापन के लिए नीचे क्लिक करें।',
    reviewFields: 'विवरण दोबारा देखें',
    verifyPhoneBadge: '🔐 चरण 1: अपना मोबाइल नंबर सत्यापित करें',
    interpretedAs: 'समझा गया उत्तर:',
    writtenAs: 'फॉर्म पर अंग्रेज़ी में ऐसे लिखा जाएगा:',
    backBtn: 'पीछे',
    currentAnswer: 'अभी का उत्तर:',
    keepAnswer: 'यही उत्तर रखें',
    skippedLabel: 'छोड़ा गया — खाली रहेगा',
    leftBlank: (n) => `${n} सवाल छोड़े गए हैं और फॉर्म पर खाली रहेंगे। भरने या बदलने के लिए सूची में किसी भी सवाल को दबाएं।`,
    tapToChange: 'किसी उत्तर को जांचने या बदलने के लिए सूची में उस सवाल को दबाएं।',
  },
  ta: {
    badge: '📄 குரல் படிவம் நிரப்புதல்',
    title: 'பேசியே படிவத்தை நிரப்பவும்',
    subtitle: 'வங்கி அல்லது அரசு படிவத்தை பதிவேற்றவும் — கேள்விகளை கேட்டு நாங்களே நிரப்புவோம்.',
    dropText: 'படிவத்தை இங்கே பதிவேற்றவும்',
    dropSub: 'PDF அல்லது புகைப்பட படிவம் (வங்கி கணக்கு, ஓய்வூதியம், குடும்ப அட்டை)',
    chooseBtn: 'படிவத்தை தேர்ந்தெடுக்கவும்',
    demoBtn: '🏦 மாதிரி வங்கி படிவத்தை முயற்சிக்கவும்',
    processingTitle: 'படிவம் படிக்கப்படுகிறது…',
    processingSub: 'படிவத்தில் உள்ள கேள்விகள் பிரித்தெடுக்கப்படுகின்றன',
    fieldsProgress: 'கேள்விகள்',
    fieldOf: 'கேள்வி',
    yourAnswer: 'நீங்கள் பேசும்போது உங்கள் பதில் இங்கே தோன்றும்…',
    repeatBtn: 'கேள்வியை மீண்டும் கேட்க',
    skipBtn: 'தவிர்க்க',
    reAnswer: 'மீண்டும் பதிலளிக்க',
    editAnswer: 'பதிலை திருத்தவும்',
    formComplete: 'படிவ மதிப்பாய்வு',
    allConfirmed: 'அனைத்து கேள்விகளுக்கும் பதிலளிக்கப்பட்டது. பதிவிறக்கம் செய்ய சரிபார்க்கவும்.',
    downloadBtn: 'பூர்த்தி செய்த படிவத்தை (PDF) பதிவிறக்கவும்',
    generatingBtn: 'படிவம் தயாராகிறது…',
    cantHear: 'சரியாக கேட்கவில்லை. தயவுசெய்து மீண்டும் பேசவும்.',
    confirmSuccess: 'சரி! அடுத்த கேள்விக்கு செல்லலாம்.',
    // Green & Red Button labels
    confirmYes: 'சரி — சரிபார்க்கவும்',
    confirmYesSub: 'பதிலை உறுதிசெய்து பாதுகாப்பு எண்களை மீண்டும் கூறவும்',
    confirmNo: 'தவறு — மீண்டும் பேசவும்',
    confirmNoSub: 'அழித்துவிட்டு மீண்டும் பேசவும்',
    // Voice optional confirmation
    orSayVoice: 'அல்லது மைக் அழுத்தி "ஆம்" / "இல்லை" என கூறவும்',
    voiceAffirmHint: 'உறுதிப்படுத்த "ஆம்" அல்லது "சரி" எனவும், மீண்டும் பேச "இல்லை" எனவும் கூறவும்.',
    // Final Security Challenge
    finalChallengeBadge: '🔐 இறுதி பாதுகாப்பு சரிபார்ப்பு',
    finalChallengeTitle: 'குரல் உறுதிப்படுத்தல் & ஒப்புதல்',
    finalChallengeSub: 'நிரப்பப்பட்ட PDF உருவாக்கும் முன், சமர்ப்பிப்பை உறுதிப்படுத்த 4 பாதுகாப்பு எண்களைக் கூறவும்.',
    proceedToFinalize: 'சரிபார்த்து PDF ஐ உருவாக்கவும்',
    readyToFinalize: 'அனைத்து விவரங்களும் பூர்த்தியடைந்தன! இறுதி பாதுகாப்பு சரிபார்ப்புக்கு கிளிக் செய்யவும்.',
    reviewFields: 'விவரங்களை மதிப்பாய்வு செய்யவும்',
    verifyPhoneBadge: '🔐 படி 1: உங்கள் மொபைல் எண்ணைச் சரிபார்க்கவும்',
    interpretedAs: 'புரிந்துகொள்ளப்பட்ட பதில்:',
    writtenAs: 'படிவத்தில் ஆங்கிலத்தில் இவ்வாறு எழுதப்படும்:',
    backBtn: 'பின்செல்',
    currentAnswer: 'தற்போதைய பதில்:',
    keepAnswer: 'இந்தப் பதிலை வைத்துக்கொள்',
    skippedLabel: 'தவிர்க்கப்பட்டது — காலியாக இருக்கும்',
    leftBlank: (n) => `${n} கேள்விகள் தவிர்க்கப்பட்டன, படிவத்தில் காலியாக இருக்கும். நிரப்ப அல்லது மாற்ற பட்டியலில் உள்ள கேள்வியைத் தொடவும்.`,
    tapToChange: 'ஒரு பதிலைச் சரிபார்க்க அல்லது மாற்ற பட்டியலில் அந்தக் கேள்வியைத் தொடவும்.',
  },
};

// Keyword matcher for optional voice confirmation
const YES_KEYWORDS = [
  'yes', 'yeah', 'yup', 'correct', 'right', 'ok', 'okay', 'fine', 'confirm', 'good', 'true',
  'haan', 'ha', 'sahi', 'theek', 'thik', 'theek hai', 'thik hai', 'sahi hai', 'achha', 'ji haan',
  'हाँ', 'सही', 'ठीक', 'ठीक है', 'जी हाँ', 'अच्छा',
  'aama', 'aam', 'aamaa', 'seri', 'sari', 'serithan', 'sarithan', 'kandippa',
  'ஆம்', 'சரி', 'ஆமாம்', 'சரிதான்'
];

const NO_KEYWORDS = [
  'no', 'nope', 'nah', 'wrong', 'incorrect', 'change', 'retry', 're-answer', 'false',
  'nahi', 'nahin', 'na', 'galat', 'galt', 'badlo', 'punah',
  'नहीं', 'ना', 'गलत', 'बदलो',
  'illai', 'illa', 'thappu', 'marrru',
  'இல்லை', 'தவறு', 'இல்ல', 'மாற்று'
];

// Spoken navigation while a question is being asked
const BACK_WORDS = ['back', 'go back', 'previous', 'peeche', 'piche', 'pichla', 'wapas', 'पीछे', 'पिछला', 'वापस', 'பின்னால்', 'பின்செல்', 'முந்தைய', 'பின்'];
const SKIP_WORDS = ['skip', 'skip it', 'next', 'chhodo', 'chodo', 'aage', 'छोड़ें', 'छोड़ो', 'छोड़ दो', 'अगला', 'आगे', 'தவிர்', 'தவிர்க்க', 'அடுத்து', 'அடுத்தது'];

function navCommand(text) {
  const clean = (text || '').toLowerCase().replace(/[.,!?।]/g, '').trim();
  if (BACK_WORDS.includes(clean)) return 'back';
  if (SKIP_WORDS.includes(clean)) return 'skip';
  return null;
}

function isAffirmative(text) {
  if (!text) return false;
  const clean = text.toLowerCase().trim();
  const words = clean.split(/[\s,.-]+/);
  return YES_KEYWORDS.some((kw) => clean === kw || words.includes(kw) || clean.includes(kw));
}

function isNegative(text) {
  if (!text) return false;
  const clean = text.toLowerCase().trim();
  const words = clean.split(/[\s,.-]+/);
  return NO_KEYWORDS.some((kw) => clean === kw || words.includes(kw) || clean.includes(kw));
}

export default function FormFill() {
  const { language } = useSession();
  const lang = language === 'hi' || language === 'ta' ? language : 'en';
  const t = UI_STRINGS[lang];

  const { speak, listen, stopListening, isListening, isSpeaking, stopSpeaking, transcript, setTranscript, error: speechError, clearError: clearSpeechError } = useSpeech(lang);

  // The SMS gate runs once before the first upload. The four-digit anti-spoofing
  // challenge remains in place after every three fields and before final submission.
  // Phases: starting | verify-phone | upload | processing | asking | confirming | field-challenge | final-challenge | done
  const [phase, setPhase] = useState('starting');
  const [activeSessionId, setActiveSessionId] = useState(null);
  const [mfaVerified, setMfaVerified] = useState(false);
  const [formId, setFormId] = useState(null);
  const [fields, setFields] = useState([]);
  const [currentField, setCurrentField] = useState(null);
  const [progress, setProgress] = useState({ completed: 0, total: 0, percentage: 0 });
  const [userTranscript, setUserTranscript] = useState('');
  const [answerData, setAnswerData] = useState(null);
  const [dragOver, setDragOver] = useState(false);
  const [error, setError] = useState('');
  const [downloadUrl, setDownloadUrl] = useState(null);
  const [generatingPdf, setGeneratingPdf] = useState(false);
  const [finalNonce, setFinalNonce] = useState(null);
  const [customAnswer, setCustomAnswer] = useState('');
  const fileRef = useRef();
  const enrollmentRequest = useRef(null);

  const effectiveSession = activeSessionId;
  const confirmedCount = fields.filter((f) => f.status === 'confirmed').length;

  useEffect(() => {
    let active = true;
    // A form-fill visit gets a fresh session. Keeping the promise in a ref
    // makes React StrictMode's development remount reuse the same request
    // instead of canceling initialization and leaving a blank page.
    if (!enrollmentRequest.current) {
      enrollmentRequest.current = (async () => {
        const created = await createSession(lang);
        const sid = created.id;
        const status = await getOtpStatus(sid);
        return { sid, status };
      })();
    }

    const request = enrollmentRequest.current;
    request
      .then(({ sid, status }) => {
        if (!active) return;
        setActiveSessionId(sid);
        setMfaVerified(Boolean(status?.verified));
        setPhase(status?.verified ? 'upload' : 'verify-phone');
      })
      .catch((e) => {
        if (!active) return;
        setError(e?.response?.data?.detail?.message || e.message || 'Could not start the form session.');
        setPhase('verify-phone');
      });

    return () => { active = false; };
  }, [lang]);

  // ── Fetch next field ──────────────────────────────────────────────
  const fetchNextField = useCallback(
    async (fid, fieldId) => {
      const id = typeof fid === 'string' ? fid : formId;
      if (!id) return;
      try {
        const res = await getNextField(id, lang, fieldId);
        setProgress(res.progress);
        if (res.is_complete) {
          setPhase('done');
          speak(t.formComplete + ' ' + t.allConfirmed);
          setCurrentField(null);
          return;
        }
        // the server's view of this field (e.g. it needs re-confirming after a change)
        setFields((prev) => prev.map((f) => (f.id === res.field.id ? { ...f, status: res.field.status } : f)));
        setCurrentField(res.field);
        setUserTranscript('');
        setTranscript('');
        setCustomAnswer('');
        setAnswerData(null);
        setPhase('asking');
        // Speak the field question in user's language
        setTimeout(() => speak(res.question_audio_text || res.field.question_text), 400);
      } catch (e) {
        console.warn('Error fetching next field:', e);
      }
    },
    [formId, speak, t, setTranscript, lang]
  );

  // ── Back / Skip / jump to a field ─────────────────────────────────
  // A changed answer must be confirmed again (the server does the same)
  const markAnswered = useCallback((fieldId) => {
    setFields((prev) => prev.map((f) => (f.id === fieldId && f.status !== 'asked' ? { ...f, status: 'asked' } : f)));
  }, []);

  const goToField = useCallback((fieldId) => {
    if (!formId || !fieldId) return;
    stopSpeaking();
    fetchNextField(formId, fieldId);
  }, [formId, fetchNextField, stopSpeaking]);

  const goBack = useCallback(() => {
    if (!fields.length) return;
    const idx = currentField ? fields.findIndex((f) => f.id === currentField.id) : fields.length;
    if (idx > 0) goToField(fields[idx - 1].id);
  }, [fields, currentField, goToField]);

  const skipCurrent = useCallback(async () => {
    if (!currentField || !formId) return;
    stopSpeaking();
    try {
      await skipFormField(formId, currentField.id);
      setFields((prev) => prev.map((f) => (f.id === currentField.id ? { ...f, status: 'skipped', confirmed_value: null, form_value: null } : f)));
    } catch (e) {
      console.warn('Skip field error:', e);
    }
    fetchNextField(formId);
  }, [currentField, formId, fetchNextField, stopSpeaking]);

  // ── Upload handler ────────────────────────────────────────────────
  const handleFile = useCallback(
    async (file) => {
      if (!file) return;
      if (!mfaVerified) {
        setError('Verify your phone before uploading a form.');
        setPhase('verify-phone');
        return;
      }
      setPhase('processing');
      setError('');
      try {
        if (!effectiveSession) throw new Error('A session is required before upload.');
        const result = await uploadForm(effectiveSession, file, lang);
        setFormId(result.form_id);
        setFields(result.fields);
        setPhase('asking');

        const welcomeMsg =
          lang === 'hi'
            ? `फॉर्म सफलतापूर्वक अपलोड हो गया। भरने के लिए ${result.total_fields} प्रश्न मिले हैं। आइए शुरू करते हैं।`
            : lang === 'ta'
            ? `படிவம் பதிவேற்றப்பட்டது. ${result.total_fields} விவரங்கள் கண்டறியப்பட்டுள்ளன. தொடங்கலாம்.`
            : `Form uploaded successfully. I found ${result.total_fields} fields to complete. Let's start!`;

        speak(welcomeMsg);
        setTimeout(() => fetchNextField(result.form_id), 1800);
      } catch (e) {
        console.error('Upload error:', e);
        const detail = e.response?.data?.detail;
        const message = typeof detail === 'object' ? detail.message : detail;
        setError(`Could not upload form (${message || e.message || 'server error'}). Please check backend.`);
        setPhase('upload');
      }
    },
    [effectiveSession, lang, mfaVerified, speak, fetchNextField]
  );

  // ── Listen and submit answer ──────────────────────────────────────
  const handleAnswer = useCallback(async () => {
    if (!currentField) return;
    setError('');
    clearSpeechError?.();
    try {
      const text = await listen();
      const finalText = text || transcript || userTranscript;
      setUserTranscript(finalText);

      if (!finalText.trim()) {
        speak(t.cantHear);
        return;
      }

      // "back" / "skip" spoken instead of an answer
      const command = navCommand(finalText);
      if (command === 'back') {
        goBack();
        return;
      }
      if (command === 'skip') {
        skipCurrent();
        return;
      }

      // Submit answer to backend
      const result = await submitFieldAnswer(formId, currentField.id, finalText, lang);
      if (!result.validation_passed) {
        setAnswerData(null);
        setError(result.validation_message || 'Please check this answer and try again.');
        setPhase('asking');
        return;
      }
      markAnswered(currentField.id);
      setAnswerData(result);
      setCustomAnswer(result.interpreted_value || finalText);
      setPhase('confirming');
      speak(result.readback_text);
    } catch (e) {
      console.warn('Answer submission error:', e);
      setError(e.message || 'Error processing your answer.');
    }
  }, [clearSpeechError, currentField, formId, lang, listen, speak, t, transcript, userTranscript, goBack, skipCurrent, markAnswered]);

  // ── Submit typed answer directly without voice ────────────────────
  const handleDirectTextSubmit = useCallback(async (customText) => {
    if (!currentField) return;
    const valueToSubmit = (customText !== undefined ? customText : userTranscript).trim();
    if (!valueToSubmit) return;
    setError('');
    try {
      const result = await submitFieldAnswer(formId, currentField.id, valueToSubmit, lang);
      if (!result.validation_passed) {
        setAnswerData(null);
        setError(result.validation_message || 'Please check this answer and try again.');
        setPhase('asking');
        return;
      }
      markAnswered(currentField.id);
      setAnswerData(result);
      setCustomAnswer(result.interpreted_value || valueToSubmit);
      setPhase('confirming');
      speak(result.readback_text);
    } catch (e) {
      console.warn('Answer submission error:', e);
      setError(e.message || 'Error processing your answer.');
    }
  }, [currentField, formId, lang, speak, userTranscript, markAnswered]);

  // ── Submit typed/corrected answer directly ────────────────────────
  const handleCustomTextSubmit = useCallback(async () => {
    if (!currentField || !customAnswer.trim()) return;
    setError('');
    try {
      const result = await submitFieldAnswer(formId, currentField.id, customAnswer.trim(), lang);
      if (!result.validation_passed) {
        setAnswerData(null);
        setError(result.validation_message || 'Please check this answer and try again.');
        setPhase('asking');
        return;
      }
      markAnswered(currentField.id);
      setAnswerData(result);
      setCustomAnswer(result.interpreted_value || customAnswer.trim());
      setPhase('confirming');
      speak(result.readback_text);
    } catch (e) {
      console.warn('Error submitting custom answer:', e);
      setError(e.message || 'Error updating answer.');
    }
  }, [currentField, customAnswer, formId, lang, speak, markAnswered]);

  // ── Green ✓ Confirm Button Action ─────────────────────────────────
  const completeFieldAndContinue = useCallback(() => {
    if (!currentField) return;
    const confirmedVal = answerData?.interpreted_value || customAnswer || userTranscript;
    setFields((prev) =>
      prev.map((f) =>
        f.id === currentField.id
          ? { ...f, status: 'confirmed', confirmed_value: confirmedVal, form_value: answerData?.form_value }
          : f
      )
    );
    speak(t.confirmSuccess);
    setTimeout(() => {
      fetchNextField();
    }, 1000);
  }, [currentField, answerData, customAnswer, userTranscript, speak, t, fetchNextField]);

  const handleConfirmField = useCallback(() => {
    if (!currentField || !answerData) {
      setError('Could not confirm this answer. Please submit it again.');
      return;
    }

    const fieldIndex = fields.findIndex((field) => field.id === currentField.id);
    const questionNumber = fieldIndex >= 0 ? fieldIndex + 1 : progress.completed + 1;

    // Let the user answer three questions in a row. The 4-digit challenge is
    // shown only at the end of each three-question batch.
    if (questionNumber % 3 !== 0) {
      completeFieldAndContinue();
      return;
    }

    if (!answerData.nonce_id || !answerData.challenge_digits) {
      setError('Could not start the security challenge. Please submit this answer again.');
      return;
    }
    setError('');
    setPhase('field-challenge');
  }, [currentField, answerData, fields, progress.completed, completeFieldAndContinue]);

  const handleFieldNonceConfirmed = completeFieldAndContinue;

  // ── Red ✗ Reject/Retry Button Action ──────────────────────────────
  const handleRejectField = useCallback(() => {
    setUserTranscript('');
    setTranscript('');
    setCustomAnswer('');
    setAnswerData(null);
    setPhase('asking');
    speak(currentField?.question_text || '');
  }, [currentField, setTranscript, speak]);

  // ── Secondary Voice Yes/No Listener in 'confirming' phase ─────────
  const handleVoiceConfirm = useCallback(async () => {
    try {
      const text = await listen();
      const spoken = text || transcript;
      if (!spoken || !spoken.trim()) {
        speak(t.voiceAffirmHint);
        return;
      }

      if (isAffirmative(spoken)) {
        handleConfirmField();
      } else if (isNegative(spoken)) {
        handleRejectField();
      } else {
        speak(t.voiceAffirmHint);
      }
    } catch (e) {
      console.warn('Voice confirmation listening error:', e);
      speak(t.voiceAffirmHint);
    }
  }, [listen, transcript, speak, t, handleConfirmField, handleRejectField]);

  // ── Finalize Form & Generate Download ────────────────────────────
  async function handleFinalize() {
    setGeneratingPdf(true);
    setError('');
    try {
      const result = await finalizeForm(formId);
      const url = resolveBackendUrl(result.pdf_url);
      setDownloadUrl(url);
      setPhase('done');
      speak(
        lang === 'hi'
          ? 'आपका भरा हुआ फॉर्म पीडीएफ तैयार है! डाउनलोड बटन दबाएं।'
          : lang === 'ta'
          ? 'உங்கள் பூர்த்தி செய்யப்பட்ட PDF தயார்! பதிவிறக்கம் செய்யவும்.'
          : 'Your completed form PDF is ready! Tap download.'
      );
    } catch (e) {
      console.warn('Finalize error:', e);
      const detail = e?.response?.data?.detail;
      setDownloadUrl(null);
      setError((typeof detail === 'object' ? detail.message : detail) || e.message || 'Could not finalize the form.');
      setPhase('done');
    } finally {
      setGeneratingPdf(false);
    }
  }

  // ── Step 1: Final One-Time Voice Challenge ───────────────────────
  const startVoiceChallenge = useCallback(async () => {
    setError('');
    try {
      // Request a four-digit anti-spoofing challenge for final submission
      const nonceData = await createChallenge(effectiveSession, 'submit_form', formId);
      setFinalNonce(nonceData);
      setPhase('final-challenge');
    } catch (e) {
      console.warn('Error issuing final challenge:', e);
      const detail = e?.response?.data?.detail;
      setError((typeof detail === 'object' ? detail.message : detail) || e.message || 'Could not create the final confirmation challenge.');
      setPhase('done');
    }
  }, [effectiveSession, formId]);

  const startFinalChallenge = startVoiceChallenge;

  const handleFinalNonceConfirmed = () => handleFinalize();
  const securityStep = phase === 'field-challenge' || phase === 'final-challenge';

  return (
    <div className="container" style={{ paddingBottom: 60, maxWidth: 960, margin: '0 auto' }}>
      {/* Page Header */}
      <div className="page-header" style={{ textAlign: 'center', marginBottom: 24 }}>
        <div className="badge badge-teal" style={{ marginBottom: 10, fontSize: 14, padding: '6px 16px' }}>
          {t.badge}
        </div>
        <h1 className="page-title" style={{ fontSize: 32, fontWeight: 800 }}>
          {t.title}
        </h1>
        <p
          className="page-subtitle"
          style={{ fontSize: 16, color: '#475569', maxWidth: 650, margin: '8px auto 0' }}
        >
          {t.subtitle}
        </p>
      </div>

      {error && (
        <div
          style={{
            padding: '12px 18px',
            background: '#fee2e2',
            border: '1.5px solid #ef4444',
            borderRadius: 12,
            marginBottom: 18,
            fontSize: 14,
            color: '#b91c1c',
            fontWeight: 600,
          }}
        >
          ⚠ {error}
        </div>
      )}

      {/* One-time SMS verification gate before the first form upload */}
      {phase === 'verify-phone' && effectiveSession && (
        <PhoneVerify
          sessionId={effectiveSession}
          language={lang}
          onVerified={() => {
            setMfaVerified(true);
            setError('');
            setPhase('upload');
          }}
          onError={(e) => {
            const detail = e?.response?.data?.detail;
            setError(typeof detail === 'object' ? detail.message : detail || e?.message || 'Phone verification failed.');
          }}
        />
      )}

      {/* Upload Phase */}
      {phase === 'upload' && (
        <motion.div initial={{ opacity: 0, y: 15 }} animate={{ opacity: 1, y: 0 }}>
          <div
            className={`upload-zone${dragOver ? ' drag-over' : ''}`}
            onDragOver={(e) => {
              e.preventDefault();
              setDragOver(true);
            }}
            onDragLeave={() => setDragOver(false)}
            onDrop={(e) => {
              e.preventDefault();
              setDragOver(false);
              handleFile(e.dataTransfer.files[0]);
            }}
            onClick={() => fileRef.current?.click()}
            style={{
              padding: '48px 24px',
              border: '3px dashed #94a3b8',
              borderRadius: '24px',
              textAlign: 'center',
              background: dragOver ? '#eff6ff' : '#ffffff',
              cursor: 'pointer',
              transition: 'all 0.2s ease',
            }}
          >
            <input
              ref={fileRef}
              type="file"
              accept="image/*,.pdf"
              style={{ display: 'none' }}
              onChange={(e) => handleFile(e.target.files[0])}
            />
            <div style={{ fontSize: 56, marginBottom: 16 }}>📄</div>
            <div style={{ fontSize: 22, fontWeight: 800, color: '#0f172a', marginBottom: 8 }}>
              {t.dropText}
            </div>
            <div style={{ fontSize: 15, color: '#64748b', maxWidth: 480, margin: '0 auto 24px' }}>
              {t.dropSub}
            </div>
            <button
              type="button"
              className="btn btn-primary"
              style={{ fontSize: 16, padding: '14px 32px', borderRadius: 30, fontWeight: 700 }}
              onClick={(e) => {
                e.stopPropagation();
                fileRef.current?.click();
              }}
            >
              <Upload size={20} /> {t.chooseBtn}
            </button>
          </div>

          {/* Sample Preset Forms for quick testing */}
          <div style={{ textAlign: 'center', marginTop: 24 }}>
            <div style={{ fontSize: 13, fontWeight: 700, color: '#64748b', marginBottom: 10 }}>
              {lang === 'hi' ? 'या तुरंत नमूना सरकारी फॉर्म आज़माएं:' : lang === 'ta' ? 'அல்லது மாதிரி அரசு படிவங்களை முயற்சிக்கவும்:' : 'Or test with official sample forms:'}
            </div>
            <div style={{ display: 'flex', justifyContent: 'center', flexWrap: 'wrap', gap: 10 }}>
              <button
                type="button"
                className="btn btn-secondary"
                style={{ padding: '10px 18px', borderRadius: 20, fontSize: 13.5, fontWeight: 700 }}
                onClick={async () => {
                  try {
                    const blob = await fetchDemoTemplate('pm_kisan');
                    const file = new File([blob], 'PM_Kisan_Enrolment_Form.pdf', { type: 'application/pdf' });
                    handleFile(file);
                  } catch (e) {
                    console.warn('Demo fetch failed, using local file:', e);
                  }
                }}
              >
                🌾 {lang === 'hi' ? 'पीएम-किसान फॉर्म' : lang === 'ta' ? 'PM-கிசான் படிவம்' : 'PM-Kisan Farmer Form'}
              </button>

              <button
                type="button"
                className="btn btn-secondary"
                style={{ padding: '10px 18px', borderRadius: 20, fontSize: 13.5, fontWeight: 700 }}
                onClick={async () => {
                  try {
                    const blob = await fetchDemoTemplate('pension');
                    const file = new File([blob], 'NSAP_Old_Age_Pension_Form.pdf', { type: 'application/pdf' });
                    handleFile(file);
                  } catch (e) {
                    console.warn('Demo fetch failed, using local file:', e);
                  }
                }}
              >
                🧓 {lang === 'hi' ? 'वृद्धावस्था पेंशन फॉर्म' : lang === 'ta' ? 'ஓய்வூதிய படிவம்' : 'Old Age Pension Form'}
              </button>

              <button
                type="button"
                className="btn btn-secondary"
                style={{ padding: '10px 18px', borderRadius: 20, fontSize: 13.5, fontWeight: 700 }}
                onClick={async () => {
                  try {
                    const blob = await fetchDemoTemplate('bank_form');
                    const file = new File([blob], 'Jan_Dhan_Bank_Account_Form.pdf', { type: 'application/pdf' });
                    handleFile(file);
                  } catch (e) {
                    console.warn('Demo fetch failed, using local file:', e);
                  }
                }}
              >
                🏦 {lang === 'hi' ? 'जन धन बैंक खाता फॉर्म' : lang === 'ta' ? 'ஜன் தன் வங்கி படிவம்' : 'Jan Dhan Bank Account Form'}
              </button>
            </div>
          </div>
        </motion.div>
      )}

      {/* Processing Phase */}
      {phase === 'processing' && (
        <div style={{ textAlign: 'center', padding: '80px 20px' }}>
          <div className="loader" style={{ width: 52, height: 52, margin: '0 auto 24px', borderWidth: 4 }} />
          <h2 style={{ fontSize: 24, fontWeight: 800, color: '#0f172a', marginBottom: 8 }}>
            {t.processingTitle}
          </h2>
          <p style={{ color: '#64748b', fontSize: 16 }}>{t.processingSub}</p>
        </div>
      )}

      {/* Active Form Fill Phases */}
      {['asking', 'confirming', 'field-challenge', 'final-challenge', 'done'].includes(phase) && (
        <div
          className="form-fill-layout"
          style={{ display: 'grid', gap: 24 }}
        >
          {/* Sidebar with field status */}
          <div
            className="field-sidebar"
            style={{
              background: '#ffffff',
              padding: 20,
              borderRadius: 20,
              border: '1.5px solid #e2e8f0',
              boxShadow: '0 4px 16px rgba(0,0,0,0.04)',
              maxHeight: '600px',
              overflowY: 'auto',
            }}
          >
            <div
              style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                marginBottom: 12,
              }}
            >
              <span style={{ fontSize: 14, fontWeight: 800, color: '#334155' }}>
                {t.fieldsProgress} ({confirmedCount}/{fields.length})
              </span>
              <span style={{ fontSize: 13, fontWeight: 700, color: '#0284c7' }}>
                {progress.percentage || 0}%
              </span>
            </div>

            {/* Progress bar */}
            <div
              style={{
                height: 8,
                background: '#f1f5f9',
                borderRadius: 4,
                overflow: 'hidden',
                marginBottom: 18,
              }}
            >
              <div
                style={{
                  height: '100%',
                  width: `${progress.percentage || 0}%`,
                  background: '#0284c7',
                  transition: 'width 0.3s ease',
                }}
              />
            </div>

            {/* Field items list */}
            {!securityStep && formId && (
              <div style={{ fontSize: 12, color: '#64748b', marginBottom: 10 }}>{t.tapToChange}</div>
            )}
            {fields.map((f, i) => (
              <div
                key={f.id || i}
                role={formId && !securityStep ? 'button' : undefined}
                tabIndex={formId && !securityStep ? 0 : undefined}
                data-field-id={f.id}
                onClick={() => !securityStep && goToField(f.id)}
                onKeyDown={(e) => e.key === 'Enter' && !securityStep && goToField(f.id)}
                style={{
                  cursor: formId && !securityStep ? 'pointer' : 'default',
                  display: 'flex',
                  alignItems: 'center',
                  gap: 10,
                  padding: '10px 12px',
                  borderRadius: 10,
                  marginBottom: 6,
                  background:
                    currentField?.id === f.id
                      ? '#eff6ff'
                      : f.status === 'confirmed'
                      ? '#f0fdf4'
                      : 'transparent',
                  border: currentField?.id === f.id ? '1.5px solid #93c5fd' : '1px solid transparent',
                }}
              >
                <div
                  style={{
                    width: 10,
                    height: 10,
                    borderRadius: '50%',
                    background:
                      f.status === 'confirmed'
                        ? '#22c55e'
                        : currentField?.id === f.id
                        ? '#0284c7'
                        : '#cbd5e1',
                    flexShrink: 0,
                  }}
                />
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div
                    style={{
                      fontSize: 14,
                      fontWeight: currentField?.id === f.id ? 700 : 500,
                      color: currentField?.id === f.id ? '#1e3a8a' : '#334155',
                      whiteSpace: 'nowrap',
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                    }}
                  >
                    {f.label_local || f.label}
                  </div>
                  {f.status === 'skipped' && (
                    <div style={{ fontSize: 12, color: '#b45309', fontWeight: 600 }}>{t.skippedLabel}</div>
                  )}
                  {f.confirmed_value && f.status !== 'skipped' && (
                    <div
                      style={{
                        fontSize: 12,
                        color: '#15803d',
                        fontWeight: 600,
                        whiteSpace: 'nowrap',
                        overflow: 'hidden',
                        textOverflow: 'ellipsis',
                      }}
                    >
                      {f.confirmed_value}
                    </div>
                  )}
                </div>
                {f.status === 'confirmed' && (
                  <CheckCircle size={16} style={{ color: '#16a34a', flexShrink: 0 }} />
                )}
              </div>
            ))}
          </div>

          {/* Main Question / Confirmation / Final Challenge / Done Panel */}
          <div
            className="glass-card question-panel"
            style={{
              padding: '36px 28px',
              borderRadius: 20,
              border: '2px solid #e2e8f0',
              background: '#ffffff',
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
              textAlign: 'center',
              boxShadow: '0 8px 30px rgba(0,0,0,0.06)',
              minHeight: 460,
            }}
          >
            <AnimatePresence mode="wait">
              {/* ── STEP 1: FAST BUTTON-BASED CONFIRMING PHASE ── */}
              {phase === 'confirming' && answerData ? (
                <motion.div
                  key="confirming"
                  initial={{ opacity: 0, y: 15 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -15 }}
                  style={{ width: '100%', display: 'flex', flexDirection: 'column', alignItems: 'center' }}
                >
                  {/* Field Header */}
                  <div
                    style={{
                      fontSize: 13,
                      fontWeight: 800,
                      color: '#0284c7',
                      textTransform: 'uppercase',
                      letterSpacing: '0.05em',
                      marginBottom: 6,
                    }}
                  >
                    {t.fieldOf} {Math.max(1, fields.findIndex((f) => f.id === currentField?.id) + 1)} / {fields.length || progress.total} — {currentField?.label_local || currentField?.label}
                  </div>

                  {/* Readback voice sentence */}
                  <div
                    className="form-confirm-readback"
                    style={{
                      fontSize: 19,
                      fontWeight: 700,
                      padding: '14px 24px',
                      borderRadius: 14,
                      marginBottom: 20,
                      maxWidth: 540,
                      lineHeight: 1.4,
                    }}
                  >
                    "{answerData.readback_text}"
                  </div>

                  {/* Interpreted value callout */}
                  <div className="form-interpreted-value" style={{ marginBottom: 24 }}>
                    <span className="form-interpreted-label" style={{ fontSize: 14, fontWeight: 600 }}>
                      {t.interpretedAs}{' '}
                    </span>
                    <span
                      className="form-interpreted-answer"
                      style={{
                        fontSize: 18,
                        fontWeight: 800,
                        padding: '4px 12px',
                        borderRadius: 8,
                      }}
                    >
                      {answerData.interpreted_value}
                    </span>
                    {answerData.form_value && answerData.form_value !== answerData.interpreted_value && (
                      <div className="form-written-value" style={{ marginTop: 10, fontSize: 15 }}>
                        {t.writtenAs}{' '}
                        <strong className="form-written-answer" style={{ fontSize: 18, padding: '3px 10px', borderRadius: 8 }}>
                          {answerData.form_value}
                        </strong>
                      </div>
                    )}
                  </div>

                  {/* ── LARGE HIGH-CONTRAST GREEN (✓) & RED (✗) CONFIRMATION BUTTONS ── */}
                  <div
                    style={{
                      display: 'grid',
                      gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
                      gap: 16,
                      width: '100%',
                      maxWidth: 480,
                      marginBottom: 24,
                    }}
                  >
                    {/* Green ✓ Button: Correct — Next */}
                    <button
                      type="button"
                      onClick={handleConfirmField}
                      style={{
                        minHeight: 64,
                        padding: '16px 20px',
                        borderRadius: 16,
                        background: '#16a34a',
                        color: '#ffffff',
                        border: 'none',
                        cursor: 'pointer',
                        display: 'flex',
                        flexDirection: 'column',
                        alignItems: 'center',
                        justifyContent: 'center',
                        gap: 4,
                        boxShadow: '0 6px 20px rgba(22, 163, 74, 0.35)',
                        transition: 'transform 0.15s ease, background 0.15s ease',
                      }}
                      onMouseEnter={(e) => (e.currentTarget.style.transform = 'scale(1.02)')}
                      onMouseLeave={(e) => (e.currentTarget.style.transform = 'scale(1)')}
                    >
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 17, fontWeight: 800 }}>
                        <CheckCircle2 size={24} /> {t.confirmYes}
                      </div>
                      <span style={{ fontSize: 12, opacity: 0.9, fontWeight: 500 }}>
                        {t.confirmYesSub}
                      </span>
                    </button>

                    {/* Red ✗ Button: Wrong — Try Again */}
                    <button
                      type="button"
                      onClick={handleRejectField}
                      style={{
                        minHeight: 64,
                        padding: '16px 20px',
                        borderRadius: 16,
                        background: '#dc2626',
                        color: '#ffffff',
                        border: 'none',
                        cursor: 'pointer',
                        display: 'flex',
                        flexDirection: 'column',
                        alignItems: 'center',
                        justifyContent: 'center',
                        gap: 4,
                        boxShadow: '0 6px 20px rgba(220, 38, 38, 0.35)',
                        transition: 'transform 0.15s ease, background 0.15s ease',
                      }}
                      onMouseEnter={(e) => (e.currentTarget.style.transform = 'scale(1.02)')}
                      onMouseLeave={(e) => (e.currentTarget.style.transform = 'scale(1)')}
                    >
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 17, fontWeight: 800 }}>
                        <XCircle size={24} /> {t.confirmNo}
                      </div>
                      <span style={{ fontSize: 12, opacity: 0.9, fontWeight: 500 }}>
                        {t.confirmNoSub}
                      </span>
                    </button>
                  </div>

                  {/* ── SECONDARY VOICE OPTION (Say Yes / No) ── */}
                  <div
                    style={{
                      background: '#f8fafc',
                      border: '1px solid #e2e8f0',
                      borderRadius: 14,
                      padding: '12px 20px',
                      display: 'flex',
                      alignItems: 'center',
                      gap: 12,
                      marginBottom: 18,
                    }}
                  >
                    <VoiceButton
                      isListening={isListening}
                      isSpeaking={isSpeaking}
                      onClick={isListening ? stopListening : handleVoiceConfirm}
                      language={lang}
                      size="medium"
                    />
                    <div style={{ textAlign: 'left' }}>
                      <div style={{ fontSize: 13, fontWeight: 700, color: '#334155' }}>
                        {t.orSayVoice}
                      </div>
                      <div style={{ fontSize: 12, color: '#64748b' }}>
                        {t.voiceAffirmHint}
                      </div>
                    </div>
                  </div>

                  {/* ── TEXT INPUT FALLBACK FOR CORRECTIONS ── */}
                  <div style={{ width: '100%', maxWidth: 460, marginTop: 4 }}>
                    <div style={{ display: 'flex', gap: 8 }}>
                      <input
                        type="text"
                        value={customAnswer}
                        placeholder="Or edit answer directly…"
                        onChange={(e) => setCustomAnswer(e.target.value)}
                        onKeyDown={(e) => e.key === 'Enter' && handleCustomTextSubmit()}
                        style={{
                          flex: 1,
                          padding: '10px 14px',
                          borderRadius: '10px',
                          border: '1px solid #cbd5e1',
                          fontSize: '14px',
                        }}
                      />
                      <button
                        type="button"
                        className="btn btn-ghost"
                        style={{ fontSize: 13, padding: '10px 16px', borderRadius: 10 }}
                        onClick={handleCustomTextSubmit}
                      >
                        <Edit3 size={15} /> {t.editAnswer}
                      </button>
                    </div>
                  </div>
                </motion.div>
              ) : phase === 'field-challenge' && answerData ? (
                <motion.div
                  key={`field-challenge-${answerData.nonce_id}`}
                  initial={{ opacity: 0, y: 15 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -15 }}
                  style={{ width: '100%', display: 'flex', flexDirection: 'column', alignItems: 'center' }}
                >
                  <div className="badge badge-teal" style={{ marginBottom: 12, fontSize: 13, padding: '5px 14px' }}>
                    {t.fieldOf} {Math.max(1, fields.findIndex((f) => f.id === currentField?.id) + 1)} / {fields.length || progress.total} — {currentField?.label_local || currentField?.label}
                  </div>
                  <h2 style={{ fontSize: 24, fontWeight: 800, color: '#0f172a', marginBottom: 6 }}>
                    {lang === 'hi' ? 'आगे बढ़ने के लिए 4 अंक दोहराएँ' : lang === 'ta' ? 'தொடர 4 எண்களை மீண்டும் கூறுங்கள்' : 'Repeat the 4 numbers to continue'}
                  </h2>
                  <p style={{ color: '#64748b', fontSize: 15, maxWidth: 500, margin: '0 auto 20px' }}>
                    {lang === 'hi' ? 'अगले सवाल से पहले 30 सेकंड में बोलें या टाइप करें।' : lang === 'ta' ? 'அடுத்த கேள்விக்கு முன் 30 விநாடிகளில் கூறவும் அல்லது தட்டச்சு செய்யவும்.' : 'Say or type the 4 digits within 30 seconds to continue.'}
                  </p>
                  <ChallengePrompt
                    nonce={answerData}
                    sessionId={effectiveSession}
                    language={lang}
                    onSuccess={handleFieldNonceConfirmed}
                    onFailure={() => speak(t.cantHear)}
                  />
                  <button
                    type="button"
                    className="btn btn-ghost"
                    style={{ marginTop: 20, fontSize: 13, padding: '8px 18px', borderRadius: 20 }}
                    onClick={handleRejectField}
                  >
                    <ArrowLeft size={14} /> {t.confirmNo}
                  </button>
                </motion.div>
              ) : phase === 'final-challenge' && finalNonce ? (
                /* Final replay-resistant four-digit challenge before submission */
                <motion.div
                  key="final-challenge"
                  initial={{ opacity: 0, y: 15 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -15 }}
                  style={{ width: '100%', display: 'flex', flexDirection: 'column', alignItems: 'center' }}
                >
                  <div
                    className="badge badge-teal"
                    style={{ marginBottom: 12, fontSize: 13, padding: '5px 14px' }}
                  >
                    {t.finalChallengeBadge}
                  </div>
                  <h2 style={{ fontSize: 24, fontWeight: 800, color: '#0f172a', marginBottom: 6 }}>
                    {t.finalChallengeTitle}
                  </h2>
                  <p style={{ color: '#64748b', fontSize: 15, maxWidth: 500, margin: '0 auto 20px' }}>
                    {t.finalChallengeSub}
                  </p>

                  <ChallengePrompt
                    nonce={finalNonce}
                    sessionId={effectiveSession}
                    language={lang}
                    onSuccess={handleFinalNonceConfirmed}
                    onFailure={() => speak(t.cantHear)}
                  />

                  <button
                    type="button"
                    className="btn btn-ghost"
                    style={{ marginTop: 20, fontSize: 13, padding: '8px 18px', borderRadius: 20 }}
                    onClick={() => setPhase('done')}
                  >
                    <ArrowLeft size={14} /> {t.reviewFields}
                  </button>
                </motion.div>
              ) : phase === 'done' ? (
                /* ── STEP 3: FORM COMPLETE / FINAL DOWNLOAD ── */
                <motion.div
                  key="done"
                  initial={{ opacity: 0, scale: 0.95 }}
                  animate={{ opacity: 1, scale: 1 }}
                  exit={{ opacity: 0, scale: 0.95 }}
                  style={{ width: '100%', textAlign: 'center' }}
                >
                  <div style={{ fontSize: 60, marginBottom: 14 }}>🎉</div>
                  <h2 style={{ fontSize: 28, fontWeight: 900, color: '#0f172a', marginBottom: 10 }}>
                    {downloadUrl ? 'PDF Ready!' : t.formComplete}
                  </h2>
                  <p style={{ color: '#475569', fontSize: 16, maxWidth: 480, margin: '0 auto 24px' }}>
                    {downloadUrl ? t.allConfirmed : t.readyToFinalize}
                  </p>
                  {!downloadUrl && fields.some((f) => f.status === 'skipped') && (
                    <p style={{ color: '#b45309', fontSize: 14, fontWeight: 600, maxWidth: 480, margin: '-12px auto 20px' }}>
                      {t.leftBlank(fields.filter((f) => f.status === 'skipped').length)}
                    </p>
                  )}

                  {!downloadUrl ? (
                    <button
                      type="button"
                      className="btn btn-primary"
                      style={{
                        fontSize: 16,
                        padding: '16px 36px',
                        borderRadius: 30,
                        fontWeight: 800,
                        display: 'inline-flex',
                        alignItems: 'center',
                        gap: 10,
                        boxShadow: '0 8px 25px rgba(2, 132, 199, 0.35)',
                      }}
                      onClick={startFinalChallenge}
                      disabled={generatingPdf}
                    >
                      <ShieldCheck size={22} /> {generatingPdf ? t.generatingBtn : t.proceedToFinalize}
                    </button>
                  ) : null}
                  {!downloadUrl && fields.length > 0 && (
                    <div style={{ marginTop: 14 }}>
                      <button
                        type="button"
                        className="btn btn-ghost"
                        style={{ fontSize: 14, padding: '8px 18px' }}
                        onClick={() => goToField(fields[fields.length - 1].id)}
                      >
                        <ArrowLeft size={15} /> {t.backBtn}
                      </button>
                    </div>
                  )}
                  {downloadUrl && (
                    <a
                      className="btn btn-green"
                      style={{
                        fontSize: 16,
                        padding: '16px 36px',
                        borderRadius: 30,
                        fontWeight: 800,
                        display: 'inline-flex',
                        alignItems: 'center',
                        gap: 10,
                        boxShadow: '0 8px 25px rgba(22, 163, 74, 0.35)',
                      }}
                      href={downloadUrl}
                      target="_blank"
                      rel="noreferrer"
                    >
                      <Download size={22} /> {t.downloadBtn}
                    </a>
                  )}
                </motion.div>
              ) : (
                /* ── STEP 0: ASKING ACTIVE QUESTION ── */
                <motion.div
                  key="asking"
                  initial={{ opacity: 0, y: 15 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -15 }}
                  style={{ width: '100%', display: 'flex', flexDirection: 'column', alignItems: 'center' }}
                >
                  {currentField && (
                    <>
                      <div
                        style={{
                          fontSize: 13,
                          fontWeight: 800,
                          color: '#0284c7',
                          textTransform: 'uppercase',
                          letterSpacing: '0.05em',
                          marginBottom: 8,
                        }}
                      >
                        {t.fieldOf} {Math.max(1, fields.findIndex((f) => f.id === currentField.id) + 1)} / {fields.length || progress.total} — {currentField.label_local || currentField.label}
                      </div>

                      <h2
                        style={{
                          fontSize: 24,
                          fontWeight: 800,
                          color: '#0f172a',
                          margin: '4px 0 20px',
                          lineHeight: 1.4,
                        }}
                      >
                        {currentField.question_text}
                      </h2>

                      {/* Answer given earlier (reached with Back or by tapping the field) */}
                      {(() => {
                        const saved = fields.find((f) => f.id === currentField.id);
                        if (!saved?.confirmed_value || saved.status === 'skipped') return null;
                        return (
                          <div style={{ marginBottom: 14, padding: '10px 16px', borderRadius: 12, background: '#f0fdf4', border: '1.5px solid #86efac', color: '#14532d', fontSize: 15 }}>
                            {t.currentAnswer} <strong>{saved.confirmed_value}</strong>
                          </div>
                        );
                      })()}

                      {/* Live real-time transcribed text box */}
                      <div
                        className={`transcript-box${transcript || userTranscript ? ' has-text' : ''}`}
                        style={{
                          width: '100%',
                          maxWidth: 520,
                          minHeight: 56,
                          fontSize: 16,
                          fontWeight: 600,
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          background: transcript || userTranscript ? '#eff6ff' : '#f8fafc',
                          border:
                            transcript || userTranscript
                              ? '2px solid #3b82f6'
                              : '1.5px dashed #cbd5e1',
                          borderRadius: '14px',
                          padding: '12px 18px',
                          color: transcript || userTranscript ? '#1e3a8a' : '#94a3b8',
                          margin: '0 auto 16px',
                        }}
                      >
                        {transcript || userTranscript || t.yourAnswer}
                      </div>

                      {/* Big Voice Button */}
                      <VoiceButton
                        isListening={isListening}
                        isSpeaking={isSpeaking}
                        onClick={isListening ? stopListening : handleAnswer}
                        language={lang}
                        size="large"
                        error={speechError}
                      />

                      {/* Optional text input fallback for non-speaking or manual entry */}
                      <div style={{ width: '100%', maxWidth: 460, marginTop: 12, marginBottom: 16 }}>
                        <div style={{ display: 'flex', gap: 8 }}>
                          <input
                            type="text"
                            placeholder={lang === 'hi' ? 'या यहाँ उत्तर टाइप करें...' : lang === 'ta' ? 'அல்லது இங்கே தட்டச்சு செய்யவும்...' : 'Or type answer here...'}
                            value={userTranscript}
                            onChange={(e) => setUserTranscript(e.target.value)}
                            onKeyDown={(e) => {
                              if (e.key === 'Enter') {
                                e.preventDefault();
                                handleDirectTextSubmit(userTranscript);
                              }
                            }}
                            style={{
                              flex: 1,
                              padding: '10px 14px',
                              borderRadius: '10px',
                              border: '1px solid #cbd5e1',
                              fontSize: '14px',
                            }}
                          />
                          <button
                            type="button"
                            className="btn btn-primary btn-sm"
                            style={{ borderRadius: 10, padding: '0 16px', fontWeight: 700 }}
                            onClick={() => handleDirectTextSubmit(userTranscript)}
                            disabled={!userTranscript.trim()}
                          >
                            {lang === 'hi' ? 'जमा करें' : lang === 'ta' ? 'சமர்ப்பி' : 'Submit'}
                          </button>
                        </div>
                      </div>

                      {/* Quick controls */}
                      <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', justifyContent: 'center' }}>
                        <button
                          type="button"
                          className="btn btn-ghost"
                          style={{ fontSize: 13, padding: '8px 18px' }}
                          onClick={() => speak(currentField.question_text)}
                        >
                          <Volume2 size={15} /> {t.repeatBtn}
                        </button>
                        <button
                          type="button"
                          className="btn btn-ghost"
                          style={{ fontSize: 13, padding: '8px 18px' }}
                          onClick={goBack}
                          disabled={!fields.length || fields.findIndex((f) => f.id === currentField.id) <= 0}
                        >
                          <ArrowLeft size={15} /> {t.backBtn}
                        </button>
                        {fields.find((f) => f.id === currentField.id && f.status === 'confirmed') && (
                          <button
                            type="button"
                            className="btn btn-ghost"
                            style={{ fontSize: 13, padding: '8px 18px', color: '#15803d' }}
                            onClick={() => fetchNextField(formId)}
                          >
                            <CheckCircle size={15} /> {t.keepAnswer} →
                          </button>
                        )}
                        <button
                          type="button"
                          className="btn btn-ghost"
                          style={{ fontSize: 13, padding: '8px 18px' }}
                          onClick={skipCurrent}
                        >
                          {t.skipBtn} →
                        </button>
                      </div>
                    </>
                  )}
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        </div>
      )}

    </div>
  );
}
