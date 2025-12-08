/**
 * Application statistics displayed in marketing pages
 */
export const APP_STATS = {
  TOTAL_USERS: '1,500+',
  TOTAL_JOBS: '5,000+',
  SATISFACTION_RATE: '95%'
} as const;

/**
 * Storage keys used throughout the application
 */
export const STORAGE_KEYS = {
  ACCESS_TOKEN: 'access_token',
  REFRESH_TOKEN: 'refresh_token',
  STORAGE_PREFERENCE: 'storage',
  PROFILE_COMPLETE: 'is_profile_complete',
  USER_NAME: 'user_name',
  SELECTED_JOB: 'selected_job',
  REDIRECT_AFTER_LOGIN: 'redirect_after_login',
  MANUAL_PROFILE_DRAFT: 'manual_profile_draft',
  THEME: 'skiltak-theme'
} as const;
