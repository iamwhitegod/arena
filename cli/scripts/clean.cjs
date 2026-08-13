#!/usr/bin/env node

const { rmSync } = require('node:fs');
const { resolve } = require('node:path');

// Resolve from this file so the command is safe regardless of the caller's cwd.
const distDir = resolve(__dirname, '..', 'dist');
rmSync(distDir, { force: true, recursive: true });
