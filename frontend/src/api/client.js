import axios from 'axios';
import { buildImageFormData } from '../utils/fraudImage';

const ROOT_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
const BASE_URL = `${ROOT_URL}/api/v1`;

export const resolveBackendUrl = (path) => new URL(path, ROOT_URL).toString();

export const api = axios.create({
  baseURL: BASE_URL,
  timeout: 30000,
});

// ── Sessions ──────────────────────────────────────────────────────────
export const createSession = (language = 'en', phone = null) =>
  api.post('/sessions', { preferred_language: language, user_phone: phone }).then(r => r.data);

export const getSession = (id) =>
  api.get(`/sessions/${id}`).then(r => r.data);

export const updateLanguage = (sessionId, language) =>
  api.patch(`/sessions/${sessionId}/language`, null, { params: { language } }).then(r => r.data);

// ── Session SMS verification ───────────────────────────────────────────────
export const sendOtp = (sessionId, phone, language = 'en') =>
  api.post('/auth/otp/send', { session_id: sessionId, phone, language }).then(r => r.data);

export const verifyOtp = (sessionId, otpId, code) =>
  api.post('/auth/otp/verify', { session_id: sessionId, otp_id: otpId, code }).then(r => r.data);

export const getOtpStatus = (sessionId) =>
  api.get(`/auth/status/${sessionId}`).then(r => r.data);

// ── Forms ─────────────────────────────────────────────────────────────
export const uploadForm = (sessionId, file, language) => {
  const form = new FormData();
  form.append('session_id', sessionId);
  form.append('file', file);
  if (language) form.append('language', language); // field labels come back translated
  return api.post('/forms/upload', form).then(r => r.data);
};

// language: questions and labels are asked in the kiosk's current language
// fieldId (optional): ask that particular field — used by Back and by tapping a field to change its answer
export const getNextField = (formId, language, fieldId) =>
  api.get(`/forms/${formId}/next-field`, { params: { language, field_id: fieldId || undefined } }).then(r => r.data);

// Leave a field blank on the form (it can be filled later before finishing)
export const skipFormField = (formId, fieldId) =>
  api.post(`/forms/${formId}/fields/${fieldId}/skip`).then(r => r.data);

export const submitFieldAnswer = (formId, fieldId, transcribedText, language = 'en') =>
  api.post(`/forms/${formId}/fields/${fieldId}/answer`, {
    transcribed_text: transcribedText,
    language,
  }).then(r => r.data);

export const finalizeForm = (formId) =>
  api.post(`/forms/${formId}/finalize`).then(r => r.data);

export const getFormDownloadUrl = (formId) =>
  `${BASE_URL}/forms/${formId}/download`;

export const fetchDemoTemplate = (templateId) =>
  api.get(`/forms/demo-templates/${templateId}`, { responseType: 'blob' }).then(r => r.data);

// ── Confirmations ─────────────────────────────────────────────────────
export const createChallenge = (sessionId, boundAction = 'submit_form', boundTargetId = null) =>
  api.post('/confirmations', {
    session_id: sessionId,
    bound_action: boundAction,
    bound_target_id: boundTargetId,
  }).then(r => r.data);

export const respondToChallenge = (nonceId, sessionId, transcribedText) =>
  api.post(`/confirmations/${nonceId}/respond`, {
    session_id: sessionId,
    transcribed_text: transcribedText,
  }).then(r => r.data);

// ── Schemes ───────────────────────────────────────────────────────────
export const fetchSchemeGroups = (language = 'en') =>
  api.get('/schemes/groups', { params: { language } }).then(r => r.data);

// filters: { audience, need, q } — who it is for, what it gives, free-text search (en / hi / ta / Hinglish)
export const fetchSchemes = (group = null, language = 'en', filters = {}) =>
  api.get('/schemes', {
    params: {
      group: group || undefined,
      language,
      audience: filters.audience || undefined,
      need: filters.need || undefined,
      q: filters.q || undefined,
    },
  }).then(r => r.data);

export const fetchSchemeFilters = (language = 'en') =>
  api.get('/schemes/filters', { params: { language } }).then(r => r.data);

export const fetchSchemeById = (schemeId, language = 'en') =>
  api.get(`/schemes/${schemeId}`, { params: { language } }).then(r => r.data);

export const matchSchemes = (profile, language = 'en') =>
  api.post('/schemes/match', profile, { params: { language } }).then(r => r.data);

// ── Guidance ──────────────────────────────────────────────────────────
// history / context: the conversation so far, so follow-ups ("yes", "what documents?", "2") are understood
export const askGuidance = (sessionId, question, language = 'en', history = [], context = {}) =>
  api.post('/guidance/ask', { session_id: sessionId, question, language, history, context }).then(r => r.data);

// ── Fraud ─────────────────────────────────────────────────────────────
export const checkFraud = (sessionId, messageText, language = 'en') =>
  api.post('/fraud/check', { session_id: sessionId, message_text: messageText, language }).then(r => r.data);

// Photo of a message the customer chose to show; OCR runs on the server and can take a few seconds.
// Returns { check_id, extracted_text, classification, ... }; errors carry detail.code (see utils/fraudImage).
export const checkFraudImage = (sessionId, file, language = 'en') =>
  api.post('/fraud/check-image', buildImageFormData(file, sessionId, language), { timeout: 90000 }).then(r => r.data);
