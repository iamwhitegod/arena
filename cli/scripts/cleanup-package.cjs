#!/usr/bin/env node

/**
 * Cleanup after npm pack/publish
 * Removes copied engine directory and requirements.txt
 */

const fs = require('fs-extra');
const path = require('path');

async function main() {
  const cliRoot = path.join(__dirname, '..');
  const enginePath = path.join(cliRoot, 'engine');
  const requirementsPath = path.join(cliRoot, 'requirements.txt');

  console.log('🧹 Cleaning up package files...');

  try {
    // Remove engine directory
    if (fs.existsSync(enginePath)) {
      console.log('  Removing engine/ directory...');
      await fs.remove(enginePath);
      console.log('  ✓ engine/ removed');
    }

    // Remove requirements.txt
    if (fs.existsSync(requirementsPath)) {
      console.log('  Removing requirements.txt...');
      await fs.remove(requirementsPath);
      console.log('  ✓ requirements.txt removed');
    }

    console.log('✓ Cleanup complete\n');
  } catch (error) {
    console.error('✗ Cleanup failed:', error.message);
    // Don't fail the build
    process.exit(0);
  }
}

main();
