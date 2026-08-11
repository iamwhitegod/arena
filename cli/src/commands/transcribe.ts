/**
 * Transcribe command - Transcribe video audio only
 * Useful for review or as first step in workflow
 */

import path from 'path';
import chalk from 'chalk';
import { PythonBridge } from '../bridge/python-bridge.js';
import { ProgressTracker } from '../ui/progress.js';
import { runPreflightChecksWithProgress } from '../core/preflight.js';
import { formatErrorWithHelp } from '../errors/formatter.js';
import { isArenaError } from '../errors/index.js';
import { displayTranscriptionSummary } from '../ui/summary.js';
import { isUrl } from '../utils/url.js';

interface TranscribeOptions {
  output?: string;
  cache?: boolean; // Note: commander negates --no-cache to cache: false
  debug?: boolean;
}

export async function transcribeCommand(
  videoPath: string,
  options: TranscribeOptions
): Promise<void> {
  const startTime = Date.now();
  const progress = new ProgressTracker();
  const bridge = new PythonBridge();

  try {
    const absoluteVideoPath = isUrl(videoPath) ? videoPath : path.resolve(videoPath);
    let outputFile: string;
    if (options.output) {
      outputFile = options.output;
    } else if (isUrl(videoPath)) {
      const slug = videoPath.split('/').pop()?.split('?')[0] || 'download';
      outputFile = path.join(process.cwd(), `${slug}_transcript.json`);
    } else {
      outputFile = path.join(
        path.dirname(absoluteVideoPath),
        `${path.basename(absoluteVideoPath, path.extname(absoluteVideoPath))}_transcript.json`
      );
    }

    // Run pre-flight checks
    console.log(chalk.cyan('\n🔍 Running pre-flight checks...\n'));

    const preflightResult = await runPreflightChecksWithProgress({
      videoPath: absoluteVideoPath,
      outputDir: path.dirname(outputFile),
      skipApiKeyCheck: false,
      enginePath: bridge.getEnginePath(),
    });

    if (!preflightResult.passed) {
      console.log(formatErrorWithHelp(preflightResult.errors[0], options.debug));
      process.exit(1);
    }

    console.log(chalk.green('✓ All pre-flight checks passed\n'));

    // Show progress
    progress.start(chalk.cyan('Transcribing audio with Whisper...'));

    console.log(chalk.gray('\nThis may take a few minutes depending on video length...\n'));

    // Call Python bridge transcribe command
    const result = await bridge.runTranscribe(
      {
        videoPath: absoluteVideoPath,
        outputFile,
        noCache: options.cache === false,
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
    displayTranscriptionSummary({
      videoPath: path.basename(videoPath),
      duration: result?.duration || 0,
      wordCount: result?.wordCount || 0,
      outputFile,
      processingTime,
      cost: result?.cost,
    });
  } catch (error) {
    progress.stop();

    // Use our error formatter
    if (isArenaError(error)) {
      console.log(formatErrorWithHelp(error, options.debug));
    } else {
      console.error(chalk.red('\n✗ Transcription failed\n'));
      console.error(chalk.white(`  ${error instanceof Error ? error.message : String(error)}\n`));

      if (options.debug && error instanceof Error && error.stack) {
        console.error(chalk.gray('\nStack trace:'));
        console.error(chalk.gray(error.stack));
      }
    }

    process.exit(1);
  }
}
