#!/usr/bin/env node

const fs = require('node:fs');
const path = require('node:path');

if (process.platform !== 'win32') {
  for (const filename of ['index.js', 'launcher.js']) {
    fs.chmodSync(path.resolve(__dirname, '..', 'dist', filename), 0o755);
  }
}
