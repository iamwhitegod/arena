/**
 * Format clips for specific social media platforms
 */

import chalk from 'chalk';
import path from 'path';
import { PythonBridge } from '../bridge/python-bridge.js';
import { displayErrorSummary } from '../ui/summary.js';
import type { ProgressUpdate } from '../bridge/python-bridge.js';

interface FormatOptions {
  output?: string;
  platform: string;
  crop?: 'center' | 'smart' | 'top' | 'bottom';
  pad?: 'blur' | 'black' | 'white' | 'color';
  padColor?: string;
  quality?: boolean;
}

export async function formatCommand(
  input: string,
  options: FormatOptions
): Promise<void> {
  try {
    console.log(chalk.cyan('\n📐 PLATFORM FORMATTING\n'));

    // Validate input
    const absoluteInputPath = path.resolve(input);

    // Default output
    const outputDir = options.output
      ? path.resolve(options.output)
      : path.join(process.cwd(), 'output', 'formatted');

    // Show configuration
    console.log(chalk.white('Configuration:'));
    console.log(chalk.gray(`  Input: ${absoluteInputPath}`));
    console.log(chalk.gray(`  Platform: ${options.platform}`));
    console.log(chalk.gray(`  Output: ${outputDir}`));
    console.log(chalk.gray(`  Crop Strategy: ${options.crop || 'center'}`));
    console.log(chalk.gray(`  Pad Strategy: ${options.pad || 'blur'}\n`));

    // Initialize bridge
    const bridge = new PythonBridge();

    // Progress tracking
    const onProgress = (update: ProgressUpdate) => {
      if (update.stage) {
        console.log(chalk.cyan(`  ${update.stage}`));
      }
      if (update.message) {
        console.log(chalk.white(`    ${update.message}`));
      }
    };

    const onError = (error: string) => {
      console.error(chalk.red(`  ⚠️  ${error}`));
    };

    // Run formatting
    const result = await bridge.runFormat(
      {
        inputPath: absoluteInputPath,
        outputDir,
        platform: options.platform,
        cropStrategy: options.crop || 'center',
        padStrategy: options.pad || 'blur',
        padColor: options.padColor,
        maintainQuality: options.quality !== false,
      },
      onProgress,
      onError
    );

    // Display results
    if (result.success) {
      console.log(chalk.green('\n✓ Formatting complete!\n'));
      console.log(chalk.white('Results:'));
      console.log(chalk.gray(`  Formatted clips: ${result.clipCount || 0}`));
      console.log(chalk.gray(`  Output directory: ${result.outputDir}\n`));

      if (result.warnings && result.warnings.length > 0) {
        console.log(chalk.yellow('⚠️  Warnings:'));
        result.warnings.forEach((warning: string) => {
          console.log(chalk.yellow(`  • ${warning}`));
        });
        console.log();
      }
    } else {
      throw new Error(result.error || 'Formatting failed');
    }
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    displayErrorSummary('Formatting failed: ' + message, [
      'Check that the input file exists',
      'Verify the platform name is correct',
      'Try using a different crop or pad strategy',
    ]);
    process.exit(1);
  }
}
