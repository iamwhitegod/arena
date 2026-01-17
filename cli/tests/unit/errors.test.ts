import { describe, it, expect } from 'vitest';
import {
  PreflightError,
  ProcessingError,
  SystemError,
  isArenaError,
} from '../../src/errors/index.js';
import { formatErrorWithHelp } from '../../src/errors/formatter.js';

describe('Error Classes', () => {
  describe('PreflightError', () => {
    it('should create preflight error with code and message', () => {
      const error = new PreflightError(
        'VIDEO_NOT_FOUND',
        'Video file not found',
        'Check the file path'
      );

      expect(error.code).toBe('VIDEO_NOT_FOUND');
      expect(error.message).toBe('Video file not found');
      expect(error.suggestion).toBe('Check the file path');
      expect(error.name).toBe('PreflightError');
    });

    it('should support optional docs URL', () => {
      const error = new PreflightError(
        'API_KEY_MISSING',
        'API key not found',
        'Set OPENAI_API_KEY',
        'https://docs.arena.com/api-key'
      );

      expect(error.docsUrl).toBe('https://docs.arena.com/api-key');
    });
  });

  describe('ProcessingError', () => {
    it('should create processing error', () => {
      const error = new ProcessingError(
        'TRANSCRIPTION_FAILED',
        'Failed to transcribe audio',
        'Check your API key'
      );

      expect(error.code).toBe('TRANSCRIPTION_FAILED');
      expect(error.message).toBe('Failed to transcribe audio');
      expect(error.suggestion).toBe('Check your API key');
      expect(error.name).toBe('ProcessingError');
    });
  });

  describe('SystemError', () => {
    it('should create system error', () => {
      const error = new SystemError(
        'DISK_FULL',
        'Not enough disk space',
        'Free up some space'
      );

      expect(error.code).toBe('DISK_FULL');
      expect(error.message).toBe('Not enough disk space');
      expect(error.suggestion).toBe('Free up some space');
      expect(error.name).toBe('SystemError');
    });
  });

  describe('isArenaError', () => {
    it('should identify Arena errors', () => {
      const preflightError = new PreflightError('TEST', 'Test message');
      const processingError = new ProcessingError('TEST', 'Test message');
      const systemError = new SystemError('TEST', 'Test message');

      expect(isArenaError(preflightError)).toBe(true);
      expect(isArenaError(processingError)).toBe(true);
      expect(isArenaError(systemError)).toBe(true);
    });

    it('should reject non-Arena errors', () => {
      const regularError = new Error('Regular error');
      const typeError = new TypeError('Type error');

      expect(isArenaError(regularError)).toBe(false);
      expect(isArenaError(typeError)).toBe(false);
      expect(isArenaError(null)).toBe(false);
      expect(isArenaError(undefined)).toBe(false);
    });
  });
});

describe('Error Formatter', () => {
  describe('formatErrorWithHelp', () => {
    it('should format preflight error', () => {
      const error = new PreflightError(
        'VIDEO_NOT_FOUND',
        'Video file not found: video.mp4',
        'Check the file path and try again'
      );

      const formatted = formatErrorWithHelp(error);

      expect(formatted).toContain('✗'); // Error symbol
      expect(formatted).toContain('Video file not found');
      expect(formatted).toContain('Check the file path');
    });

    it('should format error with docs URL', () => {
      const error = new PreflightError(
        'API_KEY_MISSING',
        'OpenAI API key not set',
        'Set OPENAI_API_KEY environment variable',
        'https://platform.openai.com/api-keys'
      );

      const formatted = formatErrorWithHelp(error);

      expect(formatted).toContain('OpenAI API key not set');
      expect(formatted).toContain('platform.openai.com/api-keys');
    });

    it('should include debug info when debug flag is true', () => {
      const error = new PreflightError('TEST', 'Test error');
      error.stack = 'Error: Test error\n  at test.js:1:1';

      const formatted = formatErrorWithHelp(error, true);

      expect(formatted).toContain('Stack trace');
      expect(formatted).toContain('test.js:1:1');
    });

    it('should not include debug info when debug flag is false', () => {
      const error = new PreflightError('TEST', 'Test error');
      error.stack = 'Error: Test error\n  at test.js:1:1';

      const formatted = formatErrorWithHelp(error, false);

      expect(formatted).not.toContain('Stack trace');
      expect(formatted).not.toContain('test.js:1:1');
    });

    it('should handle processing errors', () => {
      const error = new ProcessingError(
        'PROCESSING_FAILED',
        'Failed to generate clips',
        'Check the error message above'
      );

      const formatted = formatErrorWithHelp(error);

      expect(formatted).toContain('✗'); // Error symbol
      expect(formatted).toContain('Failed to generate clips');
      expect(formatted).toContain('Check the error message above');
    });

    it('should handle system errors', () => {
      const error = new SystemError(
        'INTERRUPTED',
        'Process was interrupted by user',
        'This is normal if you pressed Ctrl+C'
      );

      const formatted = formatErrorWithHelp(error);

      expect(formatted).toContain('✗'); // Error symbol
      expect(formatted).toContain('interrupted by user');
      expect(formatted).toContain('Ctrl+C');
    });

    it('should add contextual help for API_KEY_MISSING', () => {
      const error = new PreflightError(
        'API_KEY_MISSING',
        'OpenAI API key not found'
      );

      const formatted = formatErrorWithHelp(error);

      expect(formatted).toContain('Get an API key');
      expect(formatted).toContain('export OPENAI_API_KEY');
      expect(formatted).toContain('arena process video.mp4');
    });
  });
});
