/**
 * Transcribe command - Transcribe video audio only
 * Useful for review or as first step in workflow
 */

import path from 'path';
import chalk from 'chalk';
import { PythonBridge } from '../bridge/python-bridge.js';
import { ProgressTracker } from '../ui/progress.js';
import { ConfigManager } from '../core/config.js';
import { runPreflightChecksWithProgress } from '../core/preflight.js';
import { formatErrorWithHelp } from '../errors/formatter.js';
import { isArenaError } from '../errors/index.js';
import { displayTranscriptionSummary } from '../ui/summary.js';
import { isUrl } from '../utils/url.js';
import { commandHeader } from '../ui/output.js';
import {
  requiredProviders,
  resolveProviderSelectors,
  type ProviderSelectors,
} from '../core/providers.js';

interface TranscribeOptions extends ProviderSelectors {
  output?: string;
  cache?: boolean; // Note: commander negates --no-cache to cache: false
  cookiesFromBrowser?: string;
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

    const configManager = new ConfigManager();
    const globalConfig = await configManager.getGlobalConfig();
    const selectors = resolveProviderSelectors(options, globalConfig);
    const providerNames = requiredProviders(selectors, ['transcription']);
    await configManager.populateRequiredProviderCredentials(providerNames);

    commandHeader('Transcribe media', [
      ['Input', isUrl(videoPath) ? videoPath : path.basename(absoluteVideoPath)],
      ['Output', outputFile],
    ]);

    const preflightResult = await runPreflightChecksWithProgress({
      videoPath: absoluteVideoPath,
      outputDir: path.dirname(outputFile),
      requiredProviders: providerNames,
      enginePath: bridge.getEnginePath(),
    });

    if (!preflightResult.passed) {
      console.log(formatErrorWithHelp(preflightResult.errors[0], options.debug));
      process.exit(1);
    }

    // Show progress
    progress.start(chalk.cyan('Transcribing audio with Whisper...'));

    // Call Python bridge transcribe command
    const result = await bridge.runTranscribe(
      {
        videoPath: absoluteVideoPath,
        outputFile,
        noCache: options.cache === false,
        cookiesFromBrowser: options.cookiesFromBrowser || globalConfig?.cookies_from_browser,
        ...selectors,
      },
      (update) => {
        if (update.progress !== null) {
          progress.showDeterminate(update.progress, update.message);
        } else {
          progress.showIndeterminate(update.message);
        }
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
