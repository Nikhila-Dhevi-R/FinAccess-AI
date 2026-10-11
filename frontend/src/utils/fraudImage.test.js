import { expect, test } from 'vitest';
import {
  validateImageFile, buildImageFormData, errorCodeFromApi, cameraErrorCode, recoveryActions, MAX_IMAGE_BYTES,
} from './fraudImage.js';

const file = (name, type, size) => ({ name, type, size });

test('accepts supported photos', () => {
  expect(validateImageFile(file('a.jpg', 'image/jpeg', 2000))).toBeNull();
  expect(validateImageFile(file('a.png', 'image/png', 2000))).toBeNull();
  expect(validateImageFile(file('a.webp', '', 2000))).toBeNull(); // some devices omit the MIME type
});

test('rejects unsupported, empty and oversized files before upload', () => {
  expect(validateImageFile(file('a.gif', 'image/gif', 2000))).toBe('unsupported_type');
  expect(validateImageFile(file('a.pdf', 'application/pdf', 2000))).toBe('unsupported_type');
  expect(validateImageFile(file('notes', '', 2000))).toBe('unsupported_type');
  expect(validateImageFile(file('a.jpg', 'image/jpeg', 0))).toBe('empty_file');
  expect(validateImageFile(file('a.jpg', 'image/jpeg', MAX_IMAGE_BYTES + 1))).toBe('file_too_large');
  expect(validateImageFile(null)).toBe('unreadable_image');
});

test('builds multipart form data with session_id only when present', () => {
  const photo = new Blob(['x'], { type: 'image/jpeg' });
  photo.name = 'photo.jpg';
  const withSession = buildImageFormData(photo, 'sess-1', 'hi');
  expect(withSession.get('session_id')).toBe('sess-1');
  expect(withSession.get('language')).toBe('hi');
  expect(withSession.get('file')).toBeTruthy();
  const without = buildImageFormData(photo, null);
  expect(without.get('session_id')).toBeNull();
  expect(without.get('file')).toBeTruthy();
});

test('maps backend error details and transport failures', () => {
  const api = (status, detail) => ({ response: { status, data: { detail } } });
  expect(errorCodeFromApi(api(422, { code: 'no_text_found', message: 'x' }))).toBe('no_text_found');
  expect(errorCodeFromApi(api(503, { code: 'ocr_unavailable', message: 'x' }))).toBe('ocr_unavailable');
  expect(errorCodeFromApi(api(413, 'Request Entity Too Large'))).toBe('file_too_large');
  expect(errorCodeFromApi(api(500, 'boom'))).toBe('server');
  expect(errorCodeFromApi({ code: 'ECONNABORTED' })).toBe('timeout');
  expect(errorCodeFromApi({ message: 'Network Error' })).toBe('network');
});

test('maps camera failures and never offers a dead end', () => {
  expect(cameraErrorCode({ name: 'NotAllowedError' })).toBe('permission_denied');
  expect(cameraErrorCode({ name: 'NotFoundError' })).toBe('no_camera');
  expect(cameraErrorCode({ name: 'NotReadableError' })).toBe('camera_busy');
  for (const code of ['permission_denied', 'no_camera', 'camera_busy', 'unsupported_type', 'file_too_large',
    'unreadable_image', 'no_text_found', 'ocr_unavailable', 'ocr_failed', 'network', 'server', 'timeout']) {
    expect(recoveryActions(code).length, code).toBeGreaterThan(0);
  }
  // OCR failures must point the customer to another way of checking, not to a result
  expect(recoveryActions('no_text_found')).toContain('type');
  expect(recoveryActions('ocr_unavailable')).toContain('type');
});
