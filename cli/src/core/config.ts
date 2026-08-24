import fs from 'fs-extra';
import path from 'path';
import { getArenaHome } from './runtime.js';
import type { ProviderName } from './providers.js';

const PRIVATE_DIRECTORY_MODE = 0o700;
const PRIVATE_FILE_MODE = 0o600;
const CREDENTIALS_VERSION = 1;

export interface GlobalConfig {
  [key: string]: unknown;
  /** @deprecated Automatically migrated to credentials.json when read. */
  openai_api_key?: string;
  whisper_mode?: 'api' | 'local';
  clip_duration?: [number, number];
  output_format?: string;
  cookies_from_browser?: string;
  provider?: ProviderName;
  chat_provider?: ProviderName;
  chat_model?: string;
  overview_chat_provider?: ProviderName;
  overview_chat_model?: string;
  embedding_provider?: ProviderName;
  embedding_model?: string;
  transcription_provider?: ProviderName;
  transcription_model?: string;
  subtitle_style?: {
    font: string;
    size: number;
    color: string;
    bg_color: string;
    position: string;
  };
}

interface CredentialFile {
  version: typeof CREDENTIALS_VERSION;
  openai_api_key?: string;
}

export interface ProjectConfig {
  video_path: string;
  created_at: string;
  preferences?: {
    clip_count?: number;
    focus_topics?: string[];
  };
}

function defaultGlobalConfig(): GlobalConfig {
  return {
    whisper_mode: 'api',
    clip_duration: [30, 90],
    output_format: 'mp4',
    provider: 'openai',
    chat_model: 'gpt-4o',
    embedding_model: 'text-embedding-3-small',
    transcription_model: 'whisper-1',
    subtitle_style: {
      font: 'Arial',
      size: 24,
      color: 'white',
      bg_color: 'black',
      position: 'bottom',
    },
  };
}

export function isSensitiveConfigKey(key: string): boolean {
  const normalized = key.toLowerCase().replaceAll('-', '_');
  return /(^|_)(api_?key|authorization|cookie|password|secret|token)($|_)/.test(normalized);
}

export class ConfigManager {
  private globalConfigPath: string;
  private credentialsPath: string;
  private projectConfigPath: string;

  constructor(arenaHome = getArenaHome(), projectDir = process.cwd()) {
    this.globalConfigPath = path.join(arenaHome, 'config.json');
    this.credentialsPath = path.join(arenaHome, 'credentials.json');
    this.projectConfigPath = path.join(projectDir, '.arena', 'config.json');
  }

  getGlobalConfigPath(): string {
    return this.globalConfigPath;
  }

  getCredentialsPath(): string {
    return this.credentialsPath;
  }

  async ensureGlobalConfig(): Promise<void> {
    await this.ensurePrivateDirectory(path.dirname(this.globalConfigPath));

    if (!(await fs.pathExists(this.globalConfigPath))) {
      await this.writePrivateJson(this.globalConfigPath, defaultGlobalConfig());
      return;
    }

    await this.enforcePrivateFileMode(this.globalConfigPath);
  }

  async getGlobalConfig(): Promise<GlobalConfig> {
    await this.ensureGlobalConfig();
    return (await fs.readJson(this.globalConfigPath)) as GlobalConfig;
  }

  async updateGlobalConfig(updates: Partial<GlobalConfig>): Promise<void> {
    const sensitiveKey = Object.keys(updates).find(isSensitiveConfigKey);
    if (sensitiveKey) {
      throw new Error(
        `Refusing to store sensitive key "${sensitiveKey}" in config.json. Use the credential store instead.`
      );
    }

    const current = await this.getGlobalConfig();
    const next: GlobalConfig = { ...current, ...updates };
    const clearUnlessUpdated = (keys: Array<keyof GlobalConfig>) => {
      for (const key of keys) {
        if (!Object.prototype.hasOwnProperty.call(updates, key)) delete next[key];
      }
    };

    if (updates.provider) {
      clearUnlessUpdated([
        'chat_provider',
        'chat_model',
        'overview_chat_provider',
        'overview_chat_model',
        'embedding_provider',
        'embedding_model',
        'transcription_provider',
        'transcription_model',
      ]);
    }
    if (updates.chat_provider) {
      clearUnlessUpdated(['chat_model', 'overview_chat_model']);
    }
    if (updates.overview_chat_provider) {
      clearUnlessUpdated(['overview_chat_model']);
    }
    if (updates.embedding_provider) {
      clearUnlessUpdated(['embedding_model']);
    }
    if (updates.transcription_provider) {
      clearUnlessUpdated(['transcription_model']);
    }

    await this.writePrivateJson(this.globalConfigPath, next);
  }

  async resetGlobalConfig(includeCredentials = false): Promise<void> {
    await this.ensurePrivateDirectory(path.dirname(this.globalConfigPath));
    await this.writePrivateJson(this.globalConfigPath, defaultGlobalConfig());

    if (includeCredentials && (await fs.pathExists(this.credentialsPath))) {
      await fs.remove(this.credentialsPath);
    }
  }

  async setOpenAIApiKey(apiKey: string): Promise<void> {
    const trimmedKey = apiKey.trim();
    if (!trimmedKey) {
      throw new Error('OpenAI API key cannot be empty.');
    }

    const credentials = await this.readCredentials();
    await this.writePrivateJson(this.credentialsPath, {
      ...credentials,
      version: CREDENTIALS_VERSION,
      openai_api_key: trimmedKey,
    });
  }

  async hasStoredOpenAIApiKey(): Promise<boolean> {
    return Boolean((await this.readCredentials()).openai_api_key);
  }

  async resolveOpenAIApiKey(): Promise<string | undefined> {
    if (process.env.OPENAI_API_KEY) {
      return process.env.OPENAI_API_KEY;
    }

    const storedKey = (await this.readCredentials()).openai_api_key;
    if (storedKey) {
      return storedKey;
    }

    const config = await this.getGlobalConfig();
    const legacyKey = config.openai_api_key;
    if (!legacyKey) {
      return undefined;
    }

    await this.setOpenAIApiKey(legacyKey);
    delete config.openai_api_key;
    await this.writePrivateJson(this.globalConfigPath, config);
    process.emitWarning(
      `Arena moved a legacy API key from ${this.globalConfigPath} to the owner-only credential store.`,
      { code: 'ARENA_CREDENTIAL_MIGRATED' }
    );
    return legacyKey;
  }

  async populateRequiredProviderCredentials(providerNames: readonly string[]): Promise<void> {
    if (providerNames.includes('openai') && !process.env.OPENAI_API_KEY) {
      const apiKey = await this.resolveOpenAIApiKey();
      if (apiKey) process.env.OPENAI_API_KEY = apiKey;
    }
  }

  async createProjectConfig(videoPath: string): Promise<void> {
    const configDir = path.dirname(this.projectConfigPath);
    await this.ensurePrivateDirectory(configDir);

    const config: ProjectConfig = {
      video_path: videoPath,
      created_at: new Date().toISOString(),
      preferences: {
        clip_count: 10,
      },
    };

    await this.writePrivateJson(this.projectConfigPath, config);
  }

  async getProjectConfig(): Promise<ProjectConfig | null> {
    if (!(await fs.pathExists(this.projectConfigPath))) {
      return null;
    }
    await this.enforcePrivateFileMode(this.projectConfigPath);
    return (await fs.readJson(this.projectConfigPath)) as ProjectConfig;
  }

  async updateProjectConfig(updates: Partial<ProjectConfig>): Promise<void> {
    const current = await this.getProjectConfig();
    if (!current) {
      throw new Error('No project config found. Run arena process first.');
    }
    await this.writePrivateJson(this.projectConfigPath, { ...current, ...updates });
  }

  private async readCredentials(): Promise<CredentialFile> {
    if (!(await fs.pathExists(this.credentialsPath))) {
      return { version: CREDENTIALS_VERSION };
    }

    await this.enforcePrivateFileMode(this.credentialsPath);
    const credentials = (await fs.readJson(this.credentialsPath)) as Partial<CredentialFile>;
    if (credentials.version !== CREDENTIALS_VERSION) {
      throw new Error('Unsupported Arena credential file version.');
    }
    return credentials as CredentialFile;
  }

  private async ensurePrivateDirectory(directory: string): Promise<void> {
    if (await fs.pathExists(directory)) {
      const stats = await fs.lstat(directory);
      if (!stats.isDirectory() || stats.isSymbolicLink()) {
        throw new Error(`Refusing unsafe Arena configuration directory: ${directory}`);
      }
    } else {
      await fs.ensureDir(directory, { mode: PRIVATE_DIRECTORY_MODE });
    }
    if (process.platform !== 'win32') {
      await fs.chmod(directory, PRIVATE_DIRECTORY_MODE);
    }
  }

  private async enforcePrivateFileMode(filePath: string): Promise<void> {
    const stats = await fs.lstat(filePath);
    if (!stats.isFile() || stats.isSymbolicLink()) {
      throw new Error(`Refusing unsafe Arena configuration file: ${filePath}`);
    }
    if (process.platform !== 'win32') {
      await fs.chmod(filePath, PRIVATE_FILE_MODE);
    }
  }

  private async writePrivateJson(filePath: string, value: unknown): Promise<void> {
    await this.ensurePrivateDirectory(path.dirname(filePath));
    const temporaryPath = `${filePath}.tmp-${process.pid}-${Date.now()}`;

    try {
      await fs.writeJson(temporaryPath, value, {
        spaces: 2,
        mode: PRIVATE_FILE_MODE,
      });
      await this.enforcePrivateFileMode(temporaryPath);
      await fs.move(temporaryPath, filePath, { overwrite: true });
      await this.enforcePrivateFileMode(filePath);
    } finally {
      await fs.remove(temporaryPath);
    }
  }
}
