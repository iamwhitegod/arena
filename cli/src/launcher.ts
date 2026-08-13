#!/usr/bin/env node

import { unsupportedNodeVersionMessage } from './core/node-version.js';

// Keep the executable entry point dependency-free until the runtime is known
// to be supported. This avoids loading the full CLI graph on an old Node.js.
const nodeVersionError = unsupportedNodeVersionMessage();
if (nodeVersionError) {
  console.error(nodeVersionError);
  process.exitCode = 1;
} else {
  await import('./index.js');
}
