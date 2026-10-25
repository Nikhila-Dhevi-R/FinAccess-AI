import { describe, expect, test } from 'vitest';
import { isCustomOccupation, normalizeOtherCategory, splitSchemeMatches } from './schemeHelpers';

describe('custom scheme categories', () => {
  test('recognizes Others values without confusing built-in occupations', () => {
    expect(isCustomOccupation('street vendor')).toBe(true);
    expect(isCustomOccupation('farmer')).toBe(false);
    expect(isCustomOccupation('self_employed')).toBe(false);
  });

  test('normalizes a spoken custom category into a useful catalogue value', () => {
    expect(normalizeOtherCategory('I am a street vendor')).toBe('street vendor');
    expect(normalizeOtherCategory('  artisan  ')).toBe('artisan');
  });

  test('keeps only five matches visible until the user asks for more', () => {
    const schemes = Array.from({ length: 8 }, (_, index) => ({ scheme_id: `scheme-${index}` }));
    const result = splitSchemeMatches(schemes);
    expect(result.top).toHaveLength(5);
    expect(result.others).toHaveLength(3);
  });
});
