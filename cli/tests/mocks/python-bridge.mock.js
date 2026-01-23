/**
 * Mock Python Bridge for testing
 */
import { vi } from 'vitest';
export class MockPythonBridge {
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
        transcript: 'Test transcript content',
        duration: 520.3,
        wordCount: 920,
        success: true,
    });
    runGenerate = vi.fn().mockResolvedValue({
        clipsGenerated: 3,
        success: true,
    });
    runFormat = vi.fn().mockResolvedValue({
        formatted: 1,
        success: true,
    });
    runDetectScenes = vi.fn().mockResolvedValue({
        sceneCount: 15,
        avgSceneDuration: 34.5,
        success: true,
    });
    getEnginePath = vi.fn().mockReturnValue('/mock/engine/path');
    checkPythonEnvironment = vi.fn().mockResolvedValue({
        available: true,
        version: 'Python 3.11.0',
    });
    checkDependencies = vi.fn().mockResolvedValue({
        installed: true,
    });
}
//# sourceMappingURL=python-bridge.mock.js.map