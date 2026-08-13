/**
 * Detect-scenes command - Analyze scene changes in video
 * Useful for understanding video structure and finding visual transitions
 */

import path from 'path';
import chalk from 'chalk';
import { PythonBridge } from '../bridge/python-bridge.js';
import { ProgressTracker } from '../ui/progress.js';
import { runPreflightChecksWithProgress } from '../core/preflight.js';
import { formatErrorWithHelp } from '../errors/formatter.js';
import { isArenaError } from '../errors/index.js';
import { commandHeader, success } from '../ui/output.js';

interface DetectScenesOptions {
  output?: string;
  threshold?: string;
  minDuration?: string;
  report?: boolean;
  debug?: boolean;
}

export async function detectScenesCommand(
  videoPath: string,
  options: DetectScenesOptions
): Promise<void> {
  const startTime = Date.now();
  const progress = new ProgressTracker();
  const bridge = new PythonBridge();

  try {
    const absoluteVideoPath = path.resolve(videoPath);
    const outputFile =
      options.output ||
      path.join(
        path.dirname(absoluteVideoPath),
        `${path.basename(absoluteVideoPath, path.extname(absoluteVideoPath))}_scenes.json`
      );

    commandHeader('Detect scenes', [
      ['Input', path.basename(absoluteVideoPath)],
      ['Output', outputFile],
      ['Threshold', options.threshold || '0.4'],
    ]);

    const preflightResult = await runPreflightChecksWithProgress({
      videoPath: absoluteVideoPath,
      outputDir: path.dirname(outputFile),
      skipApiKeyCheck: true, // No API key needed for scene detection
      enginePath: bridge.getEnginePath(),
    });

    if (!preflightResult.passed) {
      console.log(formatErrorWithHelp(preflightResult.errors[0], options.debug));
      process.exit(1);
    }

    // Initialize progress stages
    progress.initializeStages([{ id: 'detection', name: 'Scene Detection', icon: '🎬' }]);

    // Call Python bridge detect-scenes command
    const result = await bridge.runDetectScenes(
      {
        videoPath: absoluteVideoPath,
        outputFile,
        threshold: options.threshold ? parseFloat(options.threshold) : undefined,
        minSceneDuration: options.minDuration ? parseFloat(options.minDuration) : undefined,
        generateReport: options.report || false,
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
    success('Scene detection complete', [
      ['Scenes', result?.sceneCount || result?.scene_count || 0],
      ['Average', `${(result?.avgSceneDuration || result?.avg_scene_duration || 0).toFixed(1)}s`],
      ['Elapsed', `${processingTime.toFixed(1)}s`],
      ['Output', outputFile],
      ['Report', result?.reportPath || result?.report_path],
    ]);
  } catch (error) {
    progress.stop();

    // Use our error formatter
    if (isArenaError(error)) {
      console.log(formatErrorWithHelp(error, options.debug));
    } else {
      console.error(chalk.red('\n✗ Scene detection failed\n'));
      console.error(chalk.white(`  ${error instanceof Error ? error.message : String(error)}\n`));

      if (options.debug && error instanceof Error && error.stack) {
        console.error(chalk.gray('\nStack trace:'));
        console.error(chalk.gray(error.stack));
      }
    }

    process.exit(1);
  }
}
