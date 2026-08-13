#!/usr/bin/env node

/** Pack the already-staged npm package and write reproducible test metadata. */

const crypto = require('node:crypto');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { spawnSync } = require('node:child_process');
const { verifyArtifact } = require('./verify-package.cjs');

function parseOutputDirectory(argv) {
  const outputIndex = argv.indexOf('--output');
  if (outputIndex === -1 || !argv[outputIndex + 1]) {
    throw new Error('Usage: node scripts/pack-install-artifact.cjs --output <directory>');
  }
  return path.resolve(argv[outputIndex + 1]);
}

function main() {
  const cliRoot = path.resolve(__dirname, '..');
  const stageRoot = path.join(cliRoot, '.package');
  const outputDirectory = parseOutputDirectory(process.argv.slice(2));
  fs.mkdirSync(outputDirectory, { recursive: true });

  const existingTarballs = fs.readdirSync(outputDirectory).filter((name) => name.endsWith('.tgz'));
  if (existingTarballs.length > 0) {
    throw new Error(`Output directory already contains npm tarballs: ${outputDirectory}`);
  }

  const verifiedFileCount = verifyArtifact(stageRoot);
  const npmCommand = process.platform === 'win32' ? 'npm.cmd' : 'npm';
  const packCache = fs.mkdtempSync(path.join(os.tmpdir(), 'arena npm pack cache '));
  let result;
  try {
    result = spawnSync(
      npmCommand,
      ['pack', stageRoot, '--json', '--ignore-scripts', '--pack-destination', outputDirectory],
      {
        cwd: cliRoot,
        encoding: 'utf8',
        env: { ...process.env, NPM_CONFIG_CACHE: packCache },
        shell: process.platform === 'win32',
        windowsHide: true,
        stdio: ['ignore', 'pipe', 'pipe'],
      }
    );
  } finally {
    fs.rmSync(packCache, { force: true, recursive: true });
  }
  if (result.error) {
    throw result.error;
  }
  if (result.status !== 0) {
    throw new Error(`npm pack failed: ${result.stderr || result.stdout}`);
  }

  const packResult = JSON.parse(result.stdout);
  if (!Array.isArray(packResult) || packResult.length !== 1 || !packResult[0].filename) {
    throw new Error('npm pack did not return exactly one artifact');
  }

  const packed = packResult[0];
  const tarballPath = path.join(outputDirectory, packed.filename);
  const digest = crypto.createHash('sha256').update(fs.readFileSync(tarballPath)).digest('hex');
  const metadata = {
    schemaVersion: 1,
    packageName: packed.name,
    packageVersion: packed.version,
    tarball: packed.filename,
    sha256: digest,
    size: packed.size,
    unpackedSize: packed.unpackedSize,
    verifiedFileCount,
    files: packed.files.map((file) => ({ path: file.path, size: file.size })),
  };
  fs.writeFileSync(
    path.join(outputDirectory, 'artifact-metadata.json'),
    `${JSON.stringify(metadata, null, 2)}\n`,
    { mode: 0o644 }
  );
  console.log(`Packed ${packed.name}@${packed.version}: ${packed.filename}`);
  console.log(`SHA-256: ${digest}`);
}

try {
  main();
} catch (error) {
  console.error(`Installation artifact packing failed: ${error.message}`);
  process.exitCode = 1;
}
