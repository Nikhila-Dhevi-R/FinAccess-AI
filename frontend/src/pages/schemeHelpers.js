const BUILT_IN_OCCUPATIONS = new Set(['farmer', 'laborer', 'self_employed', 'student', 'unemployed', 'other']);

export function isCustomOccupation(value) {
  return Boolean(value && !BUILT_IN_OCCUPATIONS.has(value));
}

export function normalizeOtherCategory(text) {
  return (text || '')
    .trim()
    .replace(/^(?:i am|i'm|i work as|my work is)\s+(?:a\s+|an\s+)?/i, '')
    .replace(/[.,!?]+$/, '')
    .trim();
}

export function splitSchemeMatches(schemes, limit = 5) {
  const safeSchemes = Array.isArray(schemes) ? schemes : [];
  return {
    top: safeSchemes.slice(0, limit),
    others: safeSchemes.slice(limit),
  };
}
