#!/usr/bin/env node

/**
 * Install the prepared Arena npm tarball as a real consumer.
 *
 * This script intentionally uses only Node.js APIs so the same assertions run
 * on Windows, macOS, and Linux. It does not read files from the source checkout
 * after resolving the tarball argument.
 */

const crypto = require('node:crypto');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { spawnSync } = require('node:child_process');

const PACKAGE_NAME = '@whitegodkingsley/arena-cli';
const DEFAULT_TIMEOUT_MS = 10 * 60 * 1000;
const MAX_CAPTURE_CHARS = 24_000;
const REDACTED_PATHS = new Set([os.homedir()]);

function directNodeCommand(script, displayName) {
  return {
    executable: process.execPath,
    args: [script],
    displayName,
  };
}

function resolveInvocation(command, args) {
  if (typeof command === 'string') {
    return {
      executable: command,
      args,
      displayName: path.basename(command),
    };
  }
  return {
    executable: command.executable,
    args: [...command.args, ...args],
    displayName: command.displayName ?? path.basename(command.executable),
  };
}

function npmCliCandidates(nodeExecutable, npmExecPath, platform = process.platform) {
  const pathApi = platform === 'win32' ? path.win32 : path;
  const nodeDirectory = pathApi.dirname(nodeExecutable);
  return [
    npmExecPath,
    pathApi.join(nodeDirectory, 'node_modules', 'npm', 'bin', 'npm-cli.js'),
    pathApi.resolve(nodeDirectory, '..', 'lib', 'node_modules', 'npm', 'bin', 'npm-cli.js'),
  ].filter(Boolean);
}

function npmCliFromPath(searchPath, platform = process.platform) {
  if (platform === 'win32') return null;
  for (const directory of String(searchPath ?? '').split(path.delimiter)) {
    if (!directory) continue;
    const candidate = path.join(directory, 'npm');
    if (!fs.existsSync(candidate)) continue;
    const resolved = fs.realpathSync(candidate);
    if (path.basename(resolved) === 'npm-cli.js') return resolved;
  }
  return null;
}

function resolveNpmCommand() {
  const candidates = npmCliCandidates(process.execPath, process.env.npm_execpath);
  const pathCandidate = npmCliFromPath(process.env.PATH);
  if (pathCandidate) candidates.push(pathCandidate);
  const pathApi = process.platform === 'win32' ? path.win32 : path;
  const npmCli = candidates.find(
    (candidate) =>
      pathApi.basename(candidate).toLowerCase() === 'npm-cli.js' && fs.existsSync(candidate)
  );
  if (!npmCli) {
    throw new Error('Could not locate npm-cli.js for the active Node.js runtime');
  }
  return directNodeCommand(npmCli, 'npm');
}

function packageBinEntry(packageMetadata, name) {
  const entry =
    typeof packageMetadata.bin === 'string' ? packageMetadata.bin : packageMetadata.bin?.[name];
  const normalized = typeof entry === 'string' ? path.normalize(entry) : '';
  if (
    normalized.length === 0 ||
    path.isAbsolute(normalized) ||
    normalized === '..' ||
    normalized.startsWith(`..${path.sep}`)
  ) {
    throw new Error(`Installed package does not define a valid ${name} executable`);
  }
  return normalized;
}

function usage() {
  return [
    'Usage: node scripts/consumer-install-smoke.cjs --tarball <file-or-directory>',
    '       [--evidence <json-file>] [--setup] [--setup-recovery]',
    '       [--expected-python <major.minor>]',
    '       [--keep] [--timeout-ms <milliseconds>]',
  ].join('\n');
}

function parseArgs(argv) {
  const options = {
    evidence: path.resolve('consumer-install-evidence.json'),
    keep: false,
    setupRecovery: false,
    setup: false,
    timeoutMs: DEFAULT_TIMEOUT_MS,
  };

  for (let index = 0; index < argv.length; index += 1) {
    const argument = argv[index];
    if (argument === '--keep') {
      options.keep = true;
    } else if (argument === '--setup-recovery') {
      options.setup = true;
      options.setupRecovery = true;
    } else if (argument === '--setup') {
      options.setup = true;
    } else if (
      argument === '--tarball' ||
      argument === '--evidence' ||
      argument === '--expected-python' ||
      argument === '--timeout-ms'
    ) {
      const value = argv[index + 1];
      if (!value) {
        throw new Error(`Missing value for ${argument}\n${usage()}`);
      }
      index += 1;
      if (argument === '--tarball') options.tarball = value;
      if (argument === '--evidence') options.evidence = path.resolve(value);
      if (argument === '--expected-python') options.expectedPython = value;
      if (argument === '--timeout-ms') options.timeoutMs = Number.parseInt(value, 10);
    } else if (argument === '--help' || argument === '-h') {
      console.log(usage());
      process.exit(0);
    } else {
      throw new Error(`Unknown argument: ${argument}\n${usage()}`);
    }
  }

  if (!options.tarball) {
    throw new Error(`--tarball is required\n${usage()}`);
  }
  if (!Number.isInteger(options.timeoutMs) || options.timeoutMs < 1000) {
    throw new Error('--timeout-ms must be an integer of at least 1000');
  }

  return options;
}

function resolveTarball(input) {
  const candidate = path.resolve(input);
  if (!fs.existsSync(candidate)) {
    throw new Error(`Tarball path does not exist: ${candidate}`);
  }

  if (fs.statSync(candidate).isDirectory()) {
    const tarballs = fs
      .readdirSync(candidate)
      .filter((name) => name.endsWith('.tgz'))
      .map((name) => path.join(candidate, name));
    if (tarballs.length !== 1) {
      throw new Error(`Expected exactly one .tgz in ${candidate}; found ${tarballs.length}`);
    }
    return tarballs[0];
  }

  if (!candidate.endsWith('.tgz')) {
    throw new Error(`Expected an npm .tgz tarball: ${candidate}`);
  }
  return candidate;
}

function sha256(filename) {
  return crypto.createHash('sha256').update(fs.readFileSync(filename)).digest('hex');
}

function trimOutput(value) {
  let text = String(value ?? '').replace(/\u001b\[[0-9;]*m/g, '');
  for (const redactedPath of REDACTED_PATHS) {
    text = text.replaceAll(redactedPath, '<redacted-path>');
  }
  if (text.length <= MAX_CAPTURE_CHARS) return text;
  return `${text.slice(0, MAX_CAPTURE_CHARS)}\n... output truncated ...`;
}

function runCommand(evidence, name, command, args, options = {}) {
  const startedAt = Date.now();
  const invocation = resolveInvocation(command, args);
  const result = spawnSync(invocation.executable, invocation.args, {
    cwd: options.cwd,
    env: options.env,
    encoding: 'utf8',
    shell: options.shell ?? false,
    timeout: options.timeoutMs,
    windowsHide: true,
    stdio: ['ignore', 'pipe', 'pipe'],
  });
  const record = {
    name,
    executable: invocation.displayName,
    durationMs: Date.now() - startedAt,
    exitCode: result.status,
    signal: result.signal,
    stdout: trimOutput(result.stdout),
    stderr: trimOutput(result.stderr),
  };
  evidence.commands.push(record);

  if (result.error) {
    throw new Error(`${name} could not start: ${result.error.message}`);
  }
  if (options.expectFailure && result.status === 0) {
    throw new Error(`${name} unexpectedly succeeded`);
  }
  if (!options.expectFailure && result.status !== 0) {
    throw new Error(
      `${name} failed with exit code ${String(result.status)}\n${record.stderr || record.stdout}`
    );
  }
  return record;
}

function commandOutput(record) {
  return `${record.stdout}\n${record.stderr}`;
}

function runtimeScratchEntries(runtimeDir) {
  return fs
    .readdirSync(runtimeDir, { withFileTypes: true })
    .filter(
      (entry) =>
        entry.name === 'install.lock' ||
        /^python\.(?:installing|previous)-\d+$/.test(entry.name) ||
        /^engine-source-\d+$/.test(entry.name)
    )
    .map((entry) => entry.name)
    .sort();
}

function managedArenaPackage(pythonPath) {
  const environment = path.dirname(path.dirname(pythonPath));
  const candidates =
    process.platform === 'win32'
      ? [path.join(environment, 'Lib', 'site-packages', 'arena')]
      : fs
          .readdirSync(path.join(environment, 'lib'), { withFileTypes: true })
          .filter((entry) => entry.isDirectory() && entry.name.startsWith('python'))
          .map((entry) => path.join(environment, 'lib', entry.name, 'site-packages', 'arena'));
  return candidates.find((candidate) => fs.existsSync(candidate)) ?? null;
}

function runSetupRecoverySmoke(
  evidence,
  arenaCommand,
  arenaHome,
  workspace,
  childEnv,
  timeoutMs,
  shell
) {
  const runtimeDir = path.join(arenaHome, 'runtime');
  const manifestPath = path.join(runtimeDir, 'install.json');
  const originalManifest = JSON.parse(fs.readFileSync(manifestPath, 'utf8'));
  const originalEnvironment = path.dirname(path.dirname(originalManifest.pythonPath));
  const lockPath = path.join(runtimeDir, 'install.lock');

  fs.writeFileSync(
    lockPath,
    `${JSON.stringify({ pid: process.pid, startedAt: new Date().toISOString() })}\n`,
    { mode: 0o600 }
  );
  try {
    const locked = runCommand(
      evidence,
      'reject concurrent managed setup',
      arenaCommand,
      ['setup', '--yes'],
      { cwd: workspace, env: childEnv, shell, timeoutMs: 60_000, expectFailure: true }
    );
    if (!commandOutput(locked).includes('Another Arena setup is already running')) {
      throw new Error('Concurrent setup failed without the expected lock-owner diagnostic');
    }
  } finally {
    fs.rmSync(lockPath, { force: true });
  }
  evidence.assertions.concurrentSetupIsRejected = true;

  const interruptedVenv = path.join(runtimeDir, 'python.installing-999999');
  const interruptedEngine = path.join(runtimeDir, 'engine-source-999999');
  fs.mkdirSync(interruptedVenv, { recursive: true });
  fs.mkdirSync(interruptedEngine, { recursive: true });
  fs.writeFileSync(lockPath, '{}\n', { mode: 0o600 });
  runCommand(evidence, 'recover stale managed setup state', arenaCommand, ['setup', '--yes'], {
    cwd: workspace,
    env: childEnv,
    shell,
    timeoutMs: 60_000,
  });
  if (runtimeScratchEntries(runtimeDir).length !== 0) {
    throw new Error('Stale setup recovery left lock or staging files behind');
  }
  evidence.assertions.staleSetupStateIsRecovered = true;

  const timeoutEnv = {
    ...childEnv,
    ARENA_SETUP_TIMEOUT_MINUTES: '0.001',
  };
  const timedOut = runCommand(
    evidence,
    'preserve runtime after timed-out rebuild',
    arenaCommand,
    ['setup', '--yes', '--force'],
    { cwd: workspace, env: timeoutEnv, shell, timeoutMs, expectFailure: true }
  );
  if (!commandOutput(timedOut).includes('Timed out after')) {
    throw new Error('Forced setup failed without exercising the configured timeout');
  }
  const preservedManifest = JSON.parse(fs.readFileSync(manifestPath, 'utf8'));
  if (
    preservedManifest.pythonPath !== originalManifest.pythonPath ||
    preservedManifest.installedAt !== originalManifest.installedAt ||
    !fs.existsSync(originalManifest.pythonPath) ||
    runtimeScratchEntries(runtimeDir).length !== 0
  ) {
    throw new Error('Timed-out setup did not preserve the previous managed runtime cleanly');
  }
  runCommand(evidence, 'check preserved runtime after setup failure', arenaCommand, ['setup', '--check'], {
    cwd: workspace,
    env: childEnv,
    shell,
    timeoutMs: 60_000,
  });
  evidence.assertions.failedSetupPreservesWorkingRuntime = true;

  const arenaPackage = managedArenaPackage(originalManifest.pythonPath);
  if (!arenaPackage) {
    throw new Error('Could not locate the managed engine package for repair testing');
  }
  const damagedPackage = `${arenaPackage}.arena-smoke-damaged`;
  fs.renameSync(arenaPackage, damagedPackage);

  const damagedCheck = runCommand(
    evidence,
    'detect damaged managed runtime',
    arenaCommand,
    ['setup', '--check'],
    { cwd: workspace, env: childEnv, shell, timeoutMs: 60_000, expectFailure: true }
  );
  if (!commandOutput(damagedCheck).includes('No module named')) {
    throw new Error('Damaged runtime was not reported as an engine import failure');
  }
  evidence.assertions.damagedRuntimeIsDetected = true;

  runCommand(evidence, 'repair damaged managed runtime', arenaCommand, ['setup', '--yes'], {
    cwd: workspace,
    env: childEnv,
    shell,
    timeoutMs,
  });
  runCommand(evidence, 'check repaired managed runtime', arenaCommand, ['setup', '--check'], {
    cwd: workspace,
    env: childEnv,
    shell,
    timeoutMs: 60_000,
  });
  const repairedManifest = JSON.parse(fs.readFileSync(manifestPath, 'utf8'));
  if (
    repairedManifest.pythonPath === originalManifest.pythonPath ||
    !fs.existsSync(repairedManifest.pythonPath) ||
    fs.existsSync(originalEnvironment) ||
    runtimeScratchEntries(runtimeDir).length !== 0
  ) {
    throw new Error('Managed runtime repair was not promoted and cleaned up atomically');
  }
  evidence.managedRuntime.repairedPythonPathChanged = true;
  evidence.assertions.damagedRuntimeIsRepaired = true;
  evidence.assertions.setupRecoveryLeavesNoScratchState = true;
}

function probeVersion(evidence, name, command, args, env, shell = false) {
  try {
    const record = runCommand(evidence, name, command, args, {
      env,
      shell,
      timeoutMs: 30_000,
    });
    return (record.stdout || record.stderr).split(/\r?\n/).find(Boolean) ?? null;
  } catch {
    return null;
  }
}

function writeEvidence(filename, evidence) {
  fs.mkdirSync(path.dirname(filename), { recursive: true });
  fs.writeFileSync(filename, `${JSON.stringify(evidence, null, 2)}\n`, { mode: 0o600 });
}

function pathIsInside(parent, candidate) {
  const relative = path.relative(path.resolve(parent), path.resolve(candidate));
  return relative !== '' && !relative.startsWith(`..${path.sep}`) && relative !== '..' && !path.isAbsolute(relative);
}

function runLocalProcessingSmoke(evidence, arenaCommand, workspace, childEnv, timeoutMs, shell) {
  const fixture = path.join(workspace, 'fixture video ø.mp4');
  const audio = path.join(workspace, 'extracted audio.wav');
  const scenes = path.join(workspace, 'detected scenes.json');

  runCommand(
    evidence,
    'create deterministic local fixture',
    'ffmpeg',
    [
      '-hide_banner',
      '-loglevel',
      'error',
      '-y',
      '-f',
      'lavfi',
      '-i',
      'testsrc2=size=320x240:rate=24:duration=3',
      '-f',
      'lavfi',
      '-i',
      'sine=frequency=1000:sample_rate=16000:duration=3',
      '-c:v',
      'mpeg4',
      '-q:v',
      '8',
      '-c:a',
      'aac',
      '-shortest',
      fixture,
    ],
    { cwd: workspace, env: childEnv, timeoutMs: 60_000 }
  );
  runCommand(
    evidence,
    'probe local fixture',
    'ffprobe',
    ['-v', 'error', '-show_entries', 'format=duration,size', '-of', 'json', fixture],
    { cwd: workspace, env: childEnv, timeoutMs: 30_000 }
  );
  runCommand(
    evidence,
    'extract local audio',
    arenaCommand,
    ['extract-audio', fixture, '--output', audio, '--format', 'wav'],
    { cwd: workspace, env: childEnv, shell, timeoutMs }
  );
  runCommand(
    evidence,
    'detect local scenes',
    arenaCommand,
    [
      'detect-scenes',
      fixture,
      '--output',
      scenes,
      '--threshold',
      '0.15',
      '--min-duration',
      '0.2',
    ],
    { cwd: workspace, env: childEnv, shell, timeoutMs }
  );

  if (!fs.existsSync(audio) || fs.statSync(audio).size === 0) {
    throw new Error('Local audio extraction did not produce a non-empty output');
  }
  if (!fs.existsSync(scenes) || fs.statSync(scenes).size === 0) {
    throw new Error('Local scene detection did not produce a non-empty output');
  }
  const sceneReport = JSON.parse(fs.readFileSync(scenes, 'utf8'));
  evidence.localProcessing = {
    fixtureBytes: fs.statSync(fixture).size,
    audioBytes: fs.statSync(audio).size,
    sceneReportBytes: fs.statSync(scenes).size,
    sceneCount: sceneReport.scene_count ?? sceneReport.sceneCount ?? null,
  };
  evidence.assertions.localProcessingStayedInWorkspace = [fixture, audio, scenes].every((file) =>
    pathIsInside(workspace, file)
  );
  if (!evidence.assertions.localProcessingStayedInWorkspace) {
    throw new Error('Local processing wrote outside the isolated workspace');
  }
  evidence.assertions.localProcessingCompletedWithoutCredentials = true;
}

function main() {
  const options = parseArgs(process.argv.slice(2));
  const tarball = resolveTarball(options.tarball);
  const metadataPath = path.join(path.dirname(tarball), 'artifact-metadata.json');
  const artifactMetadata = fs.existsSync(metadataPath)
    ? JSON.parse(fs.readFileSync(metadataPath, 'utf8'))
    : null;
  const temporaryRoot = fs.mkdtempSync(path.join(os.tmpdir(), 'arena consumer smoke '));
  REDACTED_PATHS.add(temporaryRoot);
  REDACTED_PATHS.add(fs.realpathSync(temporaryRoot));
  const prefix = path.join(temporaryRoot, 'npm prefix ø');
  const npmCache = path.join(temporaryRoot, 'empty npm cache');
  const arenaHome = path.join(temporaryRoot, 'Aréna Home');
  const workspace = path.join(temporaryRoot, 'consumer workspace ø');
  const processTemp = path.join(temporaryRoot, 'process temp');
  const npmUserConfig = path.join(temporaryRoot, 'isolated.npmrc');
  for (const directory of [prefix, npmCache, arenaHome, workspace, processTemp]) {
    fs.mkdirSync(directory, { recursive: true });
  }
  fs.writeFileSync(npmUserConfig, 'fund=false\naudit=false\n', { mode: 0o600 });

  const childEnv = {
    ...process.env,
    ARENA_HOME: arenaHome,
    NO_COLOR: '1',
    OPENAI_API_KEY: '',
    OPENAI_BASE_URL: '',
    NPM_CONFIG_CACHE: npmCache,
    NPM_CONFIG_PREFIX: prefix,
    NPM_CONFIG_USERCONFIG: npmUserConfig,
    TEMP: processTemp,
    TMP: processTemp,
    TMPDIR: processTemp,
  };
  const binDirectory = process.platform === 'win32' ? prefix : path.join(prefix, 'bin');
  childEnv.PATH = `${binDirectory}${path.delimiter}${process.env.PATH ?? ''}`;
  const installEnv = {
    ...childEnv,
    // npm and Node remain available, while FFmpeg, Python, and package-manager
    // paths are deliberately absent during the read-only postinstall check.
    PATH: `${binDirectory}${path.delimiter}${path.dirname(process.execPath)}`,
    NPM_CONFIG_SCRIPT_SHELL:
      process.platform === 'win32'
        ? (process.env.ComSpec ?? 'C:\\Windows\\System32\\cmd.exe')
        : '/bin/sh',
  };

  const npmCommand = resolveNpmCommand();
  const packageRoot =
    process.platform === 'win32'
      ? path.join(prefix, 'node_modules', ...PACKAGE_NAME.split('/'))
      : path.join(prefix, 'lib', 'node_modules', ...PACKAGE_NAME.split('/'));
  const arenaShim =
    process.platform === 'win32' ? path.join(prefix, 'arena.cmd') : path.join(prefix, 'bin', 'arena');

  const evidence = {
    schemaVersion: 1,
    status: 'running',
    startedAt: new Date().toISOString(),
    platform: {
      os: os.platform(),
      release: os.release(),
      architecture: os.arch(),
      node: process.version,
      npm: null,
      python: null,
      pip: null,
      ffmpeg: null,
    },
    artifact: {
      filename: path.basename(tarball),
      sha256: sha256(tarball),
      packageName: null,
      packageVersion: null,
      engineVersion: null,
      prepared: false,
    },
    isolation: {
      outsideSourceCheckout: (() => {
        const relative = path.relative(path.resolve(__dirname, '..', '..'), workspace);
        return relative === '..' || relative.startsWith(`..${path.sep}`) || path.isAbsolute(relative);
      })(),
      pathWithSpaces: workspace.includes(' '),
      pathWithUnicode: /[^\x00-\x7F]/.test(workspace),
      emptyNpmCache: fs.readdirSync(npmCache).length === 0,
    },
    commands: [],
    assertions: {},
  };

  try {
    if (artifactMetadata) {
      if (
        artifactMetadata.tarball !== path.basename(tarball) ||
        artifactMetadata.sha256 !== evidence.artifact.sha256
      ) {
        throw new Error('Tarball digest does not match artifact-metadata.json');
      }
      evidence.assertions.tarballDigestMatchesBuildMetadata = true;
    }
    evidence.platform.npm = probeVersion(
      evidence,
      'npm version',
      npmCommand,
      ['--version'],
      childEnv
    );
    evidence.platform.python =
      probeVersion(evidence, 'python3 version', 'python3', ['--version'], childEnv) ??
      probeVersion(evidence, 'python version', 'python', ['--version'], childEnv);
    evidence.platform.ffmpeg = probeVersion(
      evidence,
      'ffmpeg version',
      'ffmpeg',
      ['-version'],
      childEnv
    );
    const installFfmpeg = probeVersion(
      evidence,
      'confirm FFmpeg absent during postinstall',
      'ffmpeg',
      ['-version'],
      installEnv
    );
    const installPython =
      probeVersion(
        evidence,
        'confirm python3 absent during postinstall',
        'python3',
        ['--version'],
        installEnv
      ) ??
      probeVersion(
        evidence,
        'confirm python absent during postinstall',
        'python',
        ['--version'],
        installEnv
      );
    evidence.assertions.postinstallPrerequisitesWereAbsent =
      installFfmpeg === null && installPython === null;
    if (!evidence.assertions.postinstallPrerequisitesWereAbsent) {
      throw new Error('Could not isolate FFmpeg and Python from the npm postinstall environment');
    }

    const install = runCommand(
      evidence,
      'install packed tarball',
      npmCommand,
      [
        'install',
        '--global',
        '--foreground-scripts',
        '--no-audit',
        '--no-fund',
        '--prefix',
        prefix,
        tarball,
      ],
      { cwd: workspace, env: installEnv, timeoutMs: options.timeoutMs }
    );
    evidence.assertions.postinstallAdvisoryRan = install.stdout.includes('Arena CLI installed.');
    if (!evidence.assertions.postinstallAdvisoryRan) {
      throw new Error('npm install did not show the Arena read-only postinstall advisory');
    }

    if (!fs.existsSync(arenaShim)) {
      throw new Error(`Global Arena executable was not created: ${arenaShim}`);
    }
    evidence.assertions.globalExecutableCreated = true;

    const installedPackage = JSON.parse(
      fs.readFileSync(path.join(packageRoot, 'package.json'), 'utf8')
    );
    evidence.artifact.packageName = installedPackage.name;
    evidence.artifact.packageVersion = installedPackage.version;
    evidence.artifact.prepared = installedPackage.arenaPreparedArtifact === true;
    const engineInit = fs.readFileSync(
      path.join(packageRoot, 'engine', 'arena', 'cli', '__init__.py'),
      'utf8'
    );
    evidence.artifact.engineVersion =
      /__version__\s*=\s*['"]([^'"]+)['"]/.exec(engineInit)?.[1] ?? null;
    if (installedPackage.name !== PACKAGE_NAME || installedPackage.arenaPreparedArtifact !== true) {
      throw new Error('Installed package identity does not match the prepared Arena artifact');
    }
    if (
      artifactMetadata &&
      (installedPackage.name !== artifactMetadata.packageName ||
        installedPackage.version !== artifactMetadata.packageVersion)
    ) {
      throw new Error('Installed package identity does not match artifact-metadata.json');
    }
    evidence.assertions.exactPreparedPackageInstalled = true;

    runCommand(
      evidence,
      'verify installed artifact',
      process.execPath,
      [path.join(packageRoot, 'scripts', 'verify-package.cjs'), '--engine-only'],
      { cwd: workspace, env: childEnv, timeoutMs: 60_000 }
    );
    evidence.assertions.engineManifestVerified = true;

    const arenaCommand =
      process.platform === 'win32'
        ? directNodeCommand(
            path.join(packageRoot, packageBinEntry(installedPackage, 'arena')),
            'arena'
          )
        : arenaShim;
    const version = runCommand(evidence, 'arena version', arenaCommand, ['--version'], {
      cwd: workspace,
      env: childEnv,
      timeoutMs: 30_000,
    });
    if (version.stdout.trim() !== installedPackage.version) {
      throw new Error(
        `arena --version returned ${JSON.stringify(version.stdout.trim())}; expected ${installedPackage.version}`
      );
    }
    evidence.assertions.cliVersionMatchesPackage = true;

    const help = runCommand(evidence, 'arena help', arenaCommand, ['--help'], {
      cwd: workspace,
      env: childEnv,
      timeoutMs: 30_000,
    });
    if (!help.stdout.includes('AI-powered video clip generation tool')) {
      throw new Error('arena --help did not contain the expected CLI description');
    }
    evidence.assertions.cliHelpWorksOutsideRepository = true;

    if (options.setup) {
      runCommand(evidence, 'install managed runtime', arenaCommand, ['setup', '--yes'], {
        cwd: workspace,
        env: childEnv,
        timeoutMs: options.timeoutMs,
      });
      runCommand(evidence, 'check managed runtime', arenaCommand, ['setup', '--check'], {
        cwd: workspace,
        env: childEnv,
        timeoutMs: 60_000,
      });

      const manifestPath = path.join(arenaHome, 'runtime', 'install.json');
      const runtimeManifest = JSON.parse(fs.readFileSync(manifestPath, 'utf8'));
      if (!pathIsInside(arenaHome, runtimeManifest.pythonPath) || !fs.existsSync(runtimeManifest.pythonPath)) {
        throw new Error('Managed Python is missing or outside the isolated ARENA_HOME');
      }
      evidence.managedRuntime = {
        cliVersion: runtimeManifest.cliVersion,
        pythonVersion: runtimeManifest.pythonVersion,
        pythonInsideArenaHome: true,
      };
      evidence.assertions.managedRuntimeIsIsolated = true;
      evidence.platform.pip = probeVersion(
        evidence,
        'managed pip version',
        runtimeManifest.pythonPath,
        ['-m', 'pip', '--version'],
        childEnv
      );
      const installedEngine = runCommand(
        evidence,
        'managed engine version',
        runtimeManifest.pythonPath,
        ['-c', 'from arena.cli import __version__; print(__version__)'],
        { cwd: workspace, env: childEnv, timeoutMs: 30_000 }
      ).stdout.trim();
      if (installedEngine !== evidence.artifact.engineVersion) {
        throw new Error(
          `Managed engine version ${installedEngine} does not match packaged engine ${evidence.artifact.engineVersion}`
        );
      }
      evidence.assertions.managedEngineMatchesPackage = true;
      if (
        options.expectedPython &&
        !runtimeManifest.pythonVersion.startsWith(`${options.expectedPython}.`)
      ) {
        throw new Error(
          `Managed runtime used Python ${runtimeManifest.pythonVersion}; expected ${options.expectedPython}.x`
        );
      }
      evidence.assertions.expectedPythonBoundaryUsed = options.expectedPython
        ? true
        : 'not-requested';

      runCommand(evidence, 'verify idempotent setup', arenaCommand, ['setup', '--yes'], {
        cwd: workspace,
        env: childEnv,
        timeoutMs: 60_000,
      });
      evidence.assertions.setupIsIdempotent = true;
      if (options.setupRecovery) {
        runSetupRecoverySmoke(
          evidence,
          arenaCommand,
          arenaHome,
          workspace,
          childEnv,
          options.timeoutMs,
          false
        );
      }
      runLocalProcessingSmoke(
        evidence,
        arenaCommand,
        workspace,
        childEnv,
        options.timeoutMs,
        false
      );
    }

    runCommand(evidence, 'uninstall Arena', npmCommand, ['uninstall', '--global', PACKAGE_NAME], {
      cwd: workspace,
      env: childEnv,
      timeoutMs: options.timeoutMs,
    });
    if (fs.existsSync(packageRoot) || fs.existsSync(arenaShim)) {
      throw new Error('npm uninstall left the installed Arena package or executable behind');
    }
    evidence.assertions.uninstallRemovedPackageAndExecutable = true;
    evidence.assertions.arenaHomeExplicitlyRetained = fs.existsSync(arenaHome);

    evidence.status = 'passed';
    evidence.finishedAt = new Date().toISOString();
    writeEvidence(options.evidence, evidence);
    console.log(`Consumer installation smoke test passed for ${os.platform()} ${os.arch()}.`);
    console.log(`Evidence: ${options.evidence}`);
  } catch (error) {
    evidence.status = 'failed';
    evidence.error = error instanceof Error ? error.message : String(error);
    evidence.finishedAt = new Date().toISOString();
    writeEvidence(options.evidence, evidence);
    throw error;
  } finally {
    if (options.keep) {
      console.log(`Retained isolated consumer directory: ${temporaryRoot}`);
    } else {
      fs.rmSync(temporaryRoot, { force: true, recursive: true });
    }
  }
}

module.exports = {
  npmCliCandidates,
  npmCliFromPath,
  packageBinEntry,
  resolveInvocation,
};

if (require.main === module) {
  try {
    main();
  } catch (error) {
    console.error(`Consumer installation smoke test failed: ${error.message}`);
    process.exitCode = 1;
  }
}
