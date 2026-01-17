/**
 * Generate command - Generate clips from existing analysis
 * Allows selective clip generation without re-analyzing
 */

import path from 'path';
import fs from 'fs-extra';
import chalk from 'chalk';
import { PythonBridge } from '../bridge/python-bridge.js';
import { ProgressTracker } from '../ui/progress.js';
import { formatErrorWithHelp } from '../errors/formatter.js';
import { isArenaError, PreflightError } from '../errors/index.js';
import { displayProcessingSummary } from '../ui/summary.js';

interface GenerateOptions {
  output?: string;
  numClips?: string;
  select?: string; // Comma-separated clip indices (e.g., "1,3,5")
  fast?: boolean;
  padding?: string;
  debug?: boolean;
}

export async function generateCommand(
  videoPath: string,
  analysisPath: string,
  options: GenerateOptions
): Promise<void> {
  const startTime = Date.now();
  const progress = new ProgressTracker();
  const bridge = new PythonBridge();

  try {
    const absoluteVideoPath = path.resolve(videoPath);
    const absoluteAnalysisPath = path.resolve(analysisPath);
    const outputDir = options.output || './clips';

    // Validate video file exists
    if (!(await fs.pathExists(absoluteVideoPath))) {
      throw new PreflightError(
        'VIDEO_NOT_FOUND',
        `Video file not found: ${videoPath}`,
        'Check the file path and try again'
      );
    }

    // Validate analysis file exists
    if (!(await fs.pathExists(absoluteAnalysisPath))) {
      throw new PreflightError(
        'ANALYSIS_NOT_FOUND',
        `Analysis file not found: ${analysisPath}`,
        'Run analysis first: arena analyze video.mp4'
      );
    }

    // Ensure output directory
    await fs.ensureDir(path.resolve(outputDir));

    // Parse selection if provided
    let selectedIndices: number[] | undefined;
    if (options.select) {
      selectedIndices = options.select.split(',').map((s) => parseInt(s.trim())).filter((n) => !isNaN(n));

      if (selectedIndices.length === 0) {
        throw new PreflightError(
          'INVALID_OPTION',
          'Invalid clip selection',
          'Use comma-separated numbers: --select 1,3,5'
        );
      }

      console.log(chalk.cyan(`\n✂️  Generating ${selectedIndices.length} selected clip${selectedIndices.length !== 1 ? 's' : ''}...\n`));
    } else {
      console.log(chalk.cyan('\n✂️  Generating clips from analysis...\n'));
    }

    // Show progress
    progress.start(chalk.cyan('Generating video clips...'));

    console.log(chalk.gray('This may take a few minutes depending on clip count...\n'));

    // Call Python bridge generate command
    const result = await bridge.runGenerate(
      {
        videoPath: absoluteVideoPath,
        analysisPath: absoluteAnalysisPath,
        outputDir: path.resolve(outputDir),
        clipCount: options.numClips ? parseInt(options.numClips) : undefined,
        selectedIndices,
        fast: options.fast || false,
        padding: options.padding ? parseFloat(options.padding) : undefined,
      },
      (update) => {
        if (update.progress !== undefined) {
          progress.showDeterminate(update.progress, update.message);
        } else {
          progress.showIndeterminate(update.message);
        }
      },
      (error) => {
        console.error(chalk.red(error));
      }
    );

    // Calculate processing time
    const processingTime = (Date.now() - startTime) / 1000;

    // Display summary
    progress.stop();
    displayProcessingSummary({
      videoPath: path.basename(videoPath),
      clipsGenerated: result?.clips?.length || 0,
      clips: result?.clips,
      outputDir,
      processingTime,
    });
  } catch (error) {
    progress.stop();

    // Use our error formatter
    if (isArenaError(error)) {
      console.log(formatErrorWithHelp(error, options.debug));
    } else {
      console.error(chalk.red('\n✗ Generation failed\n'));
      console.error(chalk.white(`  ${error instanceof Error ? error.message : String(error)}\n`));

      if (options.debug && error instanceof Error && error.stack) {
        console.error(chalk.gray('\nStack trace:'));
        console.error(chalk.gray(error.stack));
      }
    }

    process.exit(1);
  }
}
