import { useCallback, useEffect, useRef, useState } from 'react';
import { Camera, ImagePlus, X, RotateCcw, ScanText, RefreshCw, Keyboard, Lock } from 'lucide-react';
import { checkFraudImage } from '../api/client';
import { validateImageFile, errorCodeFromApi, cameraErrorCode, recoveryActions } from '../utils/fraudImage';

const T = {
  en: {
    takePhoto: 'Take Photo of Message',
    chooseImage: 'Choose an Existing Image',
    privacy: 'Show the message on your phone to the camera. We never open or read your phone’s messages — only the photo you take. The photo is not saved.',
    startingCamera: 'Starting camera…',
    aimHint: 'Hold the phone screen steady so the whole message fits in the frame.',
    capture: 'Capture',
    cancel: 'Cancel',
    retake: 'Retake',
    analyze: 'Read & Check Message',
    previewHint: 'Is the message clear and readable in this photo?',
    reading: 'Reading the message from your photo…',
    readingSub: 'This can take a few seconds.',
    actions: { camera: 'Try Camera Again', choose: 'Choose an Image', retake: 'Retake Photo', type: 'Type the Message Instead', retry: 'Try Again' },
    errors: {
      camera_unsupported: 'This browser cannot open the camera here. Please choose an existing image instead.',
      permission_denied: 'Camera permission was not allowed. You can allow the camera in the browser settings, or choose an existing image instead.',
      no_camera: 'No camera was found on this device. Please choose an existing image instead.',
      camera_busy: 'The camera could not start. It may be in use by another app. Please try again or choose an image.',
      unsupported_type: 'This file type is not supported. Please use a JPG, PNG, WebP or BMP photo.',
      file_too_large: 'This image is too large (maximum 10 MB). Please retake the photo or choose a smaller image.',
      empty_file: 'This image file is empty. Please retake the photo or choose another image.',
      unreadable_image: 'We could not open this image. Please retake the photo or choose another image.',
      no_text_found: 'We could not read any message text in this photo. This does NOT mean the message is safe. Retake the photo closer and in good light, or type the message.',
      ocr_failed: 'We could not read the text in this photo. This does NOT mean the message is safe. Please retake the photo or type the message.',
      ocr_unavailable: 'Reading text from photos is not available on this kiosk right now. This does NOT mean the message is safe. Please type the message instead.',
      timeout: 'Reading the photo took too long. Please try again.',
      network: 'Could not reach the server. Please check the connection and try again.',
      server: 'Something went wrong while checking the photo. Please try again.',
    },
  },
  hi: {
    takePhoto: 'संदेश की फोटो लें',
    chooseImage: 'पहले से मौजूद फोटो चुनें',
    privacy: 'अपने फोन पर संदेश खोलकर कैमरे को दिखाएं। हम आपके फोन के संदेश कभी नहीं खोलते या पढ़ते — केवल आपके द्वारा ली गई फोटो का उपयोग होता है। फोटो सेव नहीं की जाती।',
    startingCamera: 'कैमरा चालू हो रहा है…',
    aimHint: 'फोन की स्क्रीन स्थिर रखें ताकि पूरा संदेश फ्रेम में आ जाए।',
    capture: 'फोटो लें',
    cancel: 'रद्द करें',
    retake: 'दोबारा लें',
    analyze: 'संदेश पढ़ें और जाँचें',
    previewHint: 'क्या इस फोटो में संदेश साफ़ पढ़ा जा सकता है?',
    reading: 'आपकी फोटो से संदेश पढ़ा जा रहा है…',
    readingSub: 'इसमें कुछ सेकंड लग सकते हैं।',
    actions: { camera: 'कैमरा फिर से आज़माएं', choose: 'फोटो चुनें', retake: 'फोटो दोबारा लें', type: 'संदेश टाइप करें', retry: 'फिर से कोशिश करें' },
    errors: {
      camera_unsupported: 'यह ब्राउज़र यहाँ कैमरा नहीं खोल सकता। कृपया पहले से मौजूद फोटो चुनें।',
      permission_denied: 'कैमरे की अनुमति नहीं मिली। आप ब्राउज़र सेटिंग में कैमरा चालू कर सकते हैं, या पहले से मौजूद फोटो चुनें।',
      no_camera: 'इस डिवाइस में कोई कैमरा नहीं मिला। कृपया पहले से मौजूद फोटो चुनें।',
      camera_busy: 'कैमरा शुरू नहीं हो सका। हो सकता है कोई और ऐप इसका उपयोग कर रहा हो। फिर से कोशिश करें या फोटो चुनें।',
      unsupported_type: 'यह फ़ाइल प्रकार समर्थित नहीं है। कृपया JPG, PNG, WebP या BMP फोटो का उपयोग करें।',
      file_too_large: 'यह फोटो बहुत बड़ी है (अधिकतम 10 MB)। कृपया दोबारा फोटो लें या छोटी फोटो चुनें।',
      empty_file: 'यह फोटो फ़ाइल खाली है। कृपया दोबारा फोटो लें या दूसरी फोटो चुनें।',
      unreadable_image: 'यह फोटो खोली नहीं जा सकी। कृपया दोबारा फोटो लें या दूसरी फोटो चुनें।',
      no_text_found: 'इस फोटो में कोई संदेश पढ़ा नहीं जा सका। इसका मतलब यह नहीं है कि संदेश सुरक्षित है। अच्छी रोशनी में पास से फोटो लें, या संदेश टाइप करें।',
      ocr_failed: 'इस फोटो का टेक्स्ट पढ़ा नहीं जा सका। इसका मतलब यह नहीं है कि संदेश सुरक्षित है। दोबारा फोटो लें या संदेश टाइप करें।',
      ocr_unavailable: 'इस कियोस्क पर अभी फोटो से टेक्स्ट पढ़ने की सुविधा उपलब्ध नहीं है। इसका मतलब यह नहीं है कि संदेश सुरक्षित है। कृपया संदेश टाइप करें।',
      timeout: 'फोटो पढ़ने में बहुत समय लगा। कृपया फिर से कोशिश करें।',
      network: 'सर्वर से संपर्क नहीं हो सका। कृपया कनेक्शन जाँचें और फिर से कोशिश करें।',
      server: 'फोटो जाँचते समय कुछ गड़बड़ हुई। कृपया फिर से कोशिश करें।',
    },
  },
  ta: {
    takePhoto: 'செய்தியை புகைப்படம் எடுக்கவும்',
    chooseImage: 'ஏற்கனவே உள்ள படத்தை தேர்ந்தெடுக்கவும்',
    privacy: 'உங்கள் தொலைபேசியில் செய்தியைத் திறந்து கேமராவுக்குக் காட்டுங்கள். உங்கள் தொலைபேசியின் செய்திகளை நாங்கள் ஒருபோதும் திறப்பதோ படிப்பதோ இல்லை — நீங்கள் எடுக்கும் புகைப்படம் மட்டுமே பயன்படும். புகைப்படம் சேமிக்கப்படாது.',
    startingCamera: 'கேமரா தொடங்குகிறது…',
    aimHint: 'முழு செய்தியும் சட்டகத்தில் வரும்படி தொலைபேசியை அசையாமல் பிடியுங்கள்.',
    capture: 'படம் எடு',
    cancel: 'ரத்து செய்',
    retake: 'மீண்டும் எடு',
    analyze: 'செய்தியைப் படித்து சரிபார்க்கவும்',
    previewHint: 'இந்த புகைப்படத்தில் செய்தி தெளிவாகப் படிக்கக்கூடியதாக உள்ளதா?',
    reading: 'உங்கள் புகைப்படத்திலிருந்து செய்தி படிக்கப்படுகிறது…',
    readingSub: 'இதற்கு சில விநாடிகள் ஆகலாம்.',
    actions: { camera: 'கேமராவை மீண்டும் முயற்சிக்கவும்', choose: 'படத்தைத் தேர்ந்தெடுக்கவும்', retake: 'மீண்டும் படம் எடுக்கவும்', type: 'செய்தியை தட்டச்சு செய்யவும்', retry: 'மீண்டும் முயற்சிக்கவும்' },
    errors: {
      camera_unsupported: 'இந்த உலாவியில் இங்கே கேமராவைத் திறக்க முடியாது. ஏற்கனவே உள்ள படத்தைத் தேர்ந்தெடுக்கவும்.',
      permission_denied: 'கேமரா அனுமதி வழங்கப்படவில்லை. உலாவி அமைப்புகளில் கேமராவை அனுமதிக்கலாம், அல்லது ஏற்கனவே உள்ள படத்தைத் தேர்ந்தெடுக்கவும்.',
      no_camera: 'இந்த சாதனத்தில் கேமரா இல்லை. ஏற்கனவே உள்ள படத்தைத் தேர்ந்தெடுக்கவும்.',
      camera_busy: 'கேமராவைத் தொடங்க முடியவில்லை. வேறு செயலி பயன்படுத்தக்கூடும். மீண்டும் முயற்சிக்கவும் அல்லது படத்தைத் தேர்ந்தெடுக்கவும்.',
      unsupported_type: 'இந்த கோப்பு வகை ஆதரிக்கப்படவில்லை. JPG, PNG, WebP அல்லது BMP படத்தைப் பயன்படுத்தவும்.',
      file_too_large: 'இந்த படம் மிகப் பெரியது (அதிகபட்சம் 10 MB). மீண்டும் படம் எடுக்கவும் அல்லது சிறிய படத்தைத் தேர்ந்தெடுக்கவும்.',
      empty_file: 'இந்த படக் கோப்பு காலியாக உள்ளது. மீண்டும் படம் எடுக்கவும் அல்லது வேறு படத்தைத் தேர்ந்தெடுக்கவும்.',
      unreadable_image: 'இந்த படத்தைத் திறக்க முடியவில்லை. மீண்டும் படம் எடுக்கவும் அல்லது வேறு படத்தைத் தேர்ந்தெடுக்கவும்.',
      no_text_found: 'இந்த புகைப்படத்தில் செய்தியைப் படிக்க முடியவில்லை. இதன் பொருள் செய்தி பாதுகாப்பானது என்பதல்ல. நல்ல வெளிச்சத்தில் அருகில் படம் எடுக்கவும், அல்லது செய்தியை தட்டச்சு செய்யவும்.',
      ocr_failed: 'இந்த புகைப்படத்தின் உரையைப் படிக்க முடியவில்லை. இதன் பொருள் செய்தி பாதுகாப்பானது என்பதல்ல. மீண்டும் படம் எடுக்கவும் அல்லது தட்டச்சு செய்யவும்.',
      ocr_unavailable: 'இந்த கியோஸ்கில் தற்போது புகைப்படத்திலிருந்து உரையைப் படிக்கும் வசதி இல்லை. இதன் பொருள் செய்தி பாதுகாப்பானது என்பதல்ல. செய்தியை தட்டச்சு செய்யவும்.',
      timeout: 'புகைப்படத்தைப் படிக்க அதிக நேரம் ஆனது. மீண்டும் முயற்சிக்கவும்.',
      network: 'சேவையகத்தை அணுக முடியவில்லை. இணைப்பைச் சரிபார்த்து மீண்டும் முயற்சிக்கவும்.',
      server: 'புகைப்படத்தைச் சரிபார்க்கும்போது பிழை ஏற்பட்டது. மீண்டும் முயற்சிக்கவும்.',
    },
  },
};

const BIG_BUTTON = {
  minHeight: 56,
  padding: '14px 26px',
  fontSize: 17,
  fontWeight: 700,
  borderRadius: 'var(--radius-full)',
  display: 'inline-flex',
  alignItems: 'center',
  justifyContent: 'center',
  gap: 10,
  flex: '1 1 220px',
  maxWidth: 360,
};

/**
 * Lets the customer photograph (or pick a picture of) a message they want checked.
 * The camera starts only after they tap "Take Photo"; nothing on their phone is ever accessed.
 * Calls onResult(data) with the /fraud/check-image response so the page can show the text for review.
 */
export function PhotoMessageCheck({ language, sessionId, disabled, onResult, onTypeInstead }) {
  const t = T[language] || T.en;
  // idle | starting | camera | preview | uploading
  const [mode, setMode] = useState('idle');
  const [photo, setPhoto] = useState(null);
  const [previewUrl, setPreviewUrl] = useState(null);
  const [error, setError] = useState(null);
  const videoRef = useRef(null);
  const streamRef = useRef(null);
  const fileRef = useRef(null);
  const panelRef = useRef(null);

  const stopCamera = useCallback(() => {
    streamRef.current?.getTracks().forEach((track) => track.stop());
    streamRef.current = null;
  }, []);

  const clearPhoto = useCallback(() => {
    setPhoto(null);
    setPreviewUrl((url) => {
      if (url) URL.revokeObjectURL(url);
      return null;
    });
  }, []);

  // Release the camera and the in-memory photo when leaving the page
  useEffect(() => () => {
    stopCamera();
    setPreviewUrl((url) => {
      if (url) URL.revokeObjectURL(url);
      return null;
    });
  }, [stopCamera]);

  // Bring the camera / photo and its buttons fully on screen (kiosk users should not have to scroll)
  useEffect(() => {
    if ((mode === 'camera' || mode === 'preview') && panelRef.current) {
      const header = document.querySelector('.navbar'); // sticky: keep the panel below it
      const offset = (header ? header.getBoundingClientRect().height : 0) + 12;
      const top = panelRef.current.getBoundingClientRect().top + window.scrollY - offset;
      window.scrollTo({ top, behavior: 'smooth' });
    }
  }, [mode]);

  useEffect(() => {
    if (mode === 'camera' && videoRef.current && streamRef.current) {
      videoRef.current.srcObject = streamRef.current;
      videoRef.current.play().catch(() => {});
    }
  }, [mode]);

  const startCamera = async () => {
    setError(null);
    clearPhoto();
    if (!navigator.mediaDevices?.getUserMedia) {
      setError('camera_unsupported');
      return;
    }
    setMode('starting');
    try {
      let stream;
      try {
        stream = await navigator.mediaDevices.getUserMedia({
          video: { facingMode: { ideal: 'environment' }, width: { ideal: 1920 }, height: { ideal: 1080 } },
          audio: false,
        });
      } catch (err) {
        if (err?.name !== 'OverconstrainedError') throw err;
        stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: false });
      }
      streamRef.current = stream;
      setMode('camera');
    } catch (err) {
      stopCamera();
      setError(cameraErrorCode(err));
      setMode('idle');
    }
  };

  const acceptPhoto = (file) => {
    const problem = validateImageFile(file);
    if (problem) {
      setError(problem);
      setMode('idle');
      return;
    }
    clearPhoto();
    setPhoto(file);
    setPreviewUrl(URL.createObjectURL(file));
    setError(null);
    setMode('preview');
  };

  const capture = () => {
    const video = videoRef.current;
    if (!video || !video.videoWidth) {
      setError('camera_busy');
      return;
    }
    const canvas = document.createElement('canvas');
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    canvas.getContext('2d').drawImage(video, 0, 0, canvas.width, canvas.height);
    canvas.toBlob((blob) => {
      stopCamera();
      if (!blob) {
        setError('camera_busy');
        setMode('idle');
        return;
      }
      acceptPhoto(new File([blob], 'message-photo.jpg', { type: 'image/jpeg' }));
    }, 'image/jpeg', 0.92);
  };

  const cancel = () => {
    stopCamera();
    clearPhoto();
    setError(null);
    setMode('idle');
  };

  const chooseImage = () => {
    stopCamera();
    if (fileRef.current) {
      fileRef.current.value = '';
      fileRef.current.click();
    }
  };

  const analyze = async () => {
    if (!photo) return;
    setError(null);
    setMode('uploading');
    try {
      const data = await checkFraudImage(sessionId, photo, language);
      clearPhoto(); // the photo is not kept once the text has been read
      setMode('idle');
      onResult?.(data);
    } catch (err) {
      setError(errorCodeFromApi(err));
      setMode('preview');
    }
  };

  const runAction = (action) => {
    if (action === 'camera' || action === 'retake') startCamera();
    else if (action === 'choose') chooseImage();
    else if (action === 'retry') analyze();
    else if (action === 'type') {
      cancel();
      onTypeInstead?.();
    }
  };

  const actionIcon = { camera: Camera, retake: Camera, choose: ImagePlus, retry: RefreshCw, type: Keyboard };
  const busy = disabled || mode === 'starting' || mode === 'uploading';

  return (
    <div
      ref={panelRef}
      className="glass-card"
      style={{
        padding: 'var(--space-5)',
        borderRadius: 'var(--radius-xl)',
        border: '1px solid var(--color-border)',
        marginBottom: 'var(--space-5)',
      }}
    >
      <input
        ref={fileRef}
        type="file"
        accept="image/jpeg,image/png,image/webp,image/bmp"
        style={{ display: 'none' }}
        onChange={(e) => e.target.files?.[0] && acceptPhoto(e.target.files[0])}
      />

      {(mode === 'idle' || mode === 'starting') && (
        <>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 12, justifyContent: 'center' }}>
            <button type="button" className="btn btn-primary" style={{ ...BIG_BUTTON, background: '#d97706' }} onClick={startCamera} disabled={busy}>
              {mode === 'starting' ? <div className="loader" style={{ width: 18, height: 18 }} /> : <Camera size={22} />}
              {mode === 'starting' ? t.startingCamera : t.takePhoto}
            </button>
            <button type="button" className="btn btn-ghost" style={BIG_BUTTON} onClick={chooseImage} disabled={busy}>
              <ImagePlus size={22} /> {t.chooseImage}
            </button>
          </div>
          <p style={{ display: 'flex', gap: 8, alignItems: 'flex-start', fontSize: 13, color: 'var(--color-text-secondary)', margin: '12px auto 0', maxWidth: 620 }}>
            <Lock size={15} style={{ flexShrink: 0, marginTop: 2 }} /> {t.privacy}
          </p>
        </>
      )}

      {mode === 'camera' && (
        <div style={{ textAlign: 'center' }}>
          <p style={{ fontSize: 15, fontWeight: 600, marginBottom: 10 }}>{t.aimHint}</p>
          <video
            ref={videoRef}
            playsInline
            muted
            autoPlay
            style={{ width: '100%', maxHeight: 'min(52vh, 520px)', objectFit: 'contain', background: '#000', borderRadius: 'var(--radius-lg)' }}
          />
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 12, justifyContent: 'center', marginTop: 14 }}>
            <button type="button" className="btn btn-primary" style={{ ...BIG_BUTTON, background: '#d97706' }} onClick={capture}>
              <Camera size={22} /> {t.capture}
            </button>
            <button type="button" className="btn btn-ghost" style={BIG_BUTTON} onClick={cancel}>
              <X size={22} /> {t.cancel}
            </button>
          </div>
        </div>
      )}

      {(mode === 'preview' || mode === 'uploading') && previewUrl && (
        <div style={{ textAlign: 'center' }}>
          <p style={{ fontSize: 15, fontWeight: 600, marginBottom: 10 }}>{t.previewHint}</p>
          <img
            src={previewUrl}
            alt=""
            style={{ width: '100%', maxHeight: 'min(48vh, 480px)', objectFit: 'contain', background: 'var(--color-bg-subtle)', borderRadius: 'var(--radius-lg)', opacity: mode === 'uploading' ? 0.5 : 1 }}
          />
          {mode === 'uploading' ? (
            <div role="status" aria-live="polite" style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 8, marginTop: 16 }}>
              <div className="loader" style={{ width: 34, height: 34, borderWidth: 3 }} />
              <strong style={{ fontSize: 17 }}>{t.reading}</strong>
              <span style={{ fontSize: 13, color: 'var(--color-text-secondary)' }}>{t.readingSub}</span>
            </div>
          ) : (
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 12, justifyContent: 'center', marginTop: 14 }}>
              <button type="button" className="btn btn-primary" style={{ ...BIG_BUTTON, background: '#d97706' }} onClick={analyze}>
                <ScanText size={22} /> {t.analyze}
              </button>
              <button type="button" className="btn btn-ghost" style={BIG_BUTTON} onClick={startCamera}>
                <RotateCcw size={22} /> {t.retake}
              </button>
              <button type="button" className="btn btn-ghost" style={{ ...BIG_BUTTON, flex: '0 1 auto' }} onClick={cancel}>
                <X size={22} /> {t.cancel}
              </button>
            </div>
          )}
        </div>
      )}

      {error && (
        <div
          role="alert"
          style={{
            marginTop: 14,
            padding: '14px 16px',
            background: 'var(--color-red-dim)',
            border: '1.5px solid var(--color-red-border)',
            borderRadius: 'var(--radius-md)',
            color: 'var(--color-red)',
          }}
        >
          <p style={{ margin: '0 0 12px', fontSize: 15, fontWeight: 600, lineHeight: 1.5 }}>{t.errors[error] || t.errors.server}</p>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 10 }}>
            {recoveryActions(error)
              .filter((action) => action !== 'retry' || photo)
              .map((action) => {
                const Icon = actionIcon[action];
                return (
                  <button key={action} type="button" className="btn btn-ghost" style={{ ...BIG_BUTTON, minHeight: 50, fontSize: 15, background: '#fff' }} onClick={() => runAction(action)}>
                    <Icon size={18} /> {t.actions[action]}
                  </button>
                );
              })}
          </div>
        </div>
      )}
    </div>
  );
}
