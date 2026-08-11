import { describe, it, expect, vi, beforeEach } from 'vitest';
import { PreflightError } from '../../src/errors/index.js';

// Mock validation functions
const mockValidateVideoFile = vi.fn();
const mockValidateOutputDir = vi.fn();
const mockValidateNumericOption = vi.fn().mockReturnValue(undefined);
const mockValidateApiKey = vi.fn();
const mockValidatePython = vi.fn().mockResolvedValue('Python 3.11.5');
const mockValidateDependencies = vi.fn();
const mockValidateDurationRange = vi.fn();

vi.mock('../../src/validation/index.js', () => ({
  validateVideoFile: (...args: any[]) => mockValidateVideoFile(...args),
  validateOutputDir: (...args: any[]) => mockValidateOutputDir(...args),
  validateNumericOption: (...args: any[]) => mockValidateNumericOption(...args),
  validateApiKey: (...args: any[]) => mockValidateApiKey(...args),
  validatePython: (...args: any[]) => mockValidatePython(...args),
  validateDependencies: (...args: any[]) => mockValidateDependencies(...args),
  validateDurationRange: (...args: any[]) => mockValidateDurationRange(...args),
}));

// Mock ora to avoid spinner output
vi.mock('ora', () => ({
  default: () => ({
    start: vi.fn().mockReturnThis(),
    succeed: vi.fn().mockReturnThis(),
    fail: vi.fn().mockReturnThis(),
    stop: vi.fn().mockReturnThis(),
  }),
}));

// Mock chalk
vi.mock('chalk', () => ({
  default: {
    green: (s: string) => s,
    red: (s: string) => s,
  },
}));

import { runPreflightChecks, runPreflightChecksWithProgress } from '../../src/core/preflight.js';

const baseOptions = {
  videoPath: '/test/video.mp4',
  outputDir: '/test/output',
};

describe('runPreflightChecks', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockValidateVideoFile.mockResolvedValue(undefined);
    mockValidateOutputDir.mockResolvedValue(undefined);
    mockValidateNumericOption.mockReturnValue(undefined);
    mockValidateApiKey.mockReturnValue(undefined);
    mockValidatePython.mockResolvedValue('Python 3.11.5');
    mockValidateDependencies.mockResolvedValue(undefined);
    mockValidateDurationRange.mockReturnValue(undefined);
  });

  it('should return passed=true when all validators pass', async () => {
    const result = await runPreflightChecks(baseOptions);

    expect(result.passed).toBe(true);
    expect(result.errors).toHaveLength(0);
    expect(result.pythonVersion).toBe('Python 3.11.5');
  });

  it('should collect video validation error', async () => {
    mockValidateVideoFile.mockRejectedValue(
      new PreflightError('VIDEO_NOT_FOUND', 'Video file not found')
    );

    const result = await runPreflightChecks(baseOptions);

    expect(result.passed).toBe(false);
    expect(result.errors).toHaveLength(1);
    expect(result.errors[0].code).toBe('VIDEO_NOT_FOUND');
  });

  it('should accumulate multiple errors without short-circuiting', async () => {
    mockValidateVideoFile.mockRejectedValue(
      new PreflightError('VIDEO_NOT_FOUND', 'Video file not found')
    );
    mockValidateOutputDir.mockRejectedValue(
      new PreflightError('OUTPUT_DIR_NOT_WRITABLE', 'Cannot write to output')
    );

    const result = await runPreflightChecks(baseOptions);

    expect(result.passed).toBe(false);
    expect(result.errors).toHaveLength(2);
    expect(result.errors[0].code).toBe('VIDEO_NOT_FOUND');
    expect(result.errors[1].code).toBe('OUTPUT_DIR_NOT_WRITABLE');
  });

  it('should skip API key check when skipApiKeyCheck is true', async () => {
    const result = await runPreflightChecks({
      ...baseOptions,
      skipApiKeyCheck: true,
    });

    expect(result.passed).toBe(true);
    expect(mockValidateApiKey).not.toHaveBeenCalled();
  });

  it('should validate API key by default', async () => {
    await runPreflightChecks(baseOptions);

    expect(mockValidateApiKey).toHaveBeenCalled();
  });

  it('should include python version in result', async () => {
    mockValidatePython.mockResolvedValue('Python 3.9.18');

    const result = await runPreflightChecks(baseOptions);

    expect(result.pythonVersion).toBe('Python 3.9.18');
  });

  it('should check dependencies only when python is available and enginePath provided', async () => {
    await runPreflightChecks({
      ...baseOptions,
      enginePath: '/path/to/engine',
    });

    expect(mockValidateDependencies).toHaveBeenCalledWith('/path/to/engine');
  });

  it('should skip dependency check when no enginePath', async () => {
    await runPreflightChecks(baseOptions);

    expect(mockValidateDependencies).not.toHaveBeenCalled();
  });

  it('should skip dependency check when python is unavailable', async () => {
    mockValidatePython.mockRejectedValue(
      new PreflightError('PYTHON_NOT_FOUND', 'Python not found')
    );

    const result = await runPreflightChecks({
      ...baseOptions,
      enginePath: '/path/to/engine',
    });

    expect(mockValidateDependencies).not.toHaveBeenCalled();
    expect(result.errors.some((e) => e.code === 'PYTHON_NOT_FOUND')).toBe(true);
  });
});

describe('runPreflightChecksWithProgress', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockValidateVideoFile.mockResolvedValue(undefined);
    mockValidateOutputDir.mockResolvedValue(undefined);
    mockValidateNumericOption.mockReturnValue(undefined);
    mockValidateApiKey.mockReturnValue(undefined);
    mockValidatePython.mockResolvedValue('Python 3.11.5');
    mockValidateDependencies.mockResolvedValue(undefined);
    mockValidateDurationRange.mockReturnValue(undefined);
  });

  it('should return passed=true when all checks pass', async () => {
    const result = await runPreflightChecksWithProgress(baseOptions);

    expect(result.passed).toBe(true);
    expect(result.errors).toHaveLength(0);
  });

  it('should return early on video validation failure', async () => {
    mockValidateVideoFile.mockRejectedValue(
      new PreflightError('VIDEO_NOT_FOUND', 'Video file not found')
    );

    const result = await runPreflightChecksWithProgress(baseOptions);

    expect(result.passed).toBe(false);
    expect(result.errors).toHaveLength(1);
    expect(result.errors[0].code).toBe('VIDEO_NOT_FOUND');
    // Should not have continued to check Python
    expect(mockValidatePython).not.toHaveBeenCalled();
  });

  it('should return early on Python failure', async () => {
    mockValidatePython.mockRejectedValue(
      new PreflightError('PYTHON_NOT_FOUND', 'Python not found')
    );

    const result = await runPreflightChecksWithProgress(baseOptions);

    expect(result.passed).toBe(false);
    expect(result.errors[0].code).toBe('PYTHON_NOT_FOUND');
    // Should not have continued to check API key
    expect(mockValidateApiKey).not.toHaveBeenCalled();
  });

  it('should skip API key check when skipApiKeyCheck is true', async () => {
    const result = await runPreflightChecksWithProgress({
      ...baseOptions,
      skipApiKeyCheck: true,
    });

    expect(result.passed).toBe(true);
    expect(mockValidateApiKey).not.toHaveBeenCalled();
  });

  it('should catch numeric option validation errors', async () => {
    mockValidateNumericOption.mockImplementation(() => {
      throw new PreflightError('INVALID_OPTION', 'Invalid numeric value');
    });

    const result = await runPreflightChecksWithProgress({
      ...baseOptions,
      numClips: 'abc',
    });

    expect(result.passed).toBe(false);
    expect(result.errors[0].code).toBe('INVALID_OPTION');
  });
});
