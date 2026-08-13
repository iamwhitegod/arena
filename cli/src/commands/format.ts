/**
 * Format clips for specific social media platforms
 */

import chalk from 'chalk';
import path from 'path';
import { PythonBridge } from '../bridge/python-bridge.js';
import { displayErrorSummary } from '../ui/summary.js';
import type { ProgressUpdate } from '../bridge/python-bridge.js';
import { ProgressTracker } from '../ui/progress.js';
import { commandHeader, success, warning as displayWarning } from '../ui/output.js';

interface FormatOptions {
  output?: string;
  platform: string;
  crop?: 'center' | 'smart' | 'top' | 'bottom';
  pad?: 'blur' | 'black' | 'white' | 'color';
  padColor?: string;
  quality?: boolean;
  captions?: string;
  captionFontSize?: string;
  captionColor?: string;
  captionPosition?: string;
}

export async function formatCommand(input: string, options: FormatOptions): Promise<void> {
  try {
    // Validate input
    const absoluteInputPath = path.resolve(input);

    // Default output
    const outputDir = options.output
      ? path.resolve(options.output)
      : path.join(process.cwd(), 'output', 'formatted');

    commandHeader('Format media', [
      ['Input', absoluteInputPath],
      ['Platform', options.platform],
      ['Layout', `${options.crop || 'center'} crop · ${options.pad || 'blur'} padding`],
      ['Output', outputDir],
    ]);

    // Initialize bridge
    const bridge = new PythonBridge();

    // Progress tracking
    const progress = new ProgressTracker();
    progress.start('Formatting media...');
    const onProgress = (update: ProgressUpdate) =>
      progress.showDeterminate(update.progress, update.message);

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
        captions: options.captions,
        captionFontSize: options.captionFontSize ? parseInt(options.captionFontSize) : undefined,
        captionColor: options.captionColor,
        captionPosition: options.captionPosition,
      },
      onProgress,
      onError
    );

    // Display results
    if (result.success) {
      progress.stop();
      success(
        `Formatting complete — ${result.clipCount || 0} clip${result.clipCount === 1 ? '' : 's'}`,
        [['Output', result.outputDir]]
      );

      if (result.warnings && result.warnings.length > 0) {
        result.warnings.forEach((message: string) => {
          displayWarning(message);
        });
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
