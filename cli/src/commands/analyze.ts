/**
 * Analyze command - Analyze video without generating clips
 * Fast preview of what clips would be generated
 */

import path from 'path';
import chalk from 'chalk';
import { PythonBridge } from '../bridge/python-bridge.js';
import { ProgressTracker } from '../ui/progress.js';
import { runPreflightChecksWithProgress } from '../core/preflight.js';
import { formatErrorWithHelp } from '../errors/formatter.js';
import { isArenaError } from '../errors/index.js';
import { displayAnalysisSummary } from '../ui/summary.js';

interface AnalyzeOptions {
  output?: string;
  numClips?: string;
  min?: string;
  max?: string;
  use4layer?: boolean;
  editorialModel?: 'gpt-4o' | 'gpt-4o-mini';
  transcript?: string;
  debug?: boolean;
}

export async function analyzeCommand(
  videoPath: string,
  options: AnalyzeOptions
): Promise<void> {
  const startTime = Date.now();
  const progress = new ProgressTracker();
  const bridge = new PythonBridge();

  try {
    const absoluteVideoPath = path.resolve(videoPath);
    const outputFile = options.output || path.join(
      path.dirname(absoluteVideoPath),
      `${path.basename(absoluteVideoPath, path.extname(absoluteVideoPath))}_analysis.json`
    );

    // Run pre-flight checks
    console.log(chalk.cyan('\n🔍 Running pre-flight checks...\n'));

    const preflightResult = await runPreflightChecksWithProgress({
      videoPath: absoluteVideoPath,
      outputDir: path.dirname(outputFile),
      numClips: options.numClips,
      minDuration: options.min,
      maxDuration: options.max,
      skipApiKeyCheck: false,
      enginePath: bridge.getEnginePath(),
    });

    if (!preflightResult.passed) {
      console.log(formatErrorWithHelp(preflightResult.errors[0], options.debug));
      process.exit(1);
    }

    console.log(chalk.green('✓ All pre-flight checks passed\n'));

    // Initialize progress stages
    progress.initializeStages([
      { id: 'transcription', name: 'Transcription', icon: '📝' },
      { id: 'analysis', name: options.use4layer ? 'AI Analysis - 4-Layer System' : 'AI Analysis', icon: '🧠' },
    ]);

    console.log(chalk.cyan('\n🔎 Analyzing video...\n'));
    console.log(chalk.gray('This will analyze the video without generating clips.\n'));

    // Call Python bridge analyze command
    const result = await bridge.runAnalyze(
      {
        videoPath: absoluteVideoPath,
        outputFile,
        minDuration: options.min ? parseInt(options.min) : undefined,
        maxDuration: options.max ? parseInt(options.max) : undefined,
        clipCount: options.numClips ? parseInt(options.numClips) : undefined,
        use4Layer: options.use4layer || false,
        editorialModel: options.editorialModel || 'gpt-4o',
        transcriptPath: options.transcript,
      },
      (update) => {
        progress.updateStage(update.stage, update.progress, update.message);
      },
      (error) => {
        console.error(chalk.red(error));
      }
    );

    // Calculate processing time
    const processingTime = (Date.now() - startTime) / 1000;

    // Display summary
    progress.stop();
    displayAnalysisSummary({
      videoPath: path.basename(videoPath),
      videoDuration: result?.videoDuration || 0,
      transcriptWordCount: result?.wordCount,
      momentsFound: result?.momentsFound || 0,
      estimatedClips: result?.estimatedClips || 0,
      processingTime,
      outputFile,
    });
  } catch (error) {
    progress.stop();

    // Use our error formatter
    if (isArenaError(error)) {
      console.log(formatErrorWithHelp(error, options.debug));
    } else {
      console.error(chalk.red('\n✗ Analysis failed\n'));
      console.error(chalk.white(`  ${error instanceof Error ? error.message : String(error)}\n`));

      if (options.debug && error instanceof Error && error.stack) {
        console.error(chalk.gray('\nStack trace:'));
        console.error(chalk.gray(error.stack));
      }
    }

    process.exit(1);
  }
}
