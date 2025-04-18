/**
 * Logger utility to replace direct console usage.
 * This centralizes logging and allows for easier configuration,
 * enabling/disabling logs by environment, etc.
 */

// Set to true to enable debug logs in development
const IS_DEBUG_ENABLED = process.env.NODE_ENV !== 'production';

export const Logger = {
  /**
   * Info log - use for general information
   */
  info: (message: string, ...data: unknown[]): void => {
    if (IS_DEBUG_ENABLED) {
      console.log(`[INFO] ${message}`, ...data);
    }
  },

  /**
   * Debug log - use for detailed debugging information
   */
  debug: (message: string, ...data: unknown[]): void => {
    if (IS_DEBUG_ENABLED) {
      console.log(`[DEBUG] ${message}`, ...data);
    }
  },

  /**
   * Warning log - use for non-critical issues
   */
  warn: (message: string, ...data: unknown[]): void => {
    console.warn(`[WARN] ${message}`, ...data);
  },

  /**
   * Error log - use for errors and exceptions
   */
  error: (message: string, error?: unknown, ...data: unknown[]): void => {
    console.error(`[ERROR] ${message}`, error, ...data);
  },
};