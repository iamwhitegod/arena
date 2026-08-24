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
  let originalApiKey: string | undefined;

  beforeEach(async () => {
    // Save original paths
    originalHome = os.homedir();
    originalCwd = process.cwd();
    originalApiKey = process.env.OPENAI_API_KEY;
    delete process.env.OPENAI_API_KEY;

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
    if (originalApiKey === undefined) {
      delete process.env.OPENAI_API_KEY;
    } else {
      process.env.OPENAI_API_KEY = originalApiKey;
    }

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
      expect(config.provider).toBe('openai');
      expect(config.chat_model).toBe('gpt-4o');
      expect(config.embedding_model).toBe('text-embedding-3-small');
      expect(config.transcription_model).toBe('whisper-1');

      if (process.platform !== 'win32') {
        expect((await fs.stat(configPath)).mode & 0o777).toBe(0o600);
        expect((await fs.stat(path.dirname(configPath))).mode & 0o777).toBe(0o700);
      }
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
        whisper_mode: 'local',
      });

      const config = await manager.getGlobalConfig();

      expect(config.whisper_mode).toBe('local');
      // Should preserve other fields
      expect(config.clip_duration).toBeDefined();
    });

    it('should refuse secrets in the non-sensitive config file', async () => {
      const manager = new ConfigManager();

      await expect(manager.updateGlobalConfig({ openai_api_key: 'sk-test-key' })).rejects.toThrow(
        'credential store'
      );
    });

    it('should clear stale provider-specific models when the global provider changes', async () => {
      const manager = new ConfigManager();
      await manager.ensureGlobalConfig();

      await manager.updateGlobalConfig({ provider: 'ollama' });

      const config = await manager.getGlobalConfig();
      expect(config.provider).toBe('ollama');
      expect(config).not.toHaveProperty('chat_model');
      expect(config).not.toHaveProperty('embedding_model');
      expect(config).not.toHaveProperty('transcription_model');
    });

    it('should preserve models explicitly updated with a provider', async () => {
      const manager = new ConfigManager();
      await manager.ensureGlobalConfig();

      await manager.updateGlobalConfig({ provider: 'ollama', chat_model: 'qwen3:8b' });

      const config = await manager.getGlobalConfig();
      expect(config.chat_model).toBe('qwen3:8b');
      expect(config).not.toHaveProperty('embedding_model');
    });

    it('should store credentials separately with owner-only permissions', async () => {
      const manager = new ConfigManager();
      const apiKey = `sk-${'x'.repeat(48)}`;

      await manager.setOpenAIApiKey(apiKey);

      expect(await manager.resolveOpenAIApiKey()).toBe(apiKey);
      expect(await manager.hasStoredOpenAIApiKey()).toBe(true);
      expect(await manager.getGlobalConfig()).not.toHaveProperty('openai_api_key');
      expect(await fs.readJson(manager.getCredentialsPath())).toMatchObject({
        version: 1,
        openai_api_key: apiKey,
      });
      if (process.platform !== 'win32') {
        expect((await fs.stat(manager.getCredentialsPath())).mode & 0o777).toBe(0o600);
      }
    });

    it('should prefer the environment over stored credentials', async () => {
      const manager = new ConfigManager();
      await manager.setOpenAIApiKey(`sk-${'s'.repeat(48)}`);
      process.env.OPENAI_API_KEY = `sk-${'e'.repeat(48)}`;

      expect(await manager.resolveOpenAIApiKey()).toBe(process.env.OPENAI_API_KEY);
    });

    it('should expose stored credentials only for required providers', async () => {
      const manager = new ConfigManager();
      const apiKey = `sk-${'r'.repeat(48)}`;
      await manager.setOpenAIApiKey(apiKey);

      await manager.populateRequiredProviderCredentials([]);
      expect(process.env.OPENAI_API_KEY).toBeUndefined();

      await manager.populateRequiredProviderCredentials(['openai']);
      expect(process.env.OPENAI_API_KEY).toBe(apiKey);
    });

    it('should migrate a legacy API key out of config.json', async () => {
      const manager = new ConfigManager();
      const apiKey = `sk-${'m'.repeat(48)}`;
      await manager.ensureGlobalConfig();
      const legacyConfig = await fs.readJson(manager.getGlobalConfigPath());
      await fs.writeJson(manager.getGlobalConfigPath(), {
        ...legacyConfig,
        openai_api_key: apiKey,
      });

      expect(await manager.resolveOpenAIApiKey()).toBe(apiKey);
      expect(await fs.readJson(manager.getGlobalConfigPath())).not.toHaveProperty('openai_api_key');
      expect(await fs.readJson(manager.getCredentialsPath())).toMatchObject({
        openai_api_key: apiKey,
      });
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

    it('should reject a symlinked global config file', async () => {
      if (process.platform === 'win32') return;

      const manager = new ConfigManager();
      const outsideFile = path.join(tempHomeDir, 'outside-config.json');
      await fs.writeJson(outsideFile, { whisper_mode: 'local' });
      await fs.ensureDir(path.dirname(manager.getGlobalConfigPath()));
      await fs.symlink(outsideFile, manager.getGlobalConfigPath());

      await expect(manager.getGlobalConfig()).rejects.toThrow('unsafe Arena configuration file');
    });

    it('should reject a symlinked project config directory', async () => {
      if (process.platform === 'win32') return;

      const outsideDir = path.join(tempHomeDir, 'outside-project-config');
      await fs.ensureDir(outsideDir);
      await fs.symlink(outsideDir, path.join(tempProjectDir, '.arena'));

      await expect(new ConfigManager().createProjectConfig('/tmp/video.mp4')).rejects.toThrow(
        'unsafe Arena configuration directory'
      );
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

      await manager.setOpenAIApiKey('sk-global');
      await manager.updateProjectConfig({
        preferences: { clip_count: 15 },
      });

      const globalConfig = await manager.getGlobalConfig();
      const projectConfig = await manager.getProjectConfig();

      expect(await manager.hasStoredOpenAIApiKey()).toBe(true);
      expect(projectConfig?.preferences?.clip_count).toBe(15);

      // Global config shouldn't have project fields
      expect(globalConfig).not.toHaveProperty('video_path');

      // Project config shouldn't have global fields
      expect(projectConfig).not.toHaveProperty('openai_api_key');
    });
  });
});
