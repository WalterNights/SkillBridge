/**
 * Match percentage thresholds for job offers.
 *
 * Recalibrado junto con el rewrite del matcher (Julio 2026): la formula
 * pasa a `title_score - skill_penalty`. Con esa formula el 100 es raro
 * (exige title exacto + todas las skills) y matches por debajo de 40 son
 * ruido — corresponden con el threshold del feed backend
 * (`min_match_percentage=40`).
 *
 * Tiers:
 *   EXCELLENT: 80-100  → borde/pill naranja fuerte
 *   GOOD:      60-79   → tier medio-alto
 *   REGULAR:   40-59   → tier bajo (pero sigue en feed)
 *   <40                → filtrado por el backend, no aparece
 */
export const MATCH_THRESHOLDS = {
  EXCELLENT: 80,
  GOOD_MIN: 60,
  GOOD_MAX: 79,
  REGULAR_MIN: 40,
  REGULAR_MAX: 59,
} as const;

/**
 * Color codes for match percentages
 */
export const MATCH_COLORS = {
  EXCELLENT: '#22c55e', // green-500
  GOOD: '#3b82f6', // blue-500
  REGULAR: '#f97315', // orange-500
  DEFAULT: '#f97315', // orange-500
} as const;

/**
 * UI constants for hover effects
 */
export const UI_CONSTANTS = {
  HOVER_WIDTH: '99.5%',
  GRADIENT_ANGLE: 180,
  GRADIENT_END_ANGLE: 120,
} as const;
