/**
 * Unit tests for workspace module
 */

import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { Workspace } from '../../src/core/workspace.js';
import { createTestDir, cleanTestDir } from '../setup.js';
import fs from 'fs-extra';
import path from 'path';

describe('Workspace', () => {
  let testDir: string;
  let workspace: Workspace;
  let originalCwd: string;

  beforeEach(async () => {
    originalCwd = process.cwd();
    testDir = await createTestDir('workspace-test');
    // Change to test directory
    process.chdir(testDir);
    workspace = new Workspace();
  });

  afterEach(async () => {
    // Restore original working directory before cleanup
    process.chdir(originalCwd);
    await cleanTestDir(testDir);
  });

  it('should initialize workspace directory structure', async () => {
    await workspace.initialize();

    // Check main workspace directory
    expect(await fs.pathExists(path.join(testDir, '.arena'))).toBe(true);
  });

  it('should create workspace in custom location', async () => {
    const customDir = path.join(testDir, 'custom-workspace');
    workspace = new Workspace(customDir);
    await workspace.initialize();

    expect(await fs.pathExists(customDir)).toBe(true);
  });

  it('should return correct workspace paths', async () => {
    await workspace.initialize();

    const cachePath = workspace.getCachePath('test.json');
    const outputPath = workspace.getOutputPath('test.mp4');
    const clipPath = workspace.getClipPath('clip.mp4');

    expect(cachePath).toContain('.arena');
    expect(cachePath).toContain('cache');
    expect(outputPath).toContain('output');
    expect(clipPath).toContain('clips');
  });

  it('should handle re-initialization gracefully', async () => {
    await workspace.initialize();
    await workspace.initialize();

    // Should not throw and directory should still exist
    expect(await workspace.exists()).toBe(true);
  });

  it('should create all subdirectories', async () => {
    await workspace.initialize();

    const dirs = [
      path.join(testDir, '.arena'),
      path.join(testDir, '.arena', 'cache'),
      path.join(testDir, '.arena', 'output'),
      path.join(testDir, '.arena', 'output', 'clips'),
    ];

    for (const dir of dirs) {
      expect(await fs.pathExists(dir)).toBe(true);
    }
  });

  it('should save and load cache', async () => {
    await workspace.initialize();

    const testData = { test: 'data', value: 123 };
    await workspace.saveCache('test.json', testData);

    expect(await workspace.hasCache('test.json')).toBe(true);

    const loaded = await workspace.loadCache('test.json');
    expect(loaded).toEqual(testData);
  });

  it('should return null for non-existent cache', async () => {
    await workspace.initialize();

    const loaded = await workspace.loadCache('non-existent.json');
    expect(loaded).toBeNull();
  });

  it('should clean workspace', async () => {
    await workspace.initialize();
    expect(await workspace.exists()).toBe(true);

    await workspace.clean();
    expect(await workspace.exists()).toBe(false);
  });
});
