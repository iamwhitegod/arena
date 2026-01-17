import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import fs from 'fs-extra';
import path from 'path';
import os from 'os';
import { ConfigManager } from '../../src/core/config.js';

describe('ConfigManager', () => {
  let tempHomeDir: string;
  let tempProjectDir: string;
  let originalHome: string;
  let originalCwd: string;

  beforeEach(async () => {
    // Save original paths
    originalHome = os.homedir();
    originalCwd = process.cwd();

    // Create temp directories
    tempHomeDir = path.join(os.tmpdir(), `arena-home-${Date.now()}`);
    tempProjectDir = path.join(os.tmpdir(), `arena-project-${Date.now()}`);

    await fs.ensureDir(tempHomeDir);
    await fs.ensureDir(tempProjectDir);

    // Mock home directory
    Object.defineProperty(os, 'homedir', {
      value: () => tempHomeDir,
      writable: true,
    });

    // Change to temp project directory
    process.chdir(tempProjectDir);
  });

  afterEach(async () => {
    // Restore original paths
    process.chdir(originalCwd);
    Object.defineProperty(os, 'homedir', {
      value: () => originalHome,
      writable: true,
    });

    // Clean up temp directories
    await fs.remove(tempHomeDir);
    await fs.remove(tempProjectDir);
  });

  describe('Global Config', () => {
    it('should create default global config', async () => {
      const manager = new ConfigManager();
      await manager.ensureGlobalConfig();

      const configPath = path.join(tempHomeDir, '.arena', 'config.json');
      expect(await fs.pathExists(configPath)).toBe(true);

      const config = await fs.readJson(configPath);
      expect(config.whisper_mode).toBe('api');
      expect(config.clip_duration).toEqual([30, 90]);
      expect(config.output_format).toBe('mp4');
    });

    it('should read existing global config', async () => {
      const manager = new ConfigManager();

      // Create initial config
      await manager.ensureGlobalConfig();

      // Read it back
      const config = await manager.getGlobalConfig();

      expect(config.whisper_mode).toBe('api');
      expect(config.clip_duration).toBeDefined();
    });

    it('should update global config', async () => {
      const manager = new ConfigManager();
      await manager.ensureGlobalConfig();

      await manager.updateGlobalConfig({
        openai_api_key: 'sk-test-key',
        whisper_mode: 'local',
      });

      const config = await manager.getGlobalConfig();

      expect(config.openai_api_key).toBe('sk-test-key');
      expect(config.whisper_mode).toBe('local');
      // Should preserve other fields
      expect(config.clip_duration).toBeDefined();
    });

    it('should not duplicate config on multiple ensures', async () => {
      const manager = new ConfigManager();

      await manager.ensureGlobalConfig();
      await manager.ensureGlobalConfig();
      await manager.ensureGlobalConfig();

      const configPath = path.join(tempHomeDir, '.arena', 'config.json');
      const config = await fs.readJson(configPath);

      // Should still have default values, not duplicated
      expect(config.whisper_mode).toBe('api');
    });
  });

  describe('Project Config', () => {
    it('should create project config', async () => {
      const manager = new ConfigManager();
      const videoPath = '/path/to/video.mp4';

      await manager.createProjectConfig(videoPath);

      const configPath = path.join(tempProjectDir, '.arena', 'config.json');
      expect(await fs.pathExists(configPath)).toBe(true);

      const config = await fs.readJson(configPath);
      expect(config.video_path).toBe(videoPath);
      expect(config.created_at).toBeDefined();
      expect(config.preferences.clip_count).toBe(10);
    });

    it('should return null for non-existent project config', async () => {
      const manager = new ConfigManager();

      const config = await manager.getProjectConfig();

      expect(config).toBeNull();
    });

    it('should read existing project config', async () => {
      const manager = new ConfigManager();
      const videoPath = '/path/to/video.mp4';

      await manager.createProjectConfig(videoPath);
      const config = await manager.getProjectConfig();

      expect(config).not.toBeNull();
      expect(config?.video_path).toBe(videoPath);
    });

    it('should update project config', async () => {
      const manager = new ConfigManager();
      await manager.createProjectConfig('/path/to/video.mp4');

      await manager.updateProjectConfig({
        preferences: {
          clip_count: 20,
          focus_topics: ['sports', 'highlights'],
        },
      });

      const config = await manager.getProjectConfig();

      expect(config?.preferences?.clip_count).toBe(20);
      expect(config?.preferences?.focus_topics).toEqual(['sports', 'highlights']);
      // Should preserve other fields
      expect(config?.video_path).toBe('/path/to/video.mp4');
    });

    it('should throw error when updating non-existent project config', async () => {
      const manager = new ConfigManager();

      await expect(
        manager.updateProjectConfig({ preferences: { clip_count: 20 } })
      ).rejects.toThrow('No project config found');
    });
  });

  describe('Config Isolation', () => {
    it('should keep global and project configs separate', async () => {
      const manager = new ConfigManager();

      await manager.ensureGlobalConfig();
      await manager.createProjectConfig('/path/to/video.mp4');

      await manager.updateGlobalConfig({ openai_api_key: 'sk-global' });
      await manager.updateProjectConfig({
        preferences: { clip_count: 15 },
      });

      const globalConfig = await manager.getGlobalConfig();
      const projectConfig = await manager.getProjectConfig();

      expect(globalConfig.openai_api_key).toBe('sk-global');
      expect(projectConfig?.preferences?.clip_count).toBe(15);

      // Global config shouldn't have project fields
      expect(globalConfig).not.toHaveProperty('video_path');

      // Project config shouldn't have global fields
      expect(projectConfig).not.toHaveProperty('openai_api_key');
    });
  });
});
