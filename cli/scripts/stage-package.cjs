#!/usr/bin/env node

/** Build a minimal, auditable npm publish directory. */

const crypto = require('crypto');
const fs = require('fs-extra');
const path = require('path');

const cliRoot = path.resolve(__dirname, '..');
const projectRoot = path.resolve(cliRoot, '..');
const stageRoot = path.join(cliRoot, '.package');
const sourceEngine = path.join(projectRoot, 'engine');
const { verifyArtifact: verifyPreparedArtifact } = require('./verify-package.cjs');

function normalized(relativePath) {
  return relativePath.split(path.sep).join('/');
}

async function listFiles(root, current = root) {
  const entries = await fs.readdir(current, { withFileTypes: true });
  const files = [];
  for (const entry of entries) {
    const absolutePath = path.join(current, entry.name);
    if (entry.isSymbolicLink()) {
      throw new Error(
        `Symlinks are not allowed in the npm artifact: ${normalized(path.relative(root, absolutePath))}`
      );
    }
    if (entry.isDirectory()) {
      files.push(...(await listFiles(root, absolutePath)));
    } else if (entry.isFile()) {
      files.push(normalized(path.relative(root, absolutePath)));
    }
  }
  return files.sort();
}

function includeEngineSource(sourcePath) {
  const relativePath = normalized(path.relative(path.join(sourceEngine, 'arena'), sourcePath));
  const parts = relativePath.split('/');
  return !(
    parts.includes('__pycache__') ||
    parts.includes('.pytest_cache') ||
    relativePath.endsWith('.pyc') ||
    relativePath.endsWith('.pyo') ||
    relativePath.endsWith('.DS_Store')
  );
}

async function copyArtifact() {
  await fs.remove(stageRoot);
  await fs.ensureDir(stageRoot);

  const packageJson = await fs.readJson(path.join(cliRoot, 'package.json'));
  packageJson.scripts = {
    postinstall: 'node scripts/postinstall.cjs',
    prepack: 'node scripts/verify-package.cjs',
  };
  packageJson.files = [
    'dist/',
    'scripts/postinstall.cjs',
    'scripts/verify-package.cjs',
    'engine/',
    'README.md',
    'LICENSE',
  ];
  delete packageJson.devDependencies;
  delete packageJson['lint-staged'];
  delete packageJson.pkg;
  packageJson.arenaPreparedArtifact = true;

  await fs.writeJson(path.join(stageRoot, 'package.json'), packageJson, { spaces: 2 });
  await fs.copy(path.join(cliRoot, 'dist'), path.join(stageRoot, 'dist'));
  await fs.copy(path.join(cliRoot, 'README.md'), path.join(stageRoot, 'README.md'));
  await fs.copy(path.join(cliRoot, 'LICENSE'), path.join(stageRoot, 'LICENSE'));
  await fs.copy(
    path.join(cliRoot, 'scripts', 'postinstall.cjs'),
    path.join(stageRoot, 'scripts', 'postinstall.cjs')
  );
  await fs.copy(
    path.join(cliRoot, 'scripts', 'verify-package.cjs'),
    path.join(stageRoot, 'scripts', 'verify-package.cjs')
  );

  const stagedEngine = path.join(stageRoot, 'engine');
  await fs.copy(path.join(sourceEngine, 'arena'), path.join(stagedEngine, 'arena'), {
    filter: includeEngineSource,
  });
  for (const filename of [
    'setup.py',
    'requirements.txt',
    'requirements.lock',
    'build-requirements.txt',
    'build-requirements.lock',
    'arena-cli',
  ]) {
    await fs.copy(path.join(sourceEngine, filename), path.join(stagedEngine, filename));
  }
  if (process.platform !== 'win32') {
    await fs.chmod(path.join(stagedEngine, 'arena-cli'), 0o755);
  }
}

async function writeEngineManifest() {
  const engineRoot = path.join(stageRoot, 'engine');
  const files = (await listFiles(engineRoot)).filter((file) => file !== 'MANIFEST.sha256');
  const lines = [];
  for (const file of files) {
    const content = await fs.readFile(path.join(engineRoot, file));
    lines.push(`${crypto.createHash('sha256').update(content).digest('hex')}  ${file}`);
  }
  await fs.writeFile(path.join(engineRoot, 'MANIFEST.sha256'), `${lines.join('\n')}\n`, {
    mode: 0o644,
  });
}

async function verifyArtifact() {
  const files = await listFiles(stageRoot);
  const allowed = [
    /^(package\.json|README\.md|LICENSE)$/,
    /^dist\//,
    /^scripts\/(postinstall|verify-package)\.cjs$/,
    /^engine\/(setup\.py|requirements\.txt|requirements\.lock|build-requirements\.txt|build-requirements\.lock|arena-cli|MANIFEST\.sha256)$/,
    /^engine\/arena\//,
  ];
  const forbidden = [
    /(^|\/)__pycache__(\/|$)/,
    /(^|\/)\.pytest_cache(\/|$)/,
    /(^|\/)\.arena(\/|$)/,
    /(^|\/)\.env($|\.)/,
    /(^|\/)build(\/|$)/,
    /(^|\/)tests?(\/|$)/,
    /(^|\/)test[_-]/,
    /\.(pyc|pyo|log)$/,
    /(^|\/)\.DS_Store$/,
  ];

  for (const file of files) {
    if (!allowed.some((pattern) => pattern.test(file))) {
      throw new Error(`Unexpected file in npm artifact: ${file}`);
    }
    if (forbidden.some((pattern) => pattern.test(file))) {
      throw new Error(`Forbidden file in npm artifact: ${file}`);
    }
  }

  for (const required of [
    'package.json',
    'dist/index.js',
    'scripts/postinstall.cjs',
    'scripts/verify-package.cjs',
    'engine/setup.py',
    'engine/requirements.txt',
    'engine/requirements.lock',
    'engine/build-requirements.lock',
    'engine/arena/__init__.py',
    'engine/arena/cli/main.py',
    'engine/MANIFEST.sha256',
  ]) {
    if (!files.includes(required)) {
      throw new Error(`Required package file is missing: ${required}`);
    }
  }

  const packageJson = await fs.readJson(path.join(stageRoot, 'package.json'));
  if (packageJson.arenaPreparedArtifact !== true || packageJson.scripts?.preinstall) {
    throw new Error('Staged package metadata failed validation');
  }

  verifyPreparedArtifact(stageRoot);

  return files.length;
}

async function main() {
  if (!(await fs.pathExists(path.join(cliRoot, 'dist', 'index.js')))) {
    throw new Error('dist/index.js is missing; run npm run build first');
  }
  await copyArtifact();
  await writeEngineManifest();
  const fileCount = await verifyArtifact();
  console.log(`Prepared ${fileCount} allowlisted files in ${stageRoot}`);
}

main().catch((error) => {
  console.error(`Package staging failed: ${error.message}`);
  process.exitCode = 1;
});
