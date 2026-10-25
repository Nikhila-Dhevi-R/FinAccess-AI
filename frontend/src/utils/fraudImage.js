// Helpers for checking a photo of a message (POST /fraud/check-image).
// Kept free of React so they can be unit-tested with `node --test`.

export const ALLOWED_IMAGE_TYPES = ['image/jpeg', 'image/png', 'image/webp', 'image/bmp'];
export const MAX_IMAGE_BYTES = 10 * 1024 * 1024; // matches backend MAX_UPLOAD_SIZE_MB

/** Returns an error code for a file the backend would reject, or null if it looks fine. */
export function validateImageFile(file) {
  if (!file) return 'unreadable_image';
  if (file.size === 0) return 'empty_file';
  if (file.type && !ALLOWED_IMAGE_TYPES.includes(file.type.toLowerCase())) return 'unsupported_type';
  if (!file.type && !/\.(jpe?g|png|webp|bmp)$/i.test(file.name || '')) return 'unsupported_type';
  if (file.size > MAX_IMAGE_BYTES) return 'file_too_large';
  return null;
}

/** Multipart body for the endpoint; session_id is only sent when the kiosk has one. */
export function buildImageFormData(file, sessionId, language) {
  const form = new FormData();
  if (sessionId) form.append('session_id', sessionId);
  if (language) form.append('language', language); // explanation / warning signs come back in this language
  form.append('file', file, file.name || 'message-photo.jpg');
  return form;
}

const KNOWN_CODES = new Set([
  'unsupported_type', 'file_too_large', 'empty_file', 'unreadable_image',
  'no_text_found', 'ocr_unavailable', 'ocr_failed',
]);

/** Maps an axios error from /fraud/check-image to a UI error code. */
export function errorCodeFromApi(err) {
  const detail = err?.response?.data?.detail;
  if (detail && typeof detail === 'object' && KNOWN_CODES.has(detail.code)) return detail.code;
  const status = err?.response?.status;
  if (status === 413) return 'file_too_large';
  if (status === 415) return 'unsupported_type';
  if (!err?.response) return err?.code === 'ECONNABORTED' ? 'timeout' : 'network';
  return 'server';
}

/** Maps a getUserMedia failure to a UI error code. */
export function cameraErrorCode(err) {
  switch (err?.name) {
    case 'NotAllowedError':
    case 'SecurityError':
    case 'PermissionDeniedError':
      return 'permission_denied';
    case 'NotFoundError':
    case 'DevicesNotFoundError':
    case 'OverconstrainedError':
      return 'no_camera';
    default:
      return 'camera_busy';
  }
}

/** Which recovery actions make sense for each error. */
export function recoveryActions(code) {
  if (['permission_denied', 'no_camera', 'camera_unsupported'].includes(code)) return ['choose', 'type'];
  if (code === 'camera_busy') return ['camera', 'choose'];
  if (['unsupported_type', 'file_too_large', 'empty_file', 'unreadable_image'].includes(code)) return ['retake', 'choose'];
  if (['no_text_found', 'ocr_failed'].includes(code)) return ['retake', 'choose', 'type'];
  if (code === 'ocr_unavailable') return ['type'];
  return ['retry', 'retake', 'type']; // network / timeout / server
}
