/**
 * useSpeech — Robust Multilingual Web Speech API Hook
 * Provides real-time STT (speech-to-text) and natural TTS (text-to-speech)
 * Supports English, Hindi, and Tamil with optimal Indian voices.
 */

import { useState, useRef, useCallback, useEffect } from 'react';

const LANG_MAP = {
  en: 'en-IN',
  hi: 'hi-IN',
  ta: 'ta-IN',
  'en-IN': 'en-IN',
  'hi-IN': 'hi-IN',
  'ta-IN': 'ta-IN',
};

const ERROR_MESSAGES = {
  en: {
    notSupported: 'Voice recognition is not supported in this browser. Please use Google Chrome or Microsoft Edge.',
    notAllowed: 'Microphone permission blocked. Please click the lock or camera icon in your browser address bar and select "Allow".',
    audioCapture: 'No microphone was found or it is in use by another app. Please check your audio input.',
    network: 'Could not connect to the voice service because the browser is offline. Please check your internet connection.',
    browserService: 'The browser voice service is unavailable right now. Your internet may be fine. If you use Brave, disable Shields for this localhost page and try again; Chrome or Microsoft Edge also work.',
    serviceNotAllowed: 'Speech service blocked by browser or privacy extension. Please check browser settings.',
    noSpeech: 'No speech was detected. Please speak closer to your microphone.',
    generic: 'Voice error occurred. Please try again or type directly.',
  },
  hi: {
    notSupported: 'इस ब्राउज़र में आवाज़ पहचान समर्थित नहीं है। कृपया Google Chrome या Microsoft Edge का उपयोग करें।',
    notAllowed: 'माइक्रोफ़ोन की अनुमति अवरुद्ध है। कृपया ब्राउज़र के एड्रेस बार में लॉक/कैमरा आइकन पर क्लिक करके अनुमति दें।',
    audioCapture: 'कोई माइक्रोफ़ोन नहीं मिला या यह किसी अन्य ऐप द्वारा उपयोग किया जा रहा है।',
    network: 'आवाज़ सेवा से कनेक्ट नहीं हो सका। कृपया इंटरनेट कनेक्शन जांचें।',
    serviceNotAllowed: 'ब्राउज़र द्वारा स्पीच सेवा अवरुद्ध है। कृपया सेटिंग्स जांचें।',
    noSpeech: 'कोई आवाज़ सुनाई नहीं दी। कृपया माइक्रोफ़ोन के करीब बोलें।',
    generic: 'आवाज़ पहचान में समस्या आई। कृपया दोबारा प्रयास करें या टाइप करें।',
  },
  ta: {
    notSupported: 'இந்த உலாவியில் குரல் அறிதல் ஆதரிக்கப்படவில்லை. Google Chrome அல்லது Microsoft Edge ஐப் பயன்படுத்தவும்.',
    notAllowed: 'மைக்ரோஃபோன் அனுமதி தடுக்கப்பட்டுள்ளது. உலாவி முகவரிப் பட்டியில் உள்ள பூட்டு ஐகானைக் கிளிக் செய்து அனுமதிக்கவும்.',
    audioCapture: 'மைக்ரோஃபோன் கிடைக்கவில்லை அல்லது வேறு செயலியால் பயன்படுத்தப்படுகிறது.',
    network: 'குரல் சேவையுடன் இணைக்க முடியவில்லை. இணைய இணைப்பை சரிபார்க்கவும்.',
    serviceNotAllowed: 'உலாவி அமைப்புகளால் குரல் சேவை தடுக்கப்பட்டுள்ளது.',
    noSpeech: 'குரல் எதுவும் கேட்கவில்லை. தயவுசெய்து மைக்கிற்கு அருகில் பேசவும்.',
    generic: 'குரல் அறிதலில் பிழை ஏற்பட்டது. மீண்டும் முயற்சிக்கவும் அல்லது தட்டச்சு செய்யவும்.',
  },
};

// Split long text into sentences: Chrome stops reading a single utterance after ~15 seconds,
// which cut prompts off mid-sentence. Decimal points ("2.5") are not sentence ends.
function splitSentences(text) {
  const parts = String(text)
    .split(/(?<=[.!?।])\s+/)
    .map((p) => p.trim())
    .filter(Boolean);
  const chunks = [];
  parts.forEach((part) => {
    if (part.length <= 220) {
      chunks.push(part);
      return;
    }
    // very long sentence: break at commas / semicolons
    let current = '';
    part.split(/(?<=[,;:])\s+/).forEach((piece) => {
      if ((current + ' ' + piece).trim().length > 220 && current) {
        chunks.push(current.trim());
        current = piece;
      } else {
        current = (current + ' ' + piece).trim();
      }
    });
    if (current) chunks.push(current.trim());
  });
  return chunks.length ? chunks : [String(text)];
}

export function useSpeech(language = 'en') {
  const [isListening, setIsListening] = useState(false);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [transcript, setTranscript] = useState('');
  const [error, setError] = useState(null);

  const recognitionRef = useRef(null);
  const isListeningRef = useRef(false);
  const activeResolveRef = useRef(null);
  const transcriptRef = useRef('');
  const voicesRef = useRef([]);
  const silenceTimeoutRef = useRef(null);
  const utterancesRef = useRef([]); // keep queued utterances alive so Chrome fires their onend
  const mountedRef = useRef(true);

  const baseLang = (language || 'en').split('-')[0];
  const bcp47Lang = LANG_MAP[language] || LANG_MAP[baseLang] || 'en-IN';
  const errTexts = ERROR_MESSAGES[baseLang] || ERROR_MESSAGES.en;

  // ── Voice initialization ───────────────────────────────────────────
  useEffect(() => {
    if (typeof window === 'undefined' || !window.speechSynthesis) return;

    const updateVoices = () => {
      try {
        const vs = window.speechSynthesis.getVoices();
        if (vs && vs.length > 0) {
          voicesRef.current = vs;
        }
      } catch {
        // ignore
      }
    };

    updateVoices();
    if (window.speechSynthesis.onvoiceschanged !== undefined) {
      window.speechSynthesis.onvoiceschanged = updateVoices;
    }
  }, []);

  // ── Best Natural Voice Selection ────────────────────────────────────
  const getBestVoice = useCallback((langCode) => {
    const voices = voicesRef.current.length > 0
      ? voicesRef.current
      : (window.speechSynthesis?.getVoices() || []);

    if (!voices.length) return null;

    const langTarget = LANG_MAP[langCode] || 'en-IN';

    // Priority 1: Natural/Online neural voices for target language
    const naturalVoice = voices.find(v =>
      (v.lang === langTarget || v.lang.replace('_', '-') === langTarget) &&
      (v.name.includes('Natural') || v.name.includes('Online') || v.name.includes('Google'))
    );
    if (naturalVoice) return naturalVoice;

    // Priority 2: Any exact language match
    const exactMatch = voices.find(v =>
      v.lang === langTarget || v.lang.replace('_', '-') === langTarget
    );
    if (exactMatch) return exactMatch;

    // Priority 3: Language prefix match (e.g. 'hi', 'ta', 'en')
    const prefixMatch = voices.find(v =>
      v.lang.toLowerCase().startsWith(langCode.toLowerCase())
    );
    if (prefixMatch) return prefixMatch;

    // Priority 4: Indian English voice fallback
    const indianEn = voices.find(v =>
      (v.lang === 'en-IN' || v.name.includes('India')) &&
      (v.name.includes('Natural') || v.name.includes('Google'))
    );
    if (indianEn) return indianEn;

    // Fallback: Default system voice
    return voices.find(v => v.lang.startsWith('en')) || voices[0] || null;
  }, []);

  // Is a voice for this language installed? (unknown while the voice list is still loading → assume yes)
  const hasVoiceFor = useCallback((langCode) => {
    const voices = voicesRef.current.length > 0 ? voicesRef.current : (window.speechSynthesis?.getVoices() || []);
    if (!voices.length) return true;
    const base = (langCode || 'en').split('-')[0].toLowerCase();
    return voices.some((v) => v.lang.replace('_', '-').toLowerCase().startsWith(base));
  }, []);

  // ── TTS: speak several parts, each in its own language/voice, sentence by sentence ──
  // parts: [{ text, lang, optional }] — optional parts are skipped when no voice for that language exists
  const speakParts = useCallback((parts, onEnd = null) => {
    if (!parts?.length || typeof window === 'undefined' || !window.speechSynthesis) {
      onEnd?.();
      return;
    }

    try {
      window.speechSynthesis.cancel(); // Stop any overlapping speech

      const utterances = [];
      parts.forEach((part) => {
        if (!part?.text) return;
        const partLang = part.lang || language;
        if (part.optional && !hasVoiceFor(partLang)) return;
        const cleanText = String(part.text).replace(/[*#_]/g, '').trim();
        const voice = getBestVoice(partLang);
        splitSentences(cleanText).forEach((sentence) => {
          const utt = new SpeechSynthesisUtterance(sentence);
          utt.lang = LANG_MAP[partLang] || LANG_MAP[(partLang || 'en').split('-')[0]] || 'en-IN';
          utt.rate = 0.95;
          utt.pitch = 1.0;
          utt.volume = 1.0;
          if (voice) {
            try {
              utt.voice = voice;
            } catch {
              // unusual voice object — the language tag alone still picks a voice
            }
          }
          utterances.push(utt);
        });
      });

      if (!utterances.length) {
        onEnd?.();
        return;
      }

      let finished = false;
      const finish = () => {
        if (finished) return;
        finished = true;
        if (!mountedRef.current) return;
        setIsSpeaking(false);
        onEnd?.();
      };

      utterances.forEach((utt, idx) => {
        utt.onstart = () => setIsSpeaking(true);
        utt.onend = () => {
          if (idx === utterances.length - 1) finish();
        };
        utt.onerror = (e) => {
          console.warn('Speech synthesis notice:', e);
          // stopped / replaced by other speech: end now; a single failed sentence: carry on with the rest
          if (e?.error === 'interrupted' || e?.error === 'canceled' || idx === utterances.length - 1) finish();
        };
      });

      utterancesRef.current = utterances;
      setIsSpeaking(true);
      utterances.forEach((utt) => window.speechSynthesis.speak(utt));
    } catch (err) {
      console.error('TTS error:', err);
      setIsSpeaking(false);
      onEnd?.();
    }
  }, [getBestVoice, hasVoiceFor, language]);

  // speak(text, onEnd, lang) — lang overrides the page language (e.g. right after the user switches language)
  const speak = useCallback((text, onEnd = null, langOverride = null) => {
    if (!text) {
      onEnd?.();
      return;
    }
    speakParts([{ text, lang: langOverride || language }], onEnd);
  }, [speakParts, language]);

  const stopSpeaking = useCallback(() => {
    if (typeof window !== 'undefined' && window.speechSynthesis) {
      try {
        window.speechSynthesis.cancel();
      } catch {
        // ignore
      }
    }
    setIsSpeaking(false);
  }, []);

  // ── STT: Real-time listening with live note-down ─────────────────────
  // Resolve the active turn in one place. SpeechRecognition can fire both
  // `error` and `end`, so every exit path must be idempotent.
  const finishListening = useCallback((captured = transcriptRef.current) => {
    if (silenceTimeoutRef.current) {
      clearTimeout(silenceTimeoutRef.current);
      silenceTimeoutRef.current = null;
    }

    const resolve = activeResolveRef.current;
    activeResolveRef.current = null;
    recognitionRef.current = null;
    isListeningRef.current = false;
    setIsListening(false);

    if (resolve) {
      resolve(String(captured || '').trim());
    }
  }, []);

  const stopListening = useCallback(() => {
    const recognition = recognitionRef.current;
    if (recognition && isListeningRef.current) {
      try {
        recognition.stop();
      } catch {
        // already stopped
      }
    }
    finishListening(transcriptRef.current);
  }, [finishListening]);

  const listen = useCallback(async (langOverride = null) => {
    // 1. If already actively listening, user clicked to STOP -> resolve immediately with captured text
    if (isListeningRef.current && recognitionRef.current) {
      const currentText = transcriptRef.current;
      stopListening();
      return currentText;
    }

    // 2. Stop any ongoing TTS audio immediately so mic doesn't hear computer's own voice
    stopSpeaking();
    setError(null);

    // 3. Check browser API support
    const SpeechRecognition = typeof window !== 'undefined'
      ? (window.SpeechRecognition || window.webkitSpeechRecognition)
      : null;

    if (!SpeechRecognition) {
      const errMsg = errTexts.notSupported;
      console.warn(errMsg);
      setError(errMsg);
      return '';
    }

    // 4. Check microphone permission without opening a second audio stream.
    // Calling getUserMedia and immediately stopping it before SpeechRecognition
    // starts can race in Chromium and make an otherwise healthy mic look busy.
    let permissionStateChecked = false;
    if (typeof navigator !== 'undefined' && navigator.permissions?.query) {
      try {
        const permission = await navigator.permissions.query({ name: 'microphone' });
        permissionStateChecked = true;
        if (permission.state === 'denied') {
          setError(errTexts.notAllowed);
          return '';
        }
      } catch {
        // Some browsers do not expose microphone through Permissions API.
      }
    }

    // Older browsers still need a direct permission probe.
    if (!permissionStateChecked && typeof navigator !== 'undefined' && navigator.mediaDevices?.getUserMedia) {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        stream.getTracks().forEach((track) => track.stop());
      } catch (permErr) {
        console.warn('Microphone permission query result:', permErr);
        if (permErr.name === 'NotAllowedError' || permErr.name === 'PermissionDeniedError') {
          setError(errTexts.notAllowed);
          return '';
        } else if (permErr.name === 'NotFoundError' || permErr.name === 'DevicesNotFoundError') {
          setError(errTexts.audioCapture);
          return '';
        }
      }
    }

    return new Promise((resolve) => {
      try {
        if (recognitionRef.current) {
          try {
            recognitionRef.current.abort();
          } catch {
            // ignore
          }
        }

        const rec = new SpeechRecognition();
        rec.lang = (langOverride && (LANG_MAP[langOverride] || LANG_MAP[langOverride.split('-')[0]])) || bcp47Lang;
        // One spoken answer is one turn. Continuous recognition is less stable
        // in Chromium based browsers and can leave the UI stuck in Listening.
        rec.continuous = false;
        rec.interimResults = true;
        rec.maxAlternatives = 1;

        recognitionRef.current = rec;
        activeResolveRef.current = resolve;
        transcriptRef.current = '';
        setTranscript('');
        isListeningRef.current = true;
        setIsListening(true);

        const resetSilenceTimeout = (text) => {
          if (silenceTimeoutRef.current) clearTimeout(silenceTimeoutRef.current);
          // If user pauses after speaking, finalize the answer without waiting
          // for the browser's remote service timeout.
          if (text && text.trim().length > 0) {
            silenceTimeoutRef.current = setTimeout(() => {
              if (isListeningRef.current) {
                stopListening();
              }
            }, 2800);
          }
        };

        rec.onresult = (e) => {
          let finalTranscript = '';
          let interimTranscript = '';
          for (let i = 0; i < e.results.length; i++) {
            const result = e.results[i];
            const text = result?.[0]?.transcript || '';
            if (result?.isFinal) {
              finalTranscript += `${text} `;
            } else {
              interimTranscript += `${text} `;
            }
          }
          // Do not append every interim event: Chromium may repeat interim
          // results, which previously produced duplicated words.
          const cleaned = `${finalTranscript} ${interimTranscript}`
            .replace(/\s+/g, ' ')
            .trim();
          transcriptRef.current = cleaned;
          setTranscript(cleaned);
          resetSilenceTimeout(cleaned);
        };

        rec.onerror = (e) => {
          console.warn('Speech recognition event:', e.error);
          const captured = transcriptRef.current;
          const hasCapturedText = captured.trim().length > 0;
          let friendlyMsg = null;
          if (e.error === 'not-allowed' || e.error === 'permission-denied') {
            friendlyMsg = errTexts.notAllowed;
          } else if (e.error === 'service-not-allowed') {
            friendlyMsg = errTexts.serviceNotAllowed;
          } else if (e.error === 'network') {
            const offline = typeof navigator !== 'undefined' && navigator.onLine === false;
            friendlyMsg = offline ? errTexts.network : (errTexts.browserService || errTexts.network);
          } else if (e.error === 'audio-capture') {
            friendlyMsg = errTexts.audioCapture;
          } else if (e.error === 'no-speech') {
            friendlyMsg = errTexts.noSpeech;
          } else if (e.error !== 'aborted') {
            friendlyMsg = errTexts.generic;
          }

          // A provider can report `network` after delivering a valid final
          // result. Keep that answer instead of throwing it away or showing a
          // misleading error over it.
          if (friendlyMsg && e.error !== 'no-speech' && !hasCapturedText) {
            setError(friendlyMsg);
          }
          finishListening(captured);
        };

        rec.onend = () => {
          finishListening(transcriptRef.current);
        };

        // Never leave the form in a permanent Listening state when a browser
        // provider fails silently before producing its first result.
        silenceTimeoutRef.current = setTimeout(() => {
          if (isListeningRef.current) {
            stopListening();
          }
        }, 15000);

        rec.start();
      } catch (err) {
        console.error('Error starting speech recognition:', err);
        setError(errTexts.generic);
        finishListening('');
      }
    });
  }, [bcp47Lang, errTexts, finishListening, stopListening, stopSpeaking]);

  const clearError = useCallback(() => {
    setError(null);
  }, []);

  // Cleanup on unmount
  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
      if (silenceTimeoutRef.current) {
        clearTimeout(silenceTimeoutRef.current);
      }
      if (activeResolveRef.current) {
        const resolve = activeResolveRef.current;
        activeResolveRef.current = null;
        resolve(transcriptRef.current);
      }
      if (recognitionRef.current) {
        try {
          recognitionRef.current.abort();
        } catch {
          // ignore
        }
      }
      if (typeof window !== 'undefined' && window.speechSynthesis) {
        try {
          window.speechSynthesis.cancel();
        } catch {
          // ignore
        }
      }
    };
  }, []);

  const supported = typeof window !== 'undefined' &&
    ('SpeechRecognition' in window || 'webkitSpeechRecognition' in window);

  return {
    isListening,
    isSpeaking,
    transcript,
    error,
    clearError,
    supported,
    speak,
    speakParts,
    hasVoiceFor,
    stopSpeaking,
    listen,
    stopListening,
    setTranscript,
  };
}
