/**
 * Error formatting utilities for Arena CLI
 * Formats errors into user-friendly, actionable messages
 */

import chalk from 'chalk';
import { isArenaError, PreflightError, ProcessingError, SystemError } from './index.js';

interface FormattedError {
  title: string;
  message: string;
  suggestion?: string;
  docsUrl?: string;
  stack?: string;
}

/**
 * Format any error into a user-friendly message
 * @param error - The error to format
 * @param debug - Whether to include stack traces
 * @returns Formatted error string
 */
export function formatError(error: unknown, debug = false): string {
  const formatted = extractErrorInfo(error);

  let output = '';

  // Error title (red X + type)
  output += chalk.red(`\n✗ ${formatted.title}\n`);

  // Main error message (indented)
  output += chalk.white(`\n  ${formatted.message}\n`);

  // Suggestion (if available)
  if (formatted.suggestion) {
    output += chalk.yellow(`\n  → ${formatted.suggestion}\n`);
  }

  // Documentation link (if available)
  if (formatted.docsUrl) {
    output += chalk.gray(`\n  📚 Learn more: ${formatted.docsUrl}\n`);
  }

  // Stack trace (debug mode only)
  if (debug && formatted.stack) {
    output += chalk.gray(`\n  Stack trace:\n`);
    output += chalk.gray(formatted.stack.split('\n').map(line => `    ${line}`).join('\n'));
    output += '\n';
  }

  return output;
}

/**
 * Extract error information for formatting
 */
function extractErrorInfo(error: unknown): FormattedError {
  if (isArenaError(error)) {
    return {
      title: formatErrorType(error),
      message: error.message,
      suggestion: error.suggestion,
      docsUrl: error.docsUrl,
      stack: error.stack,
    };
  }

  if (error instanceof Error) {
    return {
      title: 'An unexpected error occurred',
      message: error.message,
      stack: error.stack,
    };
  }

  return {
    title: 'An unexpected error occurred',
    message: String(error),
  };
}

/**
 * Format error type into user-friendly title
 */
function formatErrorType(error: PreflightError | ProcessingError | SystemError): string {
  if (error instanceof PreflightError) {
    return formatPreflightErrorTitle(error.code);
  }
  if (error instanceof ProcessingError) {
    return formatProcessingErrorTitle(error.code);
  }
  if (error instanceof SystemError) {
    return formatSystemErrorTitle(error.code);
  }
  return 'Error';
}

/**
 * Format preflight error codes into titles
 */
function formatPreflightErrorTitle(code: string): string {
  const titles: Record<string, string> = {
    VIDEO_NOT_FOUND: 'Video file not found',
    INVALID_VIDEO_FORMAT: 'Invalid video format',
    OUTPUT_DIR_NOT_WRITABLE: 'Output directory is not writable',
    PYTHON_NOT_FOUND: 'Python not found',
    DEPENDENCIES_MISSING: 'Python dependencies missing',
    API_KEY_MISSING: 'OpenAI API key not set',
    API_KEY_INVALID: 'OpenAI API key is invalid',
    INVALID_OPTION: 'Invalid command option',
  };

  return titles[code] || 'Validation failed';
}

/**
 * Format processing error codes into titles
 */
function formatProcessingErrorTitle(code: string): string {
  const titles: Record<string, string> = {
    TRANSCRIPTION_FAILED: 'Transcription failed',
    ANALYSIS_FAILED: 'Analysis failed',
    CLIP_GENERATION_FAILED: 'Clip generation failed',
    API_RATE_LIMIT: 'API rate limit exceeded',
    API_ERROR: 'API error',
    TIMEOUT: 'Processing timed out',
    NO_CLIPS_GENERATED: 'No clips generated',
  };

  return titles[code] || 'Processing failed';
}

/**
 * Format system error codes into titles
 */
function formatSystemErrorTitle(code: string): string {
  const titles: Record<string, string> = {
    DISK_FULL: 'Disk is full',
    PERMISSION_DENIED: 'Permission denied',
    NETWORK_ERROR: 'Network error',
    OUT_OF_MEMORY: 'Out of memory',
    PYTHON_CRASHED: 'Python process crashed',
  };

  return titles[code] || 'System error';
}

/**
 * Format error with context and help for specific error codes
 */
export function formatErrorWithHelp(error: unknown, debug = false): string {
  if (!isArenaError(error)) {
    return formatError(error, debug);
  }

  // Add contextual help based on error code
  const helpText = getHelpText(error.code);
  if (!helpText) {
    return formatError(error, debug);
  }

  let output = formatError(error, debug);
  output += '\n' + helpText;

  return output;
}

/**
 * Get contextual help text for specific error codes
 */
function getHelpText(code: string): string | null {
  const helpTexts: Record<string, string> = {
    API_KEY_MISSING: chalk.yellow(
      '  → Get an API key:\n' +
      '    https://platform.openai.com/api-keys\n\n' +
      '  → Set it in one of these ways:\n\n' +
      '    1. Environment variable:\n' +
      chalk.cyan('       export OPENAI_API_KEY="sk-..."\n\n') +
      '    2. Config file (~/.arena/config.json):\n' +
      chalk.cyan('       {\n' +
      '         "openai_api_key": "sk-..."\n' +
      '       }\n\n') +
      '  → Then try again:\n' +
      chalk.cyan('    arena process video.mp4\n')
    ),

    DEPENDENCIES_MISSING: chalk.yellow(
      '  → Install dependencies:\n\n' +
      chalk.cyan('    cd engine && pip install -r requirements.txt\n\n') +
      '  → Or use a virtual environment:\n\n' +
      chalk.cyan('    python3 -m venv venv\n' +
      '    source venv/bin/activate\n' +
      '    pip install -r engine/requirements.txt\n')
    ),

    PYTHON_NOT_FOUND: chalk.yellow(
      '  → Install Python 3.9 or higher:\n\n' +
      '    macOS: brew install python3\n' +
      '    Ubuntu: sudo apt install python3\n\n' +
      '  → Or use pyenv for version management:\n\n' +
      chalk.cyan('    curl https://pyenv.run | bash\n' +
      '    pyenv install 3.11\n')
    ),

    NO_CLIPS_GENERATED: chalk.yellow(
      '  → This usually means:\n\n' +
      '    1. Video is too short (< 30 seconds)\n' +
      '    2. No interesting moments detected\n' +
      '    3. All clips failed quality validation\n\n' +
      '  → Try:\n\n' +
      '    1. Use a longer video (> 2 minutes)\n' +
      '    2. Lower min duration: ' + chalk.cyan('--min 15\n') +
      '    3. Disable 4-layer validation temporarily\n' +
      '    4. Export layers to debug: ' + chalk.cyan('--export-layers\n')
    ),
  };

  return helpTexts[code] || null;
}

/**
 * Create a formatted error summary
 * Useful for displaying multiple errors at once
 */
export function formatErrorSummary(errors: unknown[]): string {
  if (errors.length === 0) {
    return '';
  }

  if (errors.length === 1) {
    return formatErrorWithHelp(errors[0]);
  }

  let output = chalk.red(`\n✗ ${errors.length} errors found:\n`);

  errors.forEach((error, index) => {
    const formatted = extractErrorInfo(error);
    output += chalk.gray(`\n${index + 1}. `) + chalk.white(formatted.title);
    output += chalk.gray(`\n   ${formatted.message}\n`);
  });

  output += chalk.yellow('\n  → Fix these issues and try again\n');

  return output;
}
