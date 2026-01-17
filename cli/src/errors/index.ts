/**
 * Error handling framework for Arena CLI
 * Provides structured error types and formatting
 */

/**
 * Error for pre-flight validation failures
 * Used before processing starts (e.g., file not found, missing dependencies)
 */
export class PreflightError extends Error {
  constructor(
    public code: string,
    message: string,
    public suggestion?: string,
    public docsUrl?: string
  ) {
    super(message);
    this.name = 'PreflightError';
    Error.captureStackTrace(this, this.constructor);
  }
}

/**
 * Error during video processing
 * Used when processing fails (e.g., API errors, timeouts, transcription failures)
 */
export class ProcessingError extends Error {
  constructor(
    public code: string,
    message: string,
    public suggestion?: string,
    public docsUrl?: string
  ) {
    super(message);
    this.name = 'ProcessingError';
    Error.captureStackTrace(this, this.constructor);
  }
}

/**
 * Unexpected system-level errors
 * Used for disk full, permissions, network issues
 */
export class SystemError extends Error {
  constructor(
    public code: string,
    message: string,
    public suggestion?: string,
    public docsUrl?: string
  ) {
    super(message);
    this.name = 'SystemError';
    Error.captureStackTrace(this, this.constructor);
  }
}

/**
 * Type guard to check if error is an Arena error type
 */
export function isArenaError(
  error: unknown
): error is PreflightError | ProcessingError | SystemError {
  return (
    error instanceof PreflightError ||
    error instanceof ProcessingError ||
    error instanceof SystemError
  );
}

/**
 * Extract error code from any error
 */
export function getErrorCode(error: unknown): string {
  if (isArenaError(error)) {
    return error.code;
  }
  if (error instanceof Error) {
    return 'UNKNOWN_ERROR';
  }
  return 'UNEXPECTED_ERROR';
}

/**
 * Extract error message from any error
 */
export function getErrorMessage(error: unknown): string {
  if (error instanceof Error) {
    return error.message;
  }
  return String(error);
}
