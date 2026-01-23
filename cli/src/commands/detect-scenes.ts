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

    // Run pre-flight checks (minimal - just video validation)
    console.log(chalk.cyan('\n🔍 Running pre-flight checks...\n'));

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

    console.log(chalk.green('✓ All pre-flight checks passed\n'));

    // Initialize progress stages
    progress.initializeStages([{ id: 'detection', name: 'Scene Detection', icon: '🎬' }]);

    console.log(chalk.cyan('\n🎬 Detecting scene changes...\n'));
    console.log(chalk.gray('This analyzes visual transitions in your video.\n'));

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
    console.log(chalk.green('\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━'));
    console.log(chalk.green('✨ Scene detection complete!\n'));

    console.log(chalk.cyan('📊 Summary:'));
    console.log(chalk.white(`  • Video: ${chalk.bold(path.basename(videoPath))}`));
    console.log(chalk.white(`  • Scenes detected: ${chalk.bold(result?.sceneCount || 0)}`));
    console.log(
      chalk.white(
        `  • Average scene duration: ${chalk.bold((result?.avgSceneDuration || 0).toFixed(1))}s`
      )
    );
    console.log(chalk.white(`  • Detection threshold: ${chalk.bold(options.threshold || '0.4')}`));
    console.log(chalk.white(`  • Processing time: ${chalk.bold(processingTime.toFixed(1))}s`));

    console.log(chalk.cyan('\n📁 Output:'));
    console.log(chalk.white(`  ${outputFile}`));

    if (options.report && result?.reportPath) {
      console.log(chalk.white(`  ${result.reportPath} (detailed report)`));
    }

    console.log(chalk.cyan('\n💡 Next steps:'));
    console.log(chalk.white('  • Review scene boundaries in the JSON output'));
    console.log(chalk.white('  • Use --scene-detection when processing to align clips to scenes'));
    console.log(chalk.white('  • Example: arena process video.mp4 --scene-detection'));

    console.log(chalk.green('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n'));
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
