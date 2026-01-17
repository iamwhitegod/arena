import fs from 'fs-extra';
import path from 'path';
import os from 'os';

export interface GlobalConfig {
  [key: string]: any; // Allow dynamic key access
  openai_api_key?: string;
  whisper_mode?: 'api' | 'local';
  clip_duration?: [number, number];
  output_format?: string;
  subtitle_style?: {
    font: string;
    size: number;
    color: string;
    bg_color: string;
    position: string;
  };
}

export interface ProjectConfig {
  video_path: string;
  created_at: string;
  preferences?: {
    clip_count?: number;
    focus_topics?: string[];
  };
}

export class ConfigManager {
  private globalConfigPath: string;
  private projectConfigPath: string;

  constructor() {
    this.globalConfigPath = path.join(os.homedir(), '.arena', 'config.json');
    this.projectConfigPath = path.join(process.cwd(), '.arena', 'config.json');
  }

  async ensureGlobalConfig(): Promise<void> {
    const configDir = path.dirname(this.globalConfigPath);
    await fs.ensureDir(configDir);

    if (!(await fs.pathExists(this.globalConfigPath))) {
      const defaultConfig: GlobalConfig = {
        whisper_mode: 'api',
        clip_duration: [30, 90],
        output_format: 'mp4',
        subtitle_style: {
          font: 'Arial',
          size: 24,
          color: 'white',
          bg_color: 'black',
          position: 'bottom',
        },
      };
      await fs.writeJson(this.globalConfigPath, defaultConfig, { spaces: 2 });
    }
  }

  async getGlobalConfig(): Promise<GlobalConfig> {
    await this.ensureGlobalConfig();
    return await fs.readJson(this.globalConfigPath);
  }

  async updateGlobalConfig(updates: Partial<GlobalConfig>): Promise<void> {
    const current = await this.getGlobalConfig();
    const updated = { ...current, ...updates };
    await fs.writeJson(this.globalConfigPath, updated, { spaces: 2 });
  }

  async createProjectConfig(videoPath: string): Promise<void> {
    const configDir = path.dirname(this.projectConfigPath);
    await fs.ensureDir(configDir);

    const config: ProjectConfig = {
      video_path: videoPath,
      created_at: new Date().toISOString(),
      preferences: {
        clip_count: 10,
      },
    };

    await fs.writeJson(this.projectConfigPath, config, { spaces: 2 });
  }

  async getProjectConfig(): Promise<ProjectConfig | null> {
    if (!(await fs.pathExists(this.projectConfigPath))) {
      return null;
    }
    return await fs.readJson(this.projectConfigPath);
  }

  async updateProjectConfig(updates: Partial<ProjectConfig>): Promise<void> {
    const current = await this.getProjectConfig();
    if (!current) {
      throw new Error('No project config found. Run arena process first.');
    }
    const updated = { ...current, ...updates };
    await fs.writeJson(this.projectConfigPath, updated, { spaces: 2 });
  }
}
