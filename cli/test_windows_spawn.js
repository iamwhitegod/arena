#!/usr/bin/env node

/**
 * Test script to verify Windows spawn options are applied correctly
 */

import { spawn } from 'child_process';

console.log('Platform:', process.platform);
console.log('Node version:', process.version);
console.log('');

// Test spawn with Windows options
const spawnOptions = {
  stdio: 'ignore',
};

if (process.platform === 'win32') {
  console.log('Windows detected - adding spawn options:');
  spawnOptions.windowsHide = true;
  spawnOptions.detached = false;
  spawnOptions.shell = false;
  console.log('  windowsHide:', spawnOptions.windowsHide);
  console.log('  detached:', spawnOptions.detached);
  console.log('  shell:', spawnOptions.shell);
} else {
  console.log('Non-Windows platform - no special options needed');
}

console.log('');
console.log('Testing spawn with python --version...');

const pythonCmd = process.platform === 'win32' ? 'python' : 'python3';

const proc = spawn(pythonCmd, ['--version'], spawnOptions);

proc.on('close', (code) => {
  console.log('Process exited with code:', code);
  if (code === 0) {
    console.log('✓ SUCCESS - spawn worked without errors');
  } else {
    console.log('✗ FAILED - spawn exited with non-zero code');
  }
  process.exit(code);
});

proc.on('error', (error) => {
  console.error('✗ ERROR during spawn:');
  console.error(error.message);
  console.error('');
  console.error('Full error:');
  console.error(error);
  process.exit(1);
});
