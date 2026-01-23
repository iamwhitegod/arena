/**
 * E2E tests for complete workflow
 * Note: These tests require actual Python engine and may take longer
 */
import { describe, it, expect, beforeAll, afterAll } from 'vitest';
import { createTestDir, cleanTestDir } from '../setup.js';
import { exec } from 'child_process';
import { promisify } from 'util';
import path from 'path';
import fs from 'fs-extra';
const execAsync = promisify(exec);
describe('Full Workflow E2E', () => {
    let testDir;
    const CLI_PATH = path.join(__dirname, '../../dist/index.js');
    beforeAll(async () => {
        testDir = await createTestDir('e2e-workflow-test');
    });
    afterAll(async () => {
        await cleanTestDir(testDir);
    });
    it('should display help', async () => {
        const { stdout } = await execAsync(`node "${CLI_PATH}" --help`);
        expect(stdout).toContain('AI-powered video clip generation');
        expect(stdout).toContain('Commands:');
        expect(stdout).toContain('process');
        expect(stdout).toContain('analyze');
        expect(stdout).toContain('format');
    });
    it('should display version', async () => {
        const { stdout } = await execAsync(`node "${CLI_PATH}" --version`);
        expect(stdout).toMatch(/\d+\.\d+\.\d+/);
    });
    it('should show command-specific help', async () => {
        const { stdout } = await execAsync(`node "${CLI_PATH}" process --help`);
        expect(stdout).toContain('Process a video');
        expect(stdout).toContain('--use-4layer');
        expect(stdout).toContain('--scene-detection');
    });
    // This test is skipped by default as it requires a real video file
    it.skip('should process a real video file', async () => {
        // This would require a test video file
        const testVideo = path.join(testDir, 'test-video.mp4');
        const outputDir = path.join(testDir, 'output');
        // Set API key
        process.env.OPENAI_API_KEY = 'your-test-api-key';
        const command = `node "${CLI_PATH}" process "${testVideo}" -o "${outputDir}" -n 1`;
        const { stdout } = await execAsync(command);
        expect(stdout).toContain('Processing video');
        expect(await fs.pathExists(outputDir)).toBe(true);
    }, 300000); // 5 minute timeout
});
//# sourceMappingURL=full-workflow.test.js.map