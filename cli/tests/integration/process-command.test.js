/**
 * Integration tests for process command
 */
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { createTestDir, cleanTestDir } from '../setup.js';
import fs from 'fs-extra';
import path from 'path';
// Mock the preflight checks to skip Python validation in tests
vi.mock('../../src/core/preflight.js', () => ({
    runPreflightChecksWithProgress: vi.fn().mockResolvedValue({
        passed: true,
        errors: [],
        warnings: [],
    }),
}));
// Mock the Python bridge module
vi.mock('../../src/bridge/python-bridge.js', () => ({
    PythonBridge: class MockPythonBridge {
        getEnginePath() {
            return '/mock/engine/path';
        }
        runProcess = vi.fn().mockResolvedValue({
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
    let testDir;
    let exitSpy;
    beforeEach(async () => {
        testDir = await createTestDir('process-integration-test');
        // Set test API key
        process.env.OPENAI_API_KEY = 'sk-test1234567890abcdef1234567890abcdef12345678';
        // Mock process.exit to prevent tests from exiting
        exitSpy = vi.spyOn(process, 'exit').mockImplementation((code) => {
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
    it('should process video with 4-layer system', async () => {
        const videoPath = path.join(testDir, 'test.mp4');
        await fs.writeFile(videoPath, 'fake video content');
        const options = {
            output: path.join(testDir, 'output'),
            use4layer: true,
            editorialModel: 'gpt-4o-mini',
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
});
//# sourceMappingURL=process-command.test.js.map