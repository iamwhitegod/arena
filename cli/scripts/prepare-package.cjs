#!/usr/bin/env node

/**
 * Prepare package for npm publishing
 * Copies engine directory and requirements.txt from parent directory
 */

const fs = require('fs-extra');
const path = require('path');

async function main() {
  const cliRoot = path.join(__dirname, '..');
  const projectRoot = path.join(cliRoot, '..');

  const engineSource = path.join(projectRoot, 'engine');
  const engineDest = path.join(cliRoot, 'engine');

  const requirementsSource = path.join(projectRoot, 'engine', 'requirements.txt');
  const requirementsDest = path.join(cliRoot, 'requirements.txt');

  console.log('📦 Preparing package for publishing...');

  try {
    // Copy engine directory
    if (fs.existsSync(engineSource)) {
      console.log('  Copying engine/ directory...');
      await fs.copy(engineSource, engineDest, {
        filter: (src) => {
          // Exclude Python cache and build artifacts
          return !src.includes('__pycache__') &&
                 !src.includes('.pyc') &&
                 !src.includes('.egg-info') &&
                 !src.includes('dist/') &&
                 !src.includes('build/');
        }
      });
      console.log('  ✓ engine/ copied');
    } else {
      console.warn('  ⚠ engine/ not found, skipping');
    }

    // Copy requirements.txt
    if (fs.existsSync(requirementsSource)) {
      console.log('  Copying requirements.txt...');
      await fs.copy(requirementsSource, requirementsDest);
      console.log('  ✓ requirements.txt copied');
    } else {
      console.warn('  ⚠ requirements.txt not found, skipping');
    }

    console.log('✓ Package prepared successfully\n');
  } catch (error) {
    console.error('✗ Failed to prepare package:', error.message);
    process.exit(1);
  }
}

main();
