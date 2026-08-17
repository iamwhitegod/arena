#!/usr/bin/env node

/** Verify the staged npm artifact immediately before pack or publish. */

const crypto = require('crypto');
const fs = require('fs');
const path = require('path');

function normalized(relativePath) {
  return relativePath.split(path.sep).join('/');
}

function listFiles(root, current = root) {
  const files = [];
  for (const entry of fs.readdirSync(current, { withFileTypes: true })) {
    const absolutePath = path.join(current, entry.name);
    const relativePath = normalized(path.relative(root, absolutePath));
    if (entry.isSymbolicLink()) {
      throw new Error(`Symlinks are not allowed in the npm artifact: ${relativePath}`);
    }
    if (entry.isDirectory()) {
      files.push(...listFiles(root, absolutePath));
    } else if (entry.isFile()) {
      files.push(relativePath);
    }
  }
  return files.sort();
}

function verifyEngineManifest(root) {
  const engineRoot = path.join(root, 'engine');
  const manifestPath = path.join(engineRoot, 'MANIFEST.sha256');
  const lines = fs.readFileSync(manifestPath, 'utf8').split('\n').filter(Boolean);
  for (const line of lines) {
    const match = line.match(/^([a-f0-9]{64}) {2}(.+)$/);
    if (!match) {
      throw new Error('Malformed engine/MANIFEST.sha256');
    }
    const [, expectedHash, relativePath] = match;
    const absolutePath = path.resolve(engineRoot, relativePath);
    if (!absolutePath.startsWith(`${path.resolve(engineRoot)}${path.sep}`)) {
      throw new Error(`Unsafe engine manifest path: ${relativePath}`);
    }
    const content = fs.readFileSync(absolutePath);
    const actualHash = crypto.createHash('sha256').update(content).digest('hex');
    if (actualHash !== expectedHash) {
      throw new Error(`Engine checksum failed: ${relativePath}`);
    }
  }
  return lines.length;
}

function verifyArtifact(root = path.resolve(__dirname, '..')) {
  const files = listFiles(root);
  const allowed = [
    /^(package\.json|README\.md|LICENSE)$/,
    /^dist\//,
    /^scripts\/(postinstall|verify-package)\.cjs$/,
    /^engine\/(setup\.py|requirements\.txt|requirements\.lock|requirements-local\.txt|requirements-local\.lock|build-requirements\.txt|build-requirements\.lock|arena-cli|MANIFEST\.sha256)$/,
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
    'dist/launcher.js',
    'dist/index.js',
    'scripts/postinstall.cjs',
    'scripts/verify-package.cjs',
    'engine/setup.py',
    'engine/requirements.txt',
    'engine/requirements.lock',
    'engine/requirements-local.txt',
    'engine/requirements-local.lock',
    'engine/build-requirements.lock',
    'engine/arena/__init__.py',
    'engine/arena/cli/main.py',
    'engine/MANIFEST.sha256',
  ]) {
    if (!files.includes(required)) {
      throw new Error(`Required package file is missing: ${required}`);
    }
  }

  const packageJson = JSON.parse(fs.readFileSync(path.join(root, 'package.json'), 'utf8'));
  if (packageJson.arenaPreparedArtifact !== true || packageJson.scripts?.preinstall) {
    throw new Error('Staged package metadata failed validation');
  }

  verifyEngineManifest(root);
  return files.length;
}

if (require.main === module) {
  try {
    if (process.argv.includes('--engine-only')) {
      const fileCount = verifyEngineManifest(path.resolve(__dirname, '..'));
      console.log(`Verified ${fileCount} engine manifest entries`);
    } else {
      const fileCount = verifyArtifact();
      console.log(`Verified ${fileCount} allowlisted package files`);
    }
  } catch (error) {
    console.error(`Package verification failed: ${error.message}`);
    process.exitCode = 1;
  }
}

module.exports = { verifyArtifact, verifyEngineManifest };
