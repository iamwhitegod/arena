import fs from 'fs-extra';
import os from 'os';
import path from 'path';

const WORKSPACE_MARKER = '.arena-workspace.json';
const WORKSPACE_SCHEMA_VERSION = 1;
const MAX_CACHE_BYTES = 50 * 1024 * 1024;

interface WorkspaceMarker {
  schemaVersion: typeof WORKSPACE_SCHEMA_VERSION;
  root: string;
}

export class Workspace {
  private baseDir: string;

  constructor(baseDir = '.arena') {
    this.baseDir = path.resolve(baseDir);
    this.assertSafeWorkspaceRoot();
  }

  async initialize(): Promise<void> {
    for (const directory of [
      this.baseDir,
      path.join(this.baseDir, 'cache'),
      path.join(this.baseDir, 'output'),
      path.join(this.baseDir, 'output', 'clips'),
    ]) {
      await fs.ensureDir(directory, { mode: 0o700 });
      if (process.platform !== 'win32') {
        await fs.chmod(directory, 0o700);
      }
    }

    const marker: WorkspaceMarker = {
      schemaVersion: WORKSPACE_SCHEMA_VERSION,
      root: this.baseDir,
    };
    await this.writeJsonAtomic(path.join(this.baseDir, WORKSPACE_MARKER), marker);
  }

  async clean(): Promise<void> {
    if (!(await fs.pathExists(this.baseDir))) {
      return;
    }

    const markerPath = path.join(this.baseDir, WORKSPACE_MARKER);
    let marker: Partial<WorkspaceMarker>;
    try {
      marker = (await fs.readJson(markerPath)) as Partial<WorkspaceMarker>;
    } catch {
      throw new Error(`Refusing to remove unmarked Arena workspace: ${this.baseDir}`);
    }

    if (
      marker.schemaVersion !== WORKSPACE_SCHEMA_VERSION ||
      path.resolve(marker.root ?? '') !== this.baseDir
    ) {
      throw new Error(`Refusing to remove workspace with an invalid marker: ${this.baseDir}`);
    }

    await fs.remove(this.baseDir);
  }

  getCachePath(filename: string): string {
    return this.resolveFilename(path.join(this.baseDir, 'cache'), filename);
  }

  getOutputPath(filename: string): string {
    return this.resolveFilename(path.join(this.baseDir, 'output'), filename);
  }

  getClipPath(filename: string): string {
    return this.resolveFilename(path.join(this.baseDir, 'output', 'clips'), filename);
  }

  async exists(): Promise<boolean> {
    return fs.pathExists(this.baseDir);
  }

  async saveCache(filename: string, data: unknown): Promise<void> {
    await this.writeJsonAtomic(this.getCachePath(filename), data);
  }

  async loadCache(filename: string): Promise<unknown | null> {
    const cachePath = this.getCachePath(filename);
    if (!(await fs.pathExists(cachePath))) {
      return null;
    }

    const stats = await fs.lstat(cachePath);
    if (!stats.isFile() || stats.isSymbolicLink()) {
      throw new Error(`Refusing to read non-regular Arena cache file: ${cachePath}`);
    }
    if (stats.size > MAX_CACHE_BYTES) {
      throw new Error(`Arena cache file exceeds the ${MAX_CACHE_BYTES} byte limit: ${cachePath}`);
    }
    return fs.readJson(cachePath) as Promise<unknown>;
  }

  async hasCache(filename: string): Promise<boolean> {
    const cachePath = this.getCachePath(filename);
    if (!(await fs.pathExists(cachePath))) {
      return false;
    }
    const stats = await fs.lstat(cachePath);
    return stats.isFile() && !stats.isSymbolicLink();
  }

  private assertSafeWorkspaceRoot(): void {
    const parsed = path.parse(this.baseDir);
    const forbidden = new Set([
      parsed.root,
      path.resolve(process.cwd()),
      path.resolve(os.homedir()),
    ]);
    if (forbidden.has(this.baseDir)) {
      throw new Error(`Unsafe Arena workspace root: ${this.baseDir}`);
    }
    if (fs.existsSync(this.baseDir)) {
      const stats = fs.lstatSync(this.baseDir);
      if (!stats.isDirectory() || stats.isSymbolicLink()) {
        throw new Error(`Unsafe Arena workspace root: ${this.baseDir}`);
      }
    }
  }

  private resolveFilename(directory: string, filename: string): string {
    if (
      !filename ||
      filename.includes('\0') ||
      path.isAbsolute(filename) ||
      path.basename(filename) !== filename ||
      filename === '.' ||
      filename === '..'
    ) {
      throw new Error(`Unsafe Arena workspace filename: ${filename}`);
    }

    const resolvedDirectory = path.resolve(directory);
    if (fs.existsSync(resolvedDirectory)) {
      const directoryStats = fs.lstatSync(resolvedDirectory);
      if (!directoryStats.isDirectory() || directoryStats.isSymbolicLink()) {
        throw new Error(`Unsafe Arena workspace directory: ${resolvedDirectory}`);
      }

      const realBase = fs.realpathSync(this.baseDir);
      const realDirectory = fs.realpathSync(resolvedDirectory);
      if (realDirectory !== realBase && !realDirectory.startsWith(`${realBase}${path.sep}`)) {
        throw new Error(
          `Arena workspace directory escapes its approved root: ${resolvedDirectory}`
        );
      }
    }
    const resolvedPath = path.resolve(resolvedDirectory, filename);
    if (!resolvedPath.startsWith(`${resolvedDirectory}${path.sep}`)) {
      throw new Error(`Arena workspace path escapes its approved root: ${filename}`);
    }
    if (fs.existsSync(resolvedPath)) {
      const targetStats = fs.lstatSync(resolvedPath);
      if (!targetStats.isFile() || targetStats.isSymbolicLink()) {
        throw new Error(`Unsafe Arena workspace target: ${resolvedPath}`);
      }
    }
    return resolvedPath;
  }

  private async writeJsonAtomic(filePath: string, value: unknown): Promise<void> {
    const temporaryPath = `${filePath}.tmp-${process.pid}-${Date.now()}`;
    try {
      await fs.writeJson(temporaryPath, value, { spaces: 2, mode: 0o600 });
      if (process.platform !== 'win32') {
        await fs.chmod(temporaryPath, 0o600);
      }
      await fs.move(temporaryPath, filePath, { overwrite: true });
    } finally {
      await fs.remove(temporaryPath);
    }
  }
}
