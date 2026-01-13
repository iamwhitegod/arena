import fs from 'fs-extra';
import path from 'path';

export class Workspace {
  private baseDir: string;

  constructor(baseDir: string = '.arena') {
    this.baseDir = baseDir;
  }

  async initialize(): Promise<void> {
    // Create main directories
    await fs.ensureDir(this.baseDir);
    await fs.ensureDir(path.join(this.baseDir, 'cache'));
    await fs.ensureDir(path.join(this.baseDir, 'output'));
    await fs.ensureDir(path.join(this.baseDir, 'output', 'clips'));
  }

  async clean(): Promise<void> {
    if (await fs.pathExists(this.baseDir)) {
      await fs.remove(this.baseDir);
    }
  }

  getCachePath(filename: string): string {
    return path.join(this.baseDir, 'cache', filename);
  }

  getOutputPath(filename: string): string {
    return path.join(this.baseDir, 'output', filename);
  }

  getClipPath(filename: string): string {
    return path.join(this.baseDir, 'output', 'clips', filename);
  }

  async exists(): Promise<boolean> {
    return await fs.pathExists(this.baseDir);
  }

  async saveCache(filename: string, data: any): Promise<void> {
    const cachePath = this.getCachePath(filename);
    await fs.writeJson(cachePath, data, { spaces: 2 });
  }

  async loadCache(filename: string): Promise<any | null> {
    const cachePath = this.getCachePath(filename);
    if (await fs.pathExists(cachePath)) {
      return await fs.readJson(cachePath);
    }
    return null;
  }

  async hasCache(filename: string): Promise<boolean> {
    const cachePath = this.getCachePath(filename);
    return await fs.pathExists(cachePath);
  }
}
