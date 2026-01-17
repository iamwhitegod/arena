import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import fs from 'fs-extra';
import path from 'path';
import os from 'os';
import {
  validateVideoFile,
  validateOutputDir,
  validateNumericOption,
  validateApiKey,
  validateDurationRange,
} from '../../src/validation/index.js';
import { PreflightError } from '../../src/errors/index.js';

describe('Validation', () => {
  let tempDir: string;

  beforeEach(async () => {
    // Create temp directory for tests
    tempDir = path.join(os.tmpdir(), `arena-test-${Date.now()}`);
    await fs.ensureDir(tempDir);
  });

  afterEach(async () => {
    // Clean up temp directory
    await fs.remove(tempDir);
  });

  describe('validateVideoFile', () => {
    it('should pass for existing video file', async () => {
      const videoPath = path.join(tempDir, 'test.mp4');
      await fs.writeFile(videoPath, 'fake video content');

      await expect(validateVideoFile(videoPath)).resolves.not.toThrow();
    });

    it('should throw for non-existent file', async () => {
      const videoPath = path.join(tempDir, 'nonexistent.mp4');

      await expect(validateVideoFile(videoPath)).rejects.toThrow(PreflightError);
      await expect(validateVideoFile(videoPath)).rejects.toThrow('not found');
    });

    it('should throw for directory instead of file', async () => {
      const dirPath = path.join(tempDir, 'video-dir');
      await fs.ensureDir(dirPath);

      await expect(validateVideoFile(dirPath)).rejects.toThrow(PreflightError);
      await expect(validateVideoFile(dirPath)).rejects.toThrow('not a file');
    });

    it('should throw for unsupported video extension', async () => {
      const textPath = path.join(tempDir, 'test.txt');
      await fs.writeFile(textPath, 'text content');

      await expect(validateVideoFile(textPath)).rejects.toThrow(PreflightError);
      await expect(validateVideoFile(textPath)).rejects.toThrow('Unsupported video format');
    });

    it('should accept valid video extensions', async () => {
      const extensions = ['.mp4', '.mov', '.avi', '.mkv', '.webm'];

      for (const ext of extensions) {
        const videoPath = path.join(tempDir, `test${ext}`);
        await fs.writeFile(videoPath, 'fake video content');
        await expect(validateVideoFile(videoPath)).resolves.not.toThrow();
      }
    });
  });

  describe('validateOutputDir', () => {
    it('should pass for existing directory', async () => {
      const outputDir = path.join(tempDir, 'output');
      await fs.ensureDir(outputDir);

      await expect(validateOutputDir(outputDir)).resolves.not.toThrow();
    });

    it('should create non-existent directory', async () => {
      const outputDir = path.join(tempDir, 'new-output');

      await expect(validateOutputDir(outputDir)).resolves.not.toThrow();
      expect(await fs.pathExists(outputDir)).toBe(true);
    });

    it('should pass even if directory already exists', async () => {
      const outputDir = path.join(tempDir, 'existing-output');
      await fs.ensureDir(outputDir);

      await expect(validateOutputDir(outputDir)).resolves.not.toThrow();
    });
  });

  describe('validateNumericOption', () => {
    it('should return number for valid value in range', () => {
      const result = validateNumericOption('50', 'duration', 10, 100);

      expect(result).toBe(50);
    });

    it('should throw for non-numeric value', () => {
      expect(() => validateNumericOption('abc', 'duration', 10, 100)).toThrow(PreflightError);
      expect(() => validateNumericOption('abc', 'duration', 10, 100)).toThrow('Invalid value');
    });

    it('should throw for value below minimum', () => {
      expect(() => validateNumericOption('5', 'duration', 10, 100)).toThrow(PreflightError);
      expect(() => validateNumericOption('5', 'duration', 10, 100)).toThrow('at least 10');
    });

    it('should throw for value above maximum', () => {
      expect(() => validateNumericOption('150', 'duration', 10, 100)).toThrow(PreflightError);
      expect(() => validateNumericOption('150', 'duration', 10, 100)).toThrow('at most 100');
    });

    it('should return value at boundaries', () => {
      const resultMin = validateNumericOption('10', 'duration', 10, 100);
      const resultMax = validateNumericOption('100', 'duration', 10, 100);

      expect(resultMin).toBe(10);
      expect(resultMax).toBe(100);
    });

    it('should return undefined for undefined value', () => {
      const result = validateNumericOption(undefined, 'duration', 10, 100);

      expect(result).toBeUndefined();
    });

    it('should accept decimal numbers', () => {
      const result = validateNumericOption('45.5', 'padding', 0, 100);

      expect(result).toBe(45.5);
    });
  });

  describe('validateApiKey', () => {
    const originalEnv = process.env.OPENAI_API_KEY;

    afterEach(() => {
      // Restore original env
      if (originalEnv) {
        process.env.OPENAI_API_KEY = originalEnv;
      } else {
        delete process.env.OPENAI_API_KEY;
      }
    });

    it('should pass when valid API key is set', () => {
      process.env.OPENAI_API_KEY = 'sk-' + 'a'.repeat(45); // Valid length key

      expect(() => validateApiKey()).not.toThrow();
    });

    it('should throw when API key is not set', () => {
      delete process.env.OPENAI_API_KEY;

      expect(() => validateApiKey()).toThrow(PreflightError);
      expect(() => validateApiKey()).toThrow('not found');
    });

    it('should throw when API key is empty string', () => {
      process.env.OPENAI_API_KEY = '';

      expect(() => validateApiKey()).toThrow(PreflightError);
      expect(() => validateApiKey()).toThrow('not found');
    });

    it('should throw when API key does not start with sk-', () => {
      process.env.OPENAI_API_KEY = 'invalid-key-format';

      expect(() => validateApiKey()).toThrow(PreflightError);
      expect(() => validateApiKey()).toThrow('invalid format');
    });

    it('should throw when API key is too short', () => {
      process.env.OPENAI_API_KEY = 'sk-short';

      expect(() => validateApiKey()).toThrow(PreflightError);
      expect(() => validateApiKey()).toThrow('incomplete');
    });
  });

  describe('validateDurationRange', () => {
    it('should pass when min < max', () => {
      expect(() => validateDurationRange(30, 90)).not.toThrow();
    });

    it('should throw when min >= max', () => {
      expect(() => validateDurationRange(90, 30)).toThrow(PreflightError);
      expect(() => validateDurationRange(90, 30)).toThrow('must be less than maximum');
    });

    it('should throw when min == max', () => {
      expect(() => validateDurationRange(60, 60)).toThrow(PreflightError);
    });

    it('should pass when only min is provided', () => {
      expect(() => validateDurationRange(30, undefined)).not.toThrow();
    });

    it('should pass when only max is provided', () => {
      expect(() => validateDurationRange(undefined, 90)).not.toThrow();
    });

    it('should pass when neither is provided', () => {
      expect(() => validateDurationRange(undefined, undefined)).not.toThrow();
    });
  });
});
