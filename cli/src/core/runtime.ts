import { spawn } from 'child_process';
import fs from 'fs-extra';
import os from 'os';
import path from 'path';

export const RUNTIME_SCHEMA_VERSION = 1;
export const MIN_PYTHON_VERSION = { major: 3, minor: 10 } as const;
// Exclusive upper bound: supported versions are Python 3.10 through 3.12.
export const MAX_PYTHON_VERSION = { major: 3, minor: 13 } as const;
const CLI_PACKAGE_NAME = '@whitegodkingsley/arena-cli';

export interface PythonCommand {
  command: string;
  args: string[];
  version: string;
}

export interface RuntimeManifest {
  schemaVersion: typeof RUNTIME_SCHEMA_VERSION;
  cliVersion: string;
  pythonPath: string;
  pythonVersion: string;
  installedAt: string;
}

interface CommandResult {
  code: number;
  stdout: string;
  stderr: string;
}

export function getArenaHome(): string {
  return process.env.ARENA_HOME
    ? path.resolve(process.env.ARENA_HOME)
    : path.join(os.homedir(), '.arena');
}

export function getRuntimeDir(): string {
  return path.join(getArenaHome(), 'runtime');
}

export function getManagedVenvDir(): string {
  return path.join(getRuntimeDir(), 'python');
}

export function getManagedEnvironmentsDir(): string {
  return path.join(getRuntimeDir(), 'environments');
}

export function getManagedBinDir(platform: NodeJS.Platform = process.platform): string {
  return path.join(getManagedVenvDir(), platform === 'win32' ? 'Scripts' : 'bin');
}

export function getManagedPythonPath(platform: NodeJS.Platform = process.platform): string {
  return path.join(getManagedBinDir(platform), platform === 'win32' ? 'python.exe' : 'python');
}

export function getRuntimeManifestPath(): string {
  return path.join(getRuntimeDir(), 'install.json');
}

function isRuntimeManifest(manifest: Partial<RuntimeManifest>): manifest is RuntimeManifest {
  return (
    manifest.schemaVersion === RUNTIME_SCHEMA_VERSION &&
    typeof manifest.cliVersion === 'string' &&
    typeof manifest.pythonPath === 'string' &&
    typeof manifest.pythonVersion === 'string' &&
    typeof manifest.installedAt === 'string'
  );
}

/** Resolve the active runtime synchronously for process spawning. */
export function getActivePythonPath(): string {
  try {
    const manifest = fs.readJsonSync(getRuntimeManifestPath()) as Partial<RuntimeManifest>;
    if (isRuntimeManifest(manifest) && fs.existsSync(manifest.pythonPath)) {
      return manifest.pythonPath;
    }
  } catch {
    // Fall through to the legacy fixed location for backwards compatibility.
  }
  return getManagedPythonPath();
}

export function getActiveBinDir(): string {
  return path.dirname(getActivePythonPath());
}

export function resolveEnginePath(fromDir: string): string | null {
  let currentDir = path.resolve(fromDir);

  // Find the CLI package root first. This supports arbitrary nesting under
  // dist/src while avoiding a broad ancestor search that could select an
  // unrelated `engine` directory outside Arena.
  for (let depth = 0; depth < 8; depth += 1) {
    const packagePath = path.join(currentDir, 'package.json');
    if (fs.existsSync(packagePath)) {
      try {
        const packageJson = fs.readJsonSync(packagePath) as { name?: string };
        if (packageJson.name === CLI_PACKAGE_NAME) {
          const candidates = [
            path.join(currentDir, 'engine'),
            path.resolve(currentDir, '..', 'engine'),
          ];
          for (const candidate of candidates) {
            if (
              fs.existsSync(path.join(candidate, 'setup.py')) &&
              fs.existsSync(path.join(candidate, 'arena', '__init__.py'))
            ) {
              return candidate;
            }
          }
          return null;
        }
      } catch {
        // Keep walking if this is not a readable package boundary.
      }
    }

    const parentDir = path.dirname(currentDir);
    if (parentDir === currentDir) {
      break;
    }
    currentDir = parentDir;
  }

  return null;
}

export function parsePythonVersion(output: string): string | null {
  return output.match(/Python\s+(\d+\.\d+(?:\.\d+)?)/i)?.[1] ?? null;
}

export function isSupportedPythonVersion(version: string): boolean {
  const [major, minor] = version.split('.').map(Number);

  if (!Number.isInteger(major) || !Number.isInteger(minor)) {
    return false;
  }

  const atLeastMinimum =
    major > MIN_PYTHON_VERSION.major ||
    (major === MIN_PYTHON_VERSION.major && minor >= MIN_PYTHON_VERSION.minor);
  const belowMaximum =
    major < MAX_PYTHON_VERSION.major ||
    (major === MAX_PYTHON_VERSION.major && minor < MAX_PYTHON_VERSION.minor);

  return atLeastMinimum && belowMaximum;
}

function pythonCandidates(platform: NodeJS.Platform = process.platform): Array<{
  command: string;
  args: string[];
}> {
  if (platform === 'win32') {
    return [
      { command: 'py', args: ['-3.12'] },
      { command: 'py', args: ['-3.11'] },
      { command: 'py', args: ['-3.10'] },
      { command: 'python3.12', args: [] },
      { command: 'python3.11', args: [] },
      { command: 'python3.10', args: [] },
      { command: 'python', args: [] },
      { command: 'python3', args: [] },
    ];
  }

  return [
    { command: 'python3.12', args: [] },
    { command: 'python3.11', args: [] },
    { command: 'python3.10', args: [] },
    { command: 'python3', args: [] },
    { command: 'python', args: [] },
  ];
}

function runCommand(command: string, args: string[]): Promise<CommandResult> {
  return new Promise((resolve) => {
    const child = spawn(command, args, {
      shell: false,
      windowsHide: true,
      stdio: ['ignore', 'pipe', 'pipe'],
    });

    let stdout = '';
    let stderr = '';

    child.stdout?.on('data', (data: Buffer) => {
      stdout += data.toString();
    });
    child.stderr?.on('data', (data: Buffer) => {
      stderr += data.toString();
    });
    child.on('error', () => {
      resolve({ code: 1, stdout, stderr });
    });
    child.on('close', (code: number | null) => {
      resolve({ code: code ?? 1, stdout, stderr });
    });
  });
}

export async function findCompatibleSystemPython(): Promise<PythonCommand | null> {
  for (const candidate of pythonCandidates()) {
    const result = await runCommand(candidate.command, [...candidate.args, '--version']);
    if (result.code !== 0) {
      continue;
    }

    const version = parsePythonVersion(`${result.stdout}\n${result.stderr}`);
    if (version && isSupportedPythonVersion(version)) {
      return { ...candidate, version };
    }
  }

  return null;
}

export async function readRuntimeManifest(): Promise<RuntimeManifest | null> {
  const manifestPath = getRuntimeManifestPath();

  try {
    const manifest = (await fs.readJson(manifestPath)) as Partial<RuntimeManifest>;
    if (!isRuntimeManifest(manifest)) {
      return null;
    }
    return manifest;
  } catch {
    return null;
  }
}

export async function writeRuntimeManifest(manifest: RuntimeManifest): Promise<void> {
  const runtimeDir = getRuntimeDir();
  const manifestPath = getRuntimeManifestPath();
  const temporaryPath = `${manifestPath}.tmp`;

  await fs.ensureDir(runtimeDir, { mode: 0o700 });
  await fs.writeJson(temporaryPath, manifest, { spaces: 2, mode: 0o600 });
  await fs.chmod(temporaryPath, 0o600);
  await fs.move(temporaryPath, manifestPath, { overwrite: true });
}

export function prependPath(
  currentPath: string | undefined,
  directory: string,
  platform: NodeJS.Platform = process.platform
): string {
  const separator = platform === 'win32' ? ';' : ':';
  return currentPath ? `${directory}${separator}${currentPath}` : directory;
}
