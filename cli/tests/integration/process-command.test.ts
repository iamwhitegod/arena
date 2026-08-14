/**
 * Integration tests for process command
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { createTestDir, cleanTestDir } from '../setup.js';
import fs from 'fs-extra';
import path from 'path';

const { getGlobalConfigMock, runProcessMock } = vi.hoisted(() => ({
  getGlobalConfigMock: vi.fn(),
  runProcessMock: vi.fn(),
}));

// Mock the preflight checks to skip Python validation in tests
vi.mock('../../src/core/preflight.js', () => ({
  runPreflightChecksWithProgress: vi.fn().mockResolvedValue({
    passed: true,
    errors: [],
    warnings: [],
  }),
}));

vi.mock('../../src/core/config.js', () => ({
  ConfigManager: class MockConfigManager {
    ensureGlobalConfig = vi.fn().mockResolvedValue(undefined);
    getGlobalConfig = getGlobalConfigMock;
    createProjectConfig = vi.fn().mockResolvedValue(undefined);
  },
}));

// Mock the Python bridge module
vi.mock('../../src/bridge/python-bridge.js', () => ({
  PythonBridge: class MockPythonBridge {
    getEnginePath() {
      return '/mock/engine/path';
    }

    runProcess = runProcessMock;

    runAnalyze = vi.fn().mockResolvedValue({
      moments: 10,
      videoDuration: 520.3,
      wordCount: 920,
      success: true,
    });

    runTranscribe = vi.fn().mockResolvedValue({
      transcriptPath: '/tmp/transcript.json',
      success: true,
    });

    runGenerate = vi.fn().mockResolvedValue({
      clips: 3,
      success: true,
    });

    runFormat = vi.fn().mockResolvedValue({
      outputPath: '/tmp/formatted.mp4',
      success: true,
    });
  },
}));

// Import after mock is set up
import { processCommand } from '../../src/commands/process.js';

describe('Process Command Integration', () => {
  let testDir: string;
  let exitSpy: any;

  beforeEach(async () => {
    testDir = await createTestDir('process-integration-test');
    getGlobalConfigMock.mockReset().mockResolvedValue({});
    runProcessMock.mockReset().mockResolvedValue({
      clips: [
        {
          title: 'Test Clip 1',
          duration: 45.5,
          start_time: 10.0,
          end_time: 55.5,
        },
      ],
      success: true,
    });
    // Set test API key
    process.env.OPENAI_API_KEY = 'sk-test1234567890abcdef1234567890abcdef12345678';

    // Mock process.exit to prevent tests from exiting
    exitSpy = vi.spyOn(process, 'exit').mockImplementation((code?: any) => {
      throw new Error(`process.exit called with code ${code}`);
    });
  });

  afterEach(async () => {
    await cleanTestDir(testDir);
    delete process.env.OPENAI_API_KEY;
    exitSpy.mockRestore();
  });

  it('should process video with default options', async () => {
    const videoPath = path.join(testDir, 'test.mp4');
    await fs.writeFile(videoPath, 'fake video content');

    const options = {
      output: path.join(testDir, 'output'),
    };

    // This should not throw
    await expect(processCommand(videoPath, options)).resolves.not.toThrow();
  });

  it('should process video with editorial model option', async () => {
    const videoPath = path.join(testDir, 'test.mp4');
    await fs.writeFile(videoPath, 'fake video content');

    const options = {
      output: path.join(testDir, 'output'),
      editorialModel: 'gpt-4o-mini' as const,
      numClips: '5',
    };

    await expect(processCommand(videoPath, options)).resolves.not.toThrow();
  });

  it('should process video with scene detection', async () => {
    const videoPath = path.join(testDir, 'test.mp4');
    await fs.writeFile(videoPath, 'fake video content');

    const options = {
      output: path.join(testDir, 'output'),
      sceneDetection: true,
    };

    await expect(processCommand(videoPath, options)).resolves.not.toThrow();
  });

  it('should process video with custom padding', async () => {
    const videoPath = path.join(testDir, 'test.mp4');
    await fs.writeFile(videoPath, 'fake video content');

    const options = {
      output: path.join(testDir, 'output'),
      padding: '0.5',
    };

    await expect(processCommand(videoPath, options)).resolves.not.toThrow();
  });

  it('should use the configured browser when the command flag is absent', async () => {
    const videoPath = path.join(testDir, 'test.mp4');
    await fs.writeFile(videoPath, 'fake video content');
    getGlobalConfigMock.mockResolvedValue({ cookies_from_browser: 'brave' });

    await processCommand(videoPath, { output: path.join(testDir, 'output') });

    expect(runProcessMock).toHaveBeenCalledWith(
      expect.objectContaining({ cookiesFromBrowser: 'brave' }),
      expect.any(Function),
      expect.any(Function)
    );
  });

  it('should prefer the command browser over the configured browser', async () => {
    const videoPath = path.join(testDir, 'test.mp4');
    await fs.writeFile(videoPath, 'fake video content');
    getGlobalConfigMock.mockResolvedValue({ cookies_from_browser: 'chrome' });

    await processCommand(videoPath, {
      output: path.join(testDir, 'output'),
      cookiesFromBrowser: 'brave',
    });

    expect(runProcessMock).toHaveBeenCalledWith(
      expect.objectContaining({ cookiesFromBrowser: 'brave' }),
      expect.any(Function),
      expect.any(Function)
    );
  });
});
