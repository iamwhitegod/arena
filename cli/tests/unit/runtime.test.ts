import { afterEach, describe, expect, it } from 'vitest';
import fs from 'fs-extra';
import os from 'os';
import path from 'path';
import {
  getActiveBinDir,
  getActivePythonPath,
  getArenaHome,
  getManagedBinDir,
  getManagedPythonPath,
  getRuntimeManifestPath,
  isSupportedPythonVersion,
  parsePythonVersion,
  prependPath,
  pythonCandidates,
  readRuntimeManifest,
  resolveEnginePath,
  RUNTIME_SCHEMA_VERSION,
  writeRuntimeManifest,
} from '../../src/core/runtime.js';

const originalArenaHome = process.env.ARENA_HOME;
const originalArenaPython = process.env.ARENA_PYTHON;

afterEach(async () => {
  if (originalArenaHome === undefined) {
    delete process.env.ARENA_HOME;
  } else {
    process.env.ARENA_HOME = originalArenaHome;
  }
  if (originalArenaPython === undefined) {
    delete process.env.ARENA_PYTHON;
  } else {
    process.env.ARENA_PYTHON = originalArenaPython;
  }
});

describe('managed runtime paths', () => {
  it('uses ARENA_HOME when supplied', () => {
    const arenaHome = path.join(os.tmpdir(), 'arena-custom-home');
    process.env.ARENA_HOME = arenaHome;
    expect(getArenaHome()).toBe(path.resolve(arenaHome));
    expect(getRuntimeManifestPath()).toBe(
      path.join(path.resolve(arenaHome), 'runtime', 'install.json')
    );
  });

  it('builds platform-specific virtual environment paths', () => {
    const arenaHome = path.join(os.tmpdir(), 'arena-home');
    process.env.ARENA_HOME = arenaHome;
    expect(getManagedBinDir('darwin')).toBe(path.join(arenaHome, 'runtime', 'python', 'bin'));
    expect(getManagedPythonPath('linux')).toBe(
      path.join(arenaHome, 'runtime', 'python', 'bin', 'python')
    );
    expect(getManagedPythonPath('win32')).toBe(
      path.join(arenaHome, 'runtime', 'python', 'Scripts', 'python.exe')
    );
  });

  it('prepends executable directories using the platform separator', () => {
    expect(prependPath('/usr/bin', '/arena/bin', 'linux')).toBe('/arena/bin:/usr/bin');
    expect(prependPath('C:\\Windows', 'C:\\Arena', 'win32')).toBe('C:\\Arena;C:\\Windows');
  });
});

describe('Python compatibility', () => {
  it('prefers an explicitly selected Python executable', () => {
    process.env.ARENA_PYTHON = path.join(os.tmpdir(), 'selected python');
    expect(pythonCandidates('win32')[0]).toEqual({
      command: process.env.ARENA_PYTHON,
      args: [],
    });
    expect(pythonCandidates('linux')[0]).toEqual({
      command: process.env.ARENA_PYTHON,
      args: [],
    });
  });

  it('parses versions from stdout or stderr text', () => {
    expect(parsePythonVersion('Python 3.12.4')).toBe('3.12.4');
    expect(parsePythonVersion('launcher\nPython 3.9')).toBe('3.9');
    expect(parsePythonVersion('not python')).toBeNull();
  });

  it('accepts Python 3.10 through 3.12', () => {
    expect(isSupportedPythonVersion('3.10.0')).toBe(true);
    expect(isSupportedPythonVersion('3.11.9')).toBe(true);
    expect(isSupportedPythonVersion('3.12.4')).toBe(true);
  });

  it('rejects unsupported Python versions', () => {
    expect(isSupportedPythonVersion('3.8.19')).toBe(false);
    expect(isSupportedPythonVersion('3.9.19')).toBe(false);
    expect(isSupportedPythonVersion('3.13.0')).toBe(false);
    expect(isSupportedPythonVersion('2.7.18')).toBe(false);
    expect(isSupportedPythonVersion('invalid')).toBe(false);
  });
});

describe('engine resolution', () => {
  it('finds the development engine from a CLI source directory', () => {
    const sourceCommandsDir = path.resolve(process.cwd(), 'src', 'commands');
    const enginePath = resolveEnginePath(sourceCommandsDir);
    expect(enginePath).toBe(path.resolve(process.cwd(), '..', 'engine'));
  });

  it('finds a packaged engine from a deeply nested module directory', async () => {
    const packageRoot = await fs.mkdtemp(path.join(os.tmpdir(), 'arena-runtime-package-'));
    const nestedDir = path.join(packageRoot, 'dist', 'generated', 'bridge', 'nested');

    try {
      await fs.writeJson(path.join(packageRoot, 'package.json'), {
        name: '@whitegodkingsley/arena-cli',
      });
      await fs.ensureFile(path.join(packageRoot, 'engine', 'setup.py'));
      await fs.ensureFile(path.join(packageRoot, 'engine', 'arena', '__init__.py'));
      await fs.ensureDir(nestedDir);

      expect(resolveEnginePath(nestedDir)).toBe(path.join(packageRoot, 'engine'));
    } finally {
      await fs.remove(packageRoot);
    }
  });

  it('returns null when neither packaged nor development engine exists', async () => {
    const temporaryDir = await fs.mkdtemp(path.join(os.tmpdir(), 'arena-runtime-engine-'));
    try {
      expect(resolveEnginePath(path.join(temporaryDir, 'dist', 'commands'))).toBeNull();
    } finally {
      await fs.remove(temporaryDir);
    }
  });
});

describe('runtime manifest', () => {
  it('writes and reads a validated owner-only manifest', async () => {
    const temporaryDir = await fs.mkdtemp(path.join(os.tmpdir(), 'arena-runtime-home-'));
    process.env.ARENA_HOME = temporaryDir;

    try {
      const manifest = {
        schemaVersion: RUNTIME_SCHEMA_VERSION,
        cliVersion: '0.4.1',
        pythonPath: '/tmp/arena/python',
        pythonVersion: '3.12.4',
        installedAt: '2026-08-12T12:00:00.000Z',
      } as const;

      await writeRuntimeManifest(manifest);
      await expect(readRuntimeManifest()).resolves.toEqual(manifest);

      if (process.platform !== 'win32') {
        const mode = (await fs.stat(getRuntimeManifestPath())).mode & 0o777;
        expect(mode).toBe(0o600);
      }
    } finally {
      await fs.remove(temporaryDir);
    }
  });

  it('resolves the active versioned environment from the manifest', async () => {
    const temporaryDir = await fs.mkdtemp(path.join(os.tmpdir(), 'arena-runtime-home-'));
    process.env.ARENA_HOME = temporaryDir;
    const pythonPath = path.join(
      temporaryDir,
      'runtime',
      'environments',
      'python-0.4.1-test',
      'bin',
      'python'
    );

    try {
      await fs.ensureFile(pythonPath);
      await writeRuntimeManifest({
        schemaVersion: RUNTIME_SCHEMA_VERSION,
        cliVersion: '0.4.1',
        pythonPath,
        pythonVersion: '3.12.4',
        installedAt: '2026-08-12T12:00:00.000Z',
      });

      expect(getActivePythonPath()).toBe(pythonPath);
      expect(getActiveBinDir()).toBe(path.dirname(pythonPath));
    } finally {
      await fs.remove(temporaryDir);
    }
  });

  it('rejects malformed manifests', async () => {
    const temporaryDir = await fs.mkdtemp(path.join(os.tmpdir(), 'arena-runtime-home-'));
    process.env.ARENA_HOME = temporaryDir;

    try {
      await fs.ensureDir(path.dirname(getRuntimeManifestPath()));
      await fs.writeJson(getRuntimeManifestPath(), { schemaVersion: 99 });
      await expect(readRuntimeManifest()).resolves.toBeNull();
    } finally {
      await fs.remove(temporaryDir);
    }
  });
});
