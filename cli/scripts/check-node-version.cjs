#!/usr/bin/env node

// Keep these bounds in sync with package.json and src/core/node-version.ts.
const MIN_NODE_MAJOR = 22;
const MAX_NODE_MAJOR_EXCLUSIVE = 25;
const version = process.versions.node;
const major = Number.parseInt(version.split('.')[0] ?? '', 10);

if (!Number.isInteger(major) || major < MIN_NODE_MAJOR || major >= MAX_NODE_MAJOR_EXCLUSIVE) {
  console.error(
    `Arena requires Node.js 22–24; found v${version}. ` +
      'Install a supported LTS release from https://nodejs.org/ and try again.'
  );
  process.exitCode = 1;
}
