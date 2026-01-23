/**
 * Unit tests for validation module
 */

import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import {
  validateVideoFile,
  validateOutputDir,
  validateNumericOption,
  validateApiKey,
  validateDurationRange,
} from '../../src/validation/index.js';
import { PreflightError } from '../../src/errors/index.js';
import { createTestDir, cleanTestDir } from '../setup.js';
import fs from 'fs-extra';
import path from 'path';

describe('Validation Module', () => {
  let testDir: string;

  beforeEach(async () => {
    testDir = await createTestDir('validation-test');
  });

  afterEach(async () => {
    await cleanTestDir(testDir);
  });

  describe('validateVideoFile', () => {
    it('should validate existing video file', async () => {
      const videoPath = path.join(testDir, 'test.mp4');
      await fs.writeFile(videoPath, 'fake video content');

      await expect(validateVideoFile(videoPath)).resolves.not.toThrow();
    });

    it('should reject non-existent file', async () => {
      try {
        await validateVideoFile('/non/existent/video.mp4');
        expect.fail('Should have thrown PreflightError');
      } catch (error) {
        expect(error).toBeInstanceOf(PreflightError);
        expect((error as PreflightError).code).toBe('VIDEO_NOT_FOUND');
      }
    });

    it('should accept various video formats', async () => {
      const formats = ['mp4', 'mov', 'avi', 'mkv', 'webm'];

      for (const format of formats) {
        const videoPath = path.join(testDir, `test.${format}`);
        await fs.writeFile(videoPath, 'fake video');
        // Ensure file has read permissions
        await fs.chmod(videoPath, 0o644);

        await expect(validateVideoFile(videoPath)).resolves.not.toThrow();
      }
    });

    it('should reject invalid video format', async () => {
      const txtPath = path.join(testDir, 'test.txt');
      await fs.writeFile(txtPath, 'not a video');

      try {
        await validateVideoFile(txtPath);
        expect.fail('Should have thrown PreflightError');
      } catch (error) {
        expect(error).toBeInstanceOf(PreflightError);
        expect((error as PreflightError).code).toBe('INVALID_VIDEO_FORMAT');
      }
    });

    it('should reject directory as video file', async () => {
      const dirPath = path.join(testDir, 'video-dir');
      await fs.ensureDir(dirPath);

      try {
        await validateVideoFile(dirPath);
        expect.fail('Should have thrown PreflightError');
      } catch (error) {
        expect(error).toBeInstanceOf(PreflightError);
        expect((error as PreflightError).code).toBe('INVALID_VIDEO_FORMAT');
      }
    });
  });

  describe('validateNumericOption', () => {
    it('should validate number within range', () => {
      const result = validateNumericOption('50', 'duration', 0, 100);
      expect(result).toBe(50);
    });

    it('should reject non-numeric input', () => {
      try {
        validateNumericOption('abc', 'duration', 0, 100);
        expect.fail('Should have thrown PreflightError');
      } catch (error) {
        expect(error).toBeInstanceOf(PreflightError);
        expect((error as PreflightError).code).toBe('INVALID_OPTION');
      }
    });

    it('should reject value below minimum', () => {
      try {
        validateNumericOption('5', 'duration', 10, 100);
        expect.fail('Should have thrown PreflightError');
      } catch (error) {
        expect(error).toBeInstanceOf(PreflightError);
        expect((error as PreflightError).message).toContain('must be at least 10');
      }
    });

    it('should reject value above maximum', () => {
      try {
        validateNumericOption('150', 'duration', 0, 100);
        expect.fail('Should have thrown PreflightError');
      } catch (error) {
        expect(error).toBeInstanceOf(PreflightError);
        expect((error as PreflightError).message).toContain('must be at most 100');
      }
    });

    it('should return undefined for undefined value', () => {
      const result = validateNumericOption(undefined, 'duration', 0, 100);
      expect(result).toBeUndefined();
    });
  });

  describe('validateApiKey', () => {
    it('should throw if API key is missing', () => {
      const originalKey = process.env.OPENAI_API_KEY;
      delete process.env.OPENAI_API_KEY;

      try {
        validateApiKey();
        expect.fail('Should have thrown PreflightError');
      } catch (error) {
        expect(error).toBeInstanceOf(PreflightError);
        expect((error as PreflightError).code).toBe('API_KEY_MISSING');
      } finally {
        // Restore
        if (originalKey) process.env.OPENAI_API_KEY = originalKey;
      }
    });

    it('should throw if API key has invalid format', () => {
      const originalKey = process.env.OPENAI_API_KEY;
      process.env.OPENAI_API_KEY = 'invalid-key';

      try {
        validateApiKey();
        expect.fail('Should have thrown PreflightError');
      } catch (error) {
        expect(error).toBeInstanceOf(PreflightError);
        expect((error as PreflightError).code).toBe('API_KEY_INVALID');
      } finally {
        // Restore
        if (originalKey) process.env.OPENAI_API_KEY = originalKey;
      }
    });

    it('should accept valid API key format', () => {
      const originalKey = process.env.OPENAI_API_KEY;
      process.env.OPENAI_API_KEY = 'sk-' + 'x'.repeat(48);

      expect(() => validateApiKey()).not.toThrow();

      // Restore
      if (originalKey) process.env.OPENAI_API_KEY = originalKey;
    });
  });

  describe('validateOutputDir', () => {
    it('should create output directory if it does not exist', async () => {
      const outputDir = path.join(testDir, 'new-output');

      await expect(validateOutputDir(outputDir)).resolves.not.toThrow();
      expect(await fs.pathExists(outputDir)).toBe(true);
    });

    it('should accept existing writable directory', async () => {
      const outputDir = path.join(testDir, 'existing-output');
      await fs.ensureDir(outputDir);

      await expect(validateOutputDir(outputDir)).resolves.not.toThrow();
    });
  });

  describe('validateDurationRange', () => {
    it('should accept valid duration range', () => {
      expect(() => validateDurationRange(20, 60)).not.toThrow();
    });

    it('should throw if min >= max', () => {
      expect(() => validateDurationRange(60, 20)).toThrow('must be less than');
    });

    it('should accept undefined values', () => {
      expect(() => validateDurationRange(undefined, 60)).not.toThrow();
      expect(() => validateDurationRange(20, undefined)).not.toThrow();
    });

    it('should accept when both are undefined', () => {
      expect(() => validateDurationRange(undefined, undefined)).not.toThrow();
    });

    it('should throw when min equals max', () => {
      expect(() => validateDurationRange(30, 30)).toThrow('must be less than');
    });
  });
});
