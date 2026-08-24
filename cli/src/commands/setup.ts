/**
 * Create and verify Arena's private Python runtime.
 *
 * System Python is only used to create the virtual environment. Arena never
 * installs packages into the user's global Python environment.
 */

import { spawn } from 'child_process';
import chalk from 'chalk';
import crypto from 'crypto';
import fs from 'fs-extra';
import inquirer from 'inquirer';
import ora from 'ora';
import { validateLocalReadiness } from '../core/local.js';
import path from 'path';
import { fileURLToPath } from 'url';
import {
  RUNTIME_SCHEMA_VERSION,
  findCompatibleSystemPython,
  getArenaHome,
  getManagedEnvironmentsDir,
  getManagedVenvDir,
  getRuntimeDir,
  isSupportedPythonVersion,
  parsePythonVersion,
  readRuntimeManifest,
  resolveEnginePath,
  writeRuntimeManifest,
  type PythonCommand,
} from '../core/runtime.js';
import { logCommand, logger } from '../utils/logger.js';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const packageJson = fs.readJsonSync(path.resolve(__dirname, '../../package.json')) as {
  version: string;
  arenaPreparedArtifact?: boolean;
};
const DEFAULT_SETUP_TIMEOUT_MS = 15 * 60 * 1000;
const MODEL_INSTALL_TIMEOUT_MS = 90 * 60 * 1000;
const COMMAND_CHECK_TIMEOUT_MS = 15 * 1000;
const LOCAL_MODEL_PACKS = ['lite', 'default', 'pro'] as const;
type LocalModelPack = (typeof LOCAL_MODEL_PACKS)[number];

export interface SetupOptions {
  check?: boolean;
  force?: boolean;
  local?: boolean;
  modelPack?: LocalModelPack;
  yes?: boolean;
}

interface CommandResult {
  code: number;
  stdout: string;
  stderr: string;
}

interface RuntimeStatus {
  ready: boolean;
  pythonVersion?: string;
  reason?: string;
}

interface InstallerCommand {
  command: string;
  args: string[];
  label: string;
}

interface IntegrityStatus {
  valid: boolean;
  detail: string;
}

export function nativeCompilerChecks(
  platform: NodeJS.Platform = process.platform
): Array<[string, string[]]> {
  if (platform === 'win32') {
    return [
      ['where.exe', ['cl.exe']],
      ['where.exe', ['clang.exe']],
      ['where.exe', ['gcc.exe']],
    ];
  }
  if (platform === 'darwin') {
    return [['xcrun', ['--find', 'clang']]];
  }
  return [
    ['cc', ['--version']],
    ['clang', ['--version']],
    ['gcc', ['--version']],
  ];
}

export function windowsVswherePaths(environment: NodeJS.ProcessEnv = process.env): string[] {
  return [environment['ProgramFiles(x86)'], environment.ProgramFiles]
    .filter((value): value is string => Boolean(value))
    .map((root) => path.join(root, 'Microsoft Visual Studio', 'Installer', 'vswhere.exe'));
}

async function hasNativeCompiler(): Promise<boolean> {
  for (const [command, args] of nativeCompilerChecks()) {
    if (await commandAvailable(command, args)) {
      return true;
    }
  }
  if (process.platform === 'win32') {
    for (const vswhere of windowsVswherePaths()) {
      if (!(await fs.pathExists(vswhere))) continue;
      const result = await runCommand(vswhere, [
        '-latest',
        '-products',
        '*',
        '-requires',
        'Microsoft.VisualStudio.Component.VC.Tools.x86.x64',
        '-property',
        'installationPath',
      ]);
      if (result.code === 0 && result.stdout.trim()) return true;
    }
  }
  return false;
}

function getSetupTimeoutMs(): number {
  const configuredMinutes = process.env.ARENA_SETUP_TIMEOUT_MINUTES;
  if (configuredMinutes === undefined) {
    return DEFAULT_SETUP_TIMEOUT_MS;
  }

  const minutes = Number(configuredMinutes);
  if (!Number.isFinite(minutes) || minutes <= 0) {
    throw new Error('ARENA_SETUP_TIMEOUT_MINUTES must be a positive number');
  }
  return Math.round(minutes * 60 * 1000);
}

function formatTimeout(timeoutMs: number): string {
  if (timeoutMs < 1000) {
    return `${timeoutMs} ms`;
  }
  if (timeoutMs < 60 * 1000) {
    return `${Math.round(timeoutMs / 1000)} seconds`;
  }
  return `${Number((timeoutMs / 60000).toFixed(2))} minutes`;
}

const INSTALL_LOCK_NAME = 'install.lock';

function processIsRunning(pid: number): boolean {
  try {
    process.kill(pid, 0);
    return true;
  } catch (error) {
    return (error as NodeJS.ErrnoException).code === 'EPERM';
  }
}

async function acquireInstallLock(): Promise<string> {
  const runtimeDir = getRuntimeDir();
  const lockPath = path.join(runtimeDir, INSTALL_LOCK_NAME);
  await fs.ensureDir(runtimeDir, { mode: 0o700 });

  const createLock = async () => {
    await fs.writeJson(
      lockPath,
      { pid: process.pid, startedAt: new Date().toISOString() },
      { mode: 0o600, flag: 'wx' }
    );
    await fs.chmod(lockPath, 0o600);
  };

  try {
    await createLock();
  } catch (error) {
    if ((error as NodeJS.ErrnoException).code !== 'EEXIST') {
      throw new Error(`Could not acquire the Arena setup lock: ${(error as Error).message}`);
    }

    try {
      const lock = (await fs.readJson(lockPath)) as { pid?: number };
      if (typeof lock.pid === 'number' && processIsRunning(lock.pid)) {
        throw new Error(`Another Arena setup is already running (process ${lock.pid})`);
      }
    } catch (readError) {
      if (readError instanceof Error && readError.message.startsWith('Another Arena setup')) {
        throw readError;
      }
      // A malformed lock is stale.
    }

    const staleLockPath = `${lockPath}.stale-${process.pid}-${Date.now()}`;
    try {
      // Rename is atomic: only one contender can claim a stale lock, and no
      // contender ever deletes a newly-created lock owned by another process.
      await fs.rename(lockPath, staleLockPath);
    } catch {
      try {
        await createLock();
        return lockPath;
      } catch (retryError) {
        if ((retryError as NodeJS.ErrnoException).code === 'EEXIST') {
          throw new Error('Another Arena setup started while the stale lock was being recovered');
        }
        throw new Error(`Could not acquire the Arena setup lock: ${(retryError as Error).message}`);
      }
    }

    try {
      try {
        await createLock();
      } catch (retryError) {
        if ((retryError as NodeJS.ErrnoException).code === 'EEXIST') {
          throw new Error('Another Arena setup started while the stale lock was being recovered');
        }
        throw retryError;
      }
    } finally {
      await fs.remove(staleLockPath);
    }
  }

  return lockPath;
}

async function recoverInterruptedInstall(runtimeDir: string, finalVenvDir: string): Promise<void> {
  const entries = await fs.readdir(runtimeDir, { withFileTypes: true });
  const installing = entries
    .filter((entry) => entry.isDirectory() && /^python\.installing-\d+$/.test(entry.name))
    .map((entry) => path.join(runtimeDir, entry.name));
  const previous = entries
    .filter((entry) => entry.isDirectory() && /^python\.previous-\d+$/.test(entry.name))
    .map((entry) => path.join(runtimeDir, entry.name));
  const engineSources = entries
    .filter((entry) => entry.isDirectory() && /^engine-source-\d+$/.test(entry.name))
    .map((entry) => path.join(runtimeDir, entry.name));

  for (const directory of [...installing, ...engineSources]) {
    await fs.remove(directory);
  }

  if (await fs.pathExists(finalVenvDir)) {
    for (const directory of previous) {
      await fs.remove(directory);
    }
  } else if (previous.length > 0) {
    const [restore, ...discard] = previous;
    await fs.move(restore, finalVenvDir, { overwrite: true });
    for (const directory of discard) {
      await fs.remove(directory);
    }
  }

  const manifest = await readRuntimeManifest();
  const activeVenvDir = manifest ? path.dirname(path.dirname(manifest.pythonPath)) : null;
  const environmentsDir = getManagedEnvironmentsDir();
  if (await fs.pathExists(environmentsDir)) {
    const environments = await fs.readdir(environmentsDir, { withFileTypes: true });
    for (const environment of environments) {
      const environmentPath = path.join(environmentsDir, environment.name);
      if (
        environment.isDirectory() &&
        path.resolve(environmentPath) !== (activeVenvDir ? path.resolve(activeVenvDir) : null)
      ) {
        await fs.remove(environmentPath);
      }
    }
  }

  // Migrate away from the old fixed venv only after a new active manifest exists.
  if (
    activeVenvDir &&
    path.resolve(activeVenvDir) !== path.resolve(finalVenvDir) &&
    (await fs.pathExists(finalVenvDir))
  ) {
    await fs.remove(finalVenvDir);
  }
}

async function recoverInterruptedRuntime(): Promise<void> {
  const lockPath = await acquireInstallLock();
  try {
    await recoverInterruptedInstall(getRuntimeDir(), getManagedVenvDir());
  } finally {
    await fs.remove(lockPath);
  }
}

function runCommand(
  command: string,
  args: string[],
  options: {
    inherit?: boolean;
    env?: NodeJS.ProcessEnv;
    onOutput?: (output: string) => void;
    timeoutMs?: number;
  } = {}
): Promise<CommandResult> {
  return new Promise((resolve) => {
    const child = spawn(command, args, {
      shell: false,
      windowsHide: true,
      stdio: options.inherit ? 'inherit' : ['ignore', 'pipe', 'pipe'],
      env: options.env ?? process.env,
    });

    let stdout = '';
    let stderr = '';
    let settled = false;
    let timedOut = false;
    let forceKillTimer: NodeJS.Timeout | undefined;
    const finish = (result: CommandResult) => {
      if (settled) {
        return;
      }
      settled = true;
      if (timeoutTimer) {
        clearTimeout(timeoutTimer);
      }
      if (forceKillTimer) {
        clearTimeout(forceKillTimer);
      }
      resolve(result);
    };
    const timeoutMs = options.timeoutMs;
    const timeoutTimer = timeoutMs
      ? setTimeout(() => {
          timedOut = true;
          stderr = `${stderr}\nTimed out after ${formatTimeout(timeoutMs)}`.trim();
          child.kill('SIGTERM');
          forceKillTimer = setTimeout(() => child.kill('SIGKILL'), 5000);
        }, timeoutMs)
      : undefined;

    child.stdout?.on('data', (data: Buffer) => {
      const output = data.toString();
      stdout += output;
      options.onOutput?.(output);
    });
    child.stderr?.on('data', (data: Buffer) => {
      const output = data.toString();
      stderr += output;
      options.onOutput?.(output);
    });
    child.once('error', (error: Error) => {
      finish({ code: timedOut ? 124 : 1, stdout, stderr: `${stderr}\n${error.message}`.trim() });
    });
    child.once('close', (code: number | null) => {
      finish({ code: timedOut ? 124 : (code ?? 1), stdout, stderr });
    });
  });
}

async function commandAvailable(command: string, args = ['--version']): Promise<boolean> {
  return (await runCommand(command, args, { timeoutMs: COMMAND_CHECK_TIMEOUT_MS })).code === 0;
}

async function verifyEngineIntegrity(enginePath: string): Promise<IntegrityStatus> {
  if (packageJson.arenaPreparedArtifact !== true) {
    return { valid: true, detail: 'development source tree' };
  }

  const manifestPath = path.join(enginePath, 'MANIFEST.sha256');
  if (!(await fs.pathExists(manifestPath))) {
    return { valid: false, detail: 'engine checksum manifest is missing' };
  }

  const engineRoot = path.resolve(enginePath);
  const lines = (await fs.readFile(manifestPath, 'utf8')).split('\n').filter(Boolean);
  if (lines.length < 2) {
    return { valid: false, detail: 'engine checksum manifest is empty' };
  }

  for (const line of lines) {
    const match = line.match(/^([a-f0-9]{64}) {2}(.+)$/);
    if (!match) {
      return { valid: false, detail: 'engine checksum manifest is malformed' };
    }

    const [, expectedHash, relativePath] = match;
    const absolutePath = path.resolve(engineRoot, relativePath);
    if (!absolutePath.startsWith(`${engineRoot}${path.sep}`)) {
      return { valid: false, detail: `unsafe manifest path: ${relativePath}` };
    }
    if (!(await fs.pathExists(absolutePath)) || !(await fs.stat(absolutePath)).isFile()) {
      return { valid: false, detail: `engine file is missing: ${relativePath}` };
    }

    const content = await fs.readFile(absolutePath);
    const actualHash = crypto.createHash('sha256').update(content).digest('hex');
    if (actualHash !== expectedHash) {
      return { valid: false, detail: `engine checksum failed: ${relativePath}` };
    }
  }

  return { valid: true, detail: `${lines.length} files verified` };
}

function managedPythonAt(venvDir: string): string {
  return path.join(
    venvDir,
    process.platform === 'win32' ? 'Scripts' : 'bin',
    process.platform === 'win32' ? 'python.exe' : 'python'
  );
}

export function runtimeRequirementsLock(includeLocal: boolean): string {
  return includeLocal ? 'requirements-local.lock' : 'requirements.lock';
}

export function runtimeImportProbe(includeLocal: boolean): string {
  const imports = ['arena', 'cv2', 'librosa', 'numpy', 'openai', 'requests', 'yt_dlp'];
  if (includeLocal) {
    imports.push('llama_cpp', 'faster_whisper', 'ctranslate2');
  }
  return `import ${imports.join(', ')}; print("arena-runtime-ok")`;
}

async function verifyPython(
  pythonPath: string,
  verifyImports = true,
  includeLocal = false
): Promise<RuntimeStatus> {
  if (!(await fs.pathExists(pythonPath))) {
    return { ready: false, reason: 'managed Python is missing' };
  }

  const versionResult = await runCommand(pythonPath, ['--version']);
  const pythonVersion = parsePythonVersion(`${versionResult.stdout}\n${versionResult.stderr}`);
  if (versionResult.code !== 0 || !pythonVersion || !isSupportedPythonVersion(pythonVersion)) {
    return {
      ready: false,
      pythonVersion: pythonVersion ?? undefined,
      reason: 'unsupported Python',
    };
  }

  if (!verifyImports) {
    return { ready: true, pythonVersion };
  }

  const importResult = await runCommand(pythonPath, ['-c', runtimeImportProbe(includeLocal)]);
  if (importResult.code !== 0 || !importResult.stdout.includes('arena-runtime-ok')) {
    return {
      ready: false,
      pythonVersion,
      reason: importResult.stderr.trim().split('\n').slice(-1)[0] || 'engine import check failed',
    };
  }

  return { ready: true, pythonVersion };
}

async function getInstalledRuntimeStatus(includeLocal = false): Promise<RuntimeStatus> {
  const manifest = await readRuntimeManifest();
  if (!manifest) {
    return { ready: false, reason: 'runtime manifest is missing' };
  }
  if (manifest.cliVersion !== packageJson.version) {
    return {
      ready: false,
      pythonVersion: manifest.pythonVersion,
      reason: `runtime was installed for Arena ${manifest.cliVersion}`,
    };
  }

  return verifyPython(manifest.pythonPath, true, includeLocal);
}

async function installVerifiedModelPack(
  pythonPath: string,
  pack: LocalModelPack,
  onOutput?: (output: string) => void
): Promise<void> {
  if (!LOCAL_MODEL_PACKS.includes(pack)) {
    throw new Error(`Unknown local model pack: ${pack}`);
  }
  const modelRoot = path.join(getArenaHome(), 'models');
  const code = [
    'from pathlib import Path',
    'from arena.models import MODEL_PACKS, ModelManager',
    `ModelManager(Path(${JSON.stringify(modelRoot)})).install_pack(MODEL_PACKS[${JSON.stringify(pack)}])`,
  ].join('; ');
  const result = await runCommand(pythonPath, ['-c', code], {
    env: { ...process.env, ARENA_MODEL_ROOT: modelRoot },
    onOutput,
    timeoutMs: MODEL_INSTALL_TIMEOUT_MS,
  });
  if (result.code !== 0) {
    throw commandFailure(`Installing verified ${pack} model pack`, result);
  }
}

async function detectFfmpegInstaller(): Promise<InstallerCommand | null> {
  if (process.platform === 'darwin' && (await commandAvailable('brew'))) {
    return { command: 'brew', args: ['install', 'ffmpeg'], label: 'brew install ffmpeg' };
  }

  if (process.platform === 'win32') {
    if (await commandAvailable('winget')) {
      return {
        command: 'winget',
        args: [
          'install',
          '--id',
          'Gyan.FFmpeg',
          '--exact',
          '--accept-source-agreements',
          '--accept-package-agreements',
        ],
        label: 'winget install --id Gyan.FFmpeg',
      };
    }
    if (await commandAvailable('choco')) {
      return { command: 'choco', args: ['install', '-y', 'ffmpeg'], label: 'choco install ffmpeg' };
    }
    return null;
  }

  const linuxInstallers: Array<[string, InstallerCommand]> = [
    [
      'apt-get',
      {
        command: 'sudo',
        args: ['apt-get', 'install', '-y', 'ffmpeg'],
        label: 'sudo apt-get install -y ffmpeg',
      },
    ],
    [
      'dnf',
      {
        command: 'sudo',
        args: ['dnf', 'install', '-y', 'ffmpeg'],
        label: 'sudo dnf install -y ffmpeg',
      },
    ],
    [
      'yum',
      {
        command: 'sudo',
        args: ['yum', 'install', '-y', 'ffmpeg'],
        label: 'sudo yum install -y ffmpeg',
      },
    ],
    [
      'pacman',
      {
        command: 'sudo',
        args: ['pacman', '-S', '--noconfirm', 'ffmpeg'],
        label: 'sudo pacman -S --noconfirm ffmpeg',
      },
    ],
    [
      'zypper',
      {
        command: 'sudo',
        args: ['zypper', 'install', '-y', 'ffmpeg'],
        label: 'sudo zypper install -y ffmpeg',
      },
    ],
  ];

  for (const [detector, installer] of linuxInstallers) {
    if (await commandAvailable(detector)) {
      return installer;
    }
  }
  return null;
}

async function ensureFfmpeg(options: SetupOptions): Promise<boolean> {
  if (
    (await commandAvailable('ffmpeg', ['-version'])) &&
    (await commandAvailable('ffprobe', ['-version']))
  ) {
    return true;
  }

  const installer = await detectFfmpegInstaller();
  if (!installer) {
    console.log(chalk.red('✗ FFmpeg and ffprobe are required but were not found.'));
    console.log(
      chalk.white(
        '  Install FFmpeg from https://ffmpeg.org/download.html, then rerun arena setup.\n'
      )
    );
    return false;
  }

  let shouldInstall = options.yes === true;
  if (!shouldInstall && process.stdin.isTTY && process.stdout.isTTY) {
    const answer = await inquirer.prompt<{ install: boolean }>([
      {
        type: 'confirm',
        name: 'install',
        message: `FFmpeg is missing. Run “${installer.label}”?`,
        default: true,
      },
    ]);
    shouldInstall = answer.install;
  }

  if (!shouldInstall) {
    console.log(chalk.yellow('! FFmpeg installation needs confirmation.'));
    console.log(chalk.white(`  Run ${installer.label}, or rerun with arena setup --yes.\n`));
    return false;
  }

  console.log(chalk.cyan(`\nInstalling FFmpeg with: ${installer.label}\n`));
  const result = await runCommand(installer.command, installer.args, { inherit: true });
  if (result.code !== 0) {
    console.log(chalk.red(`\n✗ FFmpeg installation failed (exit ${result.code}).`));
    console.log(chalk.white(`  Run ${installer.label} manually, then rerun arena setup.\n`));
    return false;
  }

  return (
    (await commandAvailable('ffmpeg', ['-version'])) &&
    (await commandAvailable('ffprobe', ['-version']))
  );
}

function pythonInstallHelp(): string {
  if (process.platform === 'darwin') {
    return 'brew install python@3.12';
  }
  if (process.platform === 'win32') {
    return 'winget install --id Python.Python.3.12 --exact';
  }
  return 'Install Python 3.10–3.12 (including the venv module) with your distribution package manager.';
}

function commandFailure(step: string, result: CommandResult): Error {
  const details = `${result.stderr}\n${result.stdout}`.trim().split('\n').slice(-12).join('\n');
  return new Error(`${step} failed with exit code ${result.code}${details ? `:\n${details}` : ''}`);
}

async function buildRuntime(
  basePython: PythonCommand,
  enginePath: string,
  includeLocal: boolean,
  onProgress?: (message: string) => void
): Promise<RuntimeStatus> {
  const runtimeDir = getRuntimeDir();
  const environmentsDir = getManagedEnvironmentsDir();
  const candidateVenvDir = path.join(
    environmentsDir,
    `python-${packageJson.version}-${Date.now()}-${process.pid}`
  );
  const engineSourceDir = path.join(runtimeDir, `engine-source-${process.pid}`);

  const setupTimeoutMs = getSetupTimeoutMs();
  const lockPath = await acquireInstallLock();
  let promoted = false;

  const pipEnvironment: NodeJS.ProcessEnv = {
    ...process.env,
    PIP_DISABLE_PIP_VERSION_CHECK: '1',
    PIP_NO_INPUT: '1',
    PYTHONUNBUFFERED: '1',
  };
  const reportOutput = (output: string) => {
    const lastLine = output
      .replace(/\r/g, '\n')
      .split('\n')
      .map((line) => line.trim())
      .filter(Boolean)
      .pop();
    if (lastLine) {
      onProgress?.(lastLine.slice(0, 100));
    }
  };
  const safePipArgs = [
    '--disable-pip-version-check',
    '--no-input',
    '--default-timeout',
    '30',
    '--retries',
    '3',
    '--progress-bar',
    process.stdout.isTTY ? 'on' : 'off',
    '--prefer-binary',
  ];

  try {
    await recoverInterruptedInstall(runtimeDir, getManagedVenvDir());
    await fs.ensureDir(environmentsDir, { mode: 0o700 });
    await fs.ensureDir(engineSourceDir, { mode: 0o700 });
    await fs.copy(path.join(enginePath, 'arena'), path.join(engineSourceDir, 'arena'), {
      filter: (sourcePath) => {
        const parts = sourcePath.split(path.sep);
        return (
          !parts.includes('__pycache__') &&
          !parts.includes('.pytest_cache') &&
          !sourcePath.endsWith('.pyc') &&
          !sourcePath.endsWith('.pyo')
        );
      },
    });
    for (const filename of [
      'setup.py',
      'requirements.txt',
      'requirements.lock',
      'requirements-local.txt',
      'requirements-local.lock',
      'build-requirements.txt',
      'build-requirements.lock',
    ]) {
      await fs.copy(path.join(enginePath, filename), path.join(engineSourceDir, filename));
    }

    onProgress?.('Creating private Python environment');
    const createResult = await runCommand(basePython.command, [
      ...basePython.args,
      '-m',
      'venv',
      candidateVenvDir,
    ]);
    if (createResult.code !== 0) {
      throw commandFailure('Creating the private Python environment', createResult);
    }

    const candidatePython = managedPythonAt(candidateVenvDir);
    pipEnvironment.PATH = [path.dirname(candidatePython), process.env.PATH ?? '']
      .filter(Boolean)
      .join(path.delimiter);
    if (includeLocal && process.platform === 'darwin' && process.arch === 'arm64') {
      pipEnvironment.CMAKE_ARGS = '-DGGML_METAL=on -DCMAKE_OSX_ARCHITECTURES=arm64';
    }
    onProgress?.('Installing hash-verified Python build tooling');
    const toolingResult = await runCommand(
      candidatePython,
      [
        '-m',
        'pip',
        'install',
        ...safePipArgs,
        '--require-hashes',
        '--no-build-isolation',
        '--requirement',
        path.join(engineSourceDir, 'build-requirements.lock'),
      ],
      { env: pipEnvironment, onOutput: reportOutput, timeoutMs: setupTimeoutMs }
    );
    if (toolingResult.code !== 0) {
      throw commandFailure('Preparing pip', toolingResult);
    }

    onProgress?.('Installing hash-verified Arena engine dependencies');
    const dependencyResult = await runCommand(
      candidatePython,
      [
        '-m',
        'pip',
        'install',
        ...safePipArgs,
        '--require-hashes',
        '--no-build-isolation',
        '--requirement',
        path.join(engineSourceDir, runtimeRequirementsLock(includeLocal)),
      ],
      { env: pipEnvironment, onOutput: reportOutput, timeoutMs: setupTimeoutMs }
    );
    if (dependencyResult.code !== 0) {
      throw commandFailure('Installing Arena engine dependencies', dependencyResult);
    }

    onProgress?.('Installing the Arena engine');
    const engineResult = await runCommand(
      candidatePython,
      [
        '-m',
        'pip',
        'install',
        ...safePipArgs,
        '--no-deps',
        '--no-build-isolation',
        '--upgrade',
        engineSourceDir,
      ],
      { env: pipEnvironment, onOutput: reportOutput, timeoutMs: setupTimeoutMs }
    );
    if (engineResult.code !== 0) {
      throw commandFailure('Installing the Arena engine', engineResult);
    }

    onProgress?.('Verifying engine imports');
    const verification = await verifyPython(candidatePython, true, includeLocal);
    if (!verification.ready) {
      throw new Error(`Runtime verification failed: ${verification.reason}`);
    }

    await writeRuntimeManifest({
      schemaVersion: RUNTIME_SCHEMA_VERSION,
      cliVersion: packageJson.version,
      pythonPath: candidatePython,
      pythonVersion: verification.pythonVersion ?? basePython.version,
      installedAt: new Date().toISOString(),
    });
    promoted = true;
    await recoverInterruptedInstall(runtimeDir, getManagedVenvDir()).catch(() => undefined);
    return verification;
  } finally {
    if (!promoted) {
      await fs.remove(candidateVenvDir);
    }
    await fs.remove(engineSourceDir);
    await fs.remove(lockPath);
  }
}

async function printCheck(includeLocal = false): Promise<boolean> {
  console.log(chalk.bold('\nArena installation check\n'));

  const enginePath = resolveEnginePath(__dirname);
  const integrity = enginePath
    ? await verifyEngineIntegrity(enginePath)
    : { valid: false, detail: 'engine unavailable' };
  const runtime = await getInstalledRuntimeStatus(includeLocal);
  const ffmpeg = await commandAvailable('ffmpeg', ['-version']);
  const ffprobe = await commandAvailable('ffprobe', ['-version']);
  const systemPython = await findCompatibleSystemPython();
  let localModelsReady = !includeLocal;
  if (includeLocal && runtime.ready) {
    try {
      await validateLocalReadiness([
        { capability: 'chat', provider: 'local' },
        { capability: 'embedding', provider: 'local' },
        { capability: 'transcription', provider: 'local' },
      ]);
      localModelsReady = true;
    } catch {
      localModelsReady = false;
    }
  }

  const rows: Array<[string, boolean, string]> = [
    ['Bundled engine', enginePath !== null, enginePath ?? 'not found in this installation'],
    ['Engine integrity', integrity.valid, integrity.detail],
    [
      'Managed runtime',
      runtime.ready,
      runtime.ready ? `Python ${runtime.pythonVersion}` : (runtime.reason ?? 'not installed'),
    ],
    [
      'System Python',
      systemPython !== null,
      systemPython ? `Python ${systemPython.version}` : 'requires Python 3.10–3.12',
    ],
    ['FFmpeg', ffmpeg, ffmpeg ? 'available' : 'not found'],
    ['ffprobe', ffprobe, ffprobe ? 'available' : 'not found'],
    ['yt-dlp JS runtime', true, `Node ${process.versions.node}`],
  ];
  if (includeLocal) {
    rows.push([
      'Local inference runtimes',
      runtime.ready,
      runtime.ready ? 'llama.cpp, faster-whisper, and CTranslate2 available' : 'not installed',
    ]);
    rows.push([
      'Verified local model pack',
      localModelsReady,
      localModelsReady ? 'chat, embedding, and speech models verified' : 'not installed or invalid',
    ]);
  }

  for (const [name, ready, detail] of rows) {
    console.log(`${ready ? chalk.green('✓') : chalk.red('✗')} ${name}: ${chalk.gray(detail)}`);
  }

  const ready =
    enginePath !== null &&
    integrity.valid &&
    runtime.ready &&
    ffmpeg &&
    ffprobe &&
    (!includeLocal || localModelsReady);
  console.log(
    ready
      ? chalk.green('\nArena is ready.\n')
      : chalk.yellow('\nRun arena setup to install or repair Arena.\n')
  );
  return ready;
}

export async function setupCommand(options: SetupOptions = {}): Promise<void> {
  logCommand('setup', { ...options });

  if (options.modelPack && !options.local) {
    console.log(chalk.red('\n✗ --model-pack requires --local.\n'));
    process.exitCode = 1;
    return;
  }

  if (typeof (process as NodeJS.Process & { pkg?: unknown }).pkg !== 'undefined') {
    if (options.local) {
      console.log(chalk.red('\n✗ Local inference add-ons require the npm-managed runtime.\n'));
      process.exitCode = 1;
      return;
    }
    console.log(chalk.green('\n✓ Arena standalone includes its processing runtime.\n'));
    return;
  }

  if (options.check) {
    if (!(await printCheck(options.local === true))) {
      process.exitCode = 1;
    }
    return;
  }

  console.log(chalk.bold('\nSet up Arena\n'));
  console.log(chalk.gray(`Runtime location: ${getRuntimeDir()}\n`));

  const enginePath = resolveEnginePath(__dirname);
  if (!enginePath) {
    console.log(chalk.red('✗ This Arena installation does not contain the Python engine.'));
    console.log(chalk.white('  Reinstall the npm package, then run arena setup again.\n'));
    process.exitCode = 1;
    return;
  }

  const integrity = await verifyEngineIntegrity(enginePath);
  if (!integrity.valid) {
    console.log(chalk.red(`✗ ${integrity.detail}`));
    console.log(chalk.white('  Reinstall Arena from npm before running setup again.\n'));
    process.exitCode = 1;
    return;
  }

  if (!(await ensureFfmpeg(options))) {
    process.exitCode = 1;
    return;
  }

  try {
    await recoverInterruptedRuntime();
  } catch (error) {
    console.log(chalk.red(`✗ ${(error as Error).message}\n`));
    process.exitCode = 1;
    return;
  }

  const currentStatus = await getInstalledRuntimeStatus(options.local === true);
  if (currentStatus.ready && !options.force) {
    console.log(
      chalk.green(`✓ Arena runtime is already ready (Python ${currentStatus.pythonVersion}).`)
    );
    if (options.modelPack) {
      const manifest = await readRuntimeManifest();
      if (!manifest) {
        console.log(chalk.red('✗ Arena runtime manifest is missing.\n'));
        process.exitCode = 1;
        return;
      }
      const spinner = ora(`Installing verified ${options.modelPack} model pack`).start();
      try {
        await installVerifiedModelPack(manifest.pythonPath, options.modelPack);
        spinner.succeed(`Verified ${options.modelPack} model pack installed`);
      } catch (error) {
        spinner.fail('Verified model installation failed');
        console.log(chalk.red(`\n${(error as Error).message}\n`));
        process.exitCode = 1;
      }
      return;
    }
    console.log(chalk.gray('  Use arena setup --force to rebuild it.\n'));
    return;
  }

  const basePython = await findCompatibleSystemPython();
  if (!basePython) {
    console.log(chalk.red('✗ Arena requires Python 3.10, 3.11, or 3.12.'));
    console.log(chalk.white(`  ${pythonInstallHelp()}`));
    console.log(chalk.gray('  Your global Python packages will not be modified.\n'));
    process.exitCode = 1;
    return;
  }

  if (options.local && !(await hasNativeCompiler())) {
    console.log(chalk.red('✗ Local llama.cpp setup requires a native C/C++ compiler.'));
    const help =
      process.platform === 'darwin'
        ? 'Run: xcode-select --install'
        : process.platform === 'win32'
          ? 'Install Visual Studio Build Tools with Desktop development with C++.'
          : 'Install GCC or Clang with your distribution package manager.';
    console.log(chalk.white(`  ${help}\n`));
    process.exitCode = 1;
    return;
  }

  if (options.force) {
    console.log(chalk.gray('Rebuilding the managed runtime from scratch.'));
  }

  const runtimeLabel = options.local ? 'Arena engine and local inference runtimes' : 'Arena engine';
  const spinner = ora(`Installing ${runtimeLabel} with Python ${basePython.version}`).start();
  try {
    const installed = await buildRuntime(
      basePython,
      enginePath,
      options.local === true,
      (message) => {
        spinner.text = message;
        if (!process.stdout.isTTY) {
          console.log(chalk.gray(`  ${message}`));
        }
      }
    );
    spinner.succeed(`Arena runtime installed (Python ${installed.pythonVersion})`);
    if (options.modelPack) {
      const manifest = await readRuntimeManifest();
      if (!manifest) {
        throw new Error('Runtime manifest missing after local installation');
      }
      const modelSpinner = ora(`Installing verified ${options.modelPack} model pack`).start();
      try {
        await installVerifiedModelPack(manifest.pythonPath, options.modelPack);
        modelSpinner.succeed(`Verified ${options.modelPack} model pack installed`);
      } catch (error) {
        modelSpinner.fail('Verified model installation failed');
        throw error;
      }
    }
    console.log(chalk.green('\n✓ Arena installation is ready.'));
    console.log(chalk.white('  Next: arena init'));
    console.log(chalk.white('  Verify anytime: arena setup --check\n'));
    if (options.local) {
      if (!options.modelPack) {
        console.log(chalk.white('  Install models: arena setup --local --model-pack lite'));
      }
      console.log(chalk.white('  See: docs/guides/local-inference.md\n'));
    }
  } catch (error) {
    const setupError = error instanceof Error ? error : new Error(String(error));
    spinner.fail('Arena runtime installation failed');
    logger.error('Arena setup failed', setupError, { enginePath, python: basePython.command });
    console.log(chalk.red(`\n${setupError.message}\n`));
    console.log(chalk.white('Your previous working runtime, if any, was preserved.'));
    console.log(chalk.gray('Fix the reported issue and rerun arena setup --force.\n'));
    process.exitCode = 1;
  }
}
