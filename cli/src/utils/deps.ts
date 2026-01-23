/**
 * Dependency resolution utility
 * Finds Python and FFmpeg from bundled or system locations
 */

import fs from 'fs-extra';
import path from 'path';
import { fileURLToPath } from 'url';
import { spawn } from 'child_process';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

interface DepsConfig {
  pythonPath?: string;
  ffmpegPath?: string;
  depsDir?: string;
}

let cachedConfig: DepsConfig | null = null;

/**
 * Load bundled dependencies configuration
 */
async function loadDepsConfig(): Promise<DepsConfig> {
  if (cachedConfig) {
    return cachedConfig;
  }

  const configPath = path.join(__dirname, '../../.arena-config.json');

  try {
    if (await fs.pathExists(configPath)) {
      cachedConfig = await fs.readJson(configPath);
      return cachedConfig || {};
    }
  } catch {
    // Config file doesn't exist or invalid
  }

  return {};
}

/**
 * Check if a command exists
 */
async function commandExists(command: string): Promise<boolean> {
  return new Promise((resolve) => {
    // Windows-specific spawn options to avoid job object errors
    const spawnOptions: {
      stdio: 'ignore';
      windowsHide?: boolean;
      detached?: boolean;
      shell?: boolean;
    } = {
      stdio: 'ignore',
    };

    if (process.platform === 'win32') {
      spawnOptions.windowsHide = true;
      spawnOptions.detached = false;
      spawnOptions.shell = false;
    }

    const childProcess = spawn(command, ['--version'], spawnOptions);

    childProcess.on('close', (code: number | null) => {
      resolve(code === 0);
    });

    childProcess.on('error', () => {
      resolve(false);
    });
  });
}

/**
 * Get Python executable path (bundled or system)
 */
export async function getPythonPath(): Promise<string> {
  const config = await loadDepsConfig();

  // Try bundled Python first
  if (config.pythonPath && (await fs.pathExists(config.pythonPath))) {
    return config.pythonPath;
  }

  // Try system Python
  const systemPaths = ['python3', 'python'];

  for (const pythonCmd of systemPaths) {
    if (await commandExists(pythonCmd)) {
      return pythonCmd;
    }
  }

  // Fallback to python3 (will error if not found)
  return 'python3';
}

/**
 * Get FFmpeg executable path (bundled or system)
 */
export async function getFFmpegPath(): Promise<string> {
  const config = await loadDepsConfig();

  // Try bundled FFmpeg first
  if (config.ffmpegPath && (await fs.pathExists(config.ffmpegPath))) {
    return config.ffmpegPath;
  }

  // Try system FFmpeg
  if (await commandExists('ffmpeg')) {
    return 'ffmpeg';
  }

  // Fallback to ffmpeg (will error if not found)
  return 'ffmpeg';
}

/**
 * Get pip executable path
 */
export async function getPipPath(): Promise<string> {
  const pythonPath = await getPythonPath();

  // If using bundled Python, pip is in the same directory
  if (pythonPath.includes('.arena-deps')) {
    const pipPath = pythonPath.replace(/python(3)?(.exe)?$/, 'pip$2');
    if (await fs.pathExists(pipPath)) {
      return pipPath;
    }
  }

  // Try system pip
  const systemPaths = ['pip3', 'pip'];

  for (const pipCmd of systemPaths) {
    if (await commandExists(pipCmd)) {
      return pipCmd;
    }
  }

  // Fallback
  return 'pip3';
}

/**
 * Check if all dependencies are available
 */
export async function checkDependencies(): Promise<{
  python: boolean;
  ffmpeg: boolean;
  pip: boolean;
}> {
  const pythonPath = await getPythonPath();
  const ffmpegPath = await getFFmpegPath();
  const pipPath = await getPipPath();

  return {
    python: await commandExists(pythonPath),
    ffmpeg: await commandExists(ffmpegPath),
    pip: await commandExists(pipPath),
  };
}
