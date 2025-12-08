/**
 * Match percentage thresholds for job offers
 */
export const MATCH_THRESHOLDS = {
  EXCELLENT: 100,
  GOOD_MIN: 70,
  GOOD_MAX: 99,
  REGULAR_MIN: 50,
  REGULAR_MAX: 69
} as const;

/**
 * Color codes for match percentages
 */
export const MATCH_COLORS = {
  EXCELLENT: '#22c55e',  // green-500
  GOOD: '#3b82f6',       // blue-500
  REGULAR: '#f97315',    // orange-500
  DEFAULT: '#f97315'     // orange-500
} as const;

/**
 * UI constants for hover effects
 */
export const UI_CONSTANTS = {
  HOVER_WIDTH: '99.5%',
  GRADIENT_ANGLE: 180,
  GRADIENT_END_ANGLE: 120
} as const;
