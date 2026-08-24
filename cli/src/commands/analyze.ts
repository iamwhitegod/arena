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
import { commandHeader } from '../ui/output.js';
import { ConfigManager } from '../core/config.js';
import {
  requiredProviderBindings,
  requiredProviders,
  resolveProviderSelectors,
  type ProviderSelectors,
} from '../core/providers.js';

interface AnalyzeOptions extends ProviderSelectors {
  output?: string;
  numClips?: string;
  min?: string;
  max?: string;
  editorialModel?: string;
  transcript?: string;
  sceneDetection?: boolean;
  debug?: boolean;
}

export async function analyzeCommand(videoPath: string, options: AnalyzeOptions): Promise<void> {
  const startTime = Date.now();
  const progress = new ProgressTracker();
  const bridge = new PythonBridge();

  try {
    const absoluteVideoPath = path.resolve(videoPath);
    const outputFile =
      options.output ||
      path.join(
        path.dirname(absoluteVideoPath),
        `${path.basename(absoluteVideoPath, path.extname(absoluteVideoPath))}_analysis.json`
      );
    const configManager = new ConfigManager();
    const globalConfig = await configManager.getGlobalConfig();
    const selectors = resolveProviderSelectors(
      {
        ...options,
        chatModel: options.chatModel || options.editorialModel,
      },
      globalConfig
    );
    const requiredCapabilities = options.transcript
      ? (['chat', 'overviewChat', 'embedding'] as const)
      : (['chat', 'overviewChat', 'embedding', 'transcription'] as const);
    const providerNames = requiredProviders(selectors, [...requiredCapabilities]);
    const providerBindings = requiredProviderBindings(selectors, [...requiredCapabilities]);
    await configManager.populateRequiredProviderCredentials(providerNames);

    commandHeader('Analyze video', [
      ['Input', path.basename(absoluteVideoPath)],
      ['Output', outputFile],
      ['Model', selectors.chatModel || 'provider default'],
    ]);

    const preflightResult = await runPreflightChecksWithProgress({
      videoPath: absoluteVideoPath,
      outputDir: path.dirname(outputFile),
      numClips: options.numClips,
      minDuration: options.min,
      maxDuration: options.max,
      requiredProviders: providerNames,
      requiredProviderBindings: providerBindings,
      enginePath: bridge.getEnginePath(),
    });

    if (!preflightResult.passed) {
      console.log(formatErrorWithHelp(preflightResult.errors[0], options.debug));
      process.exit(1);
    }

    // Initialize progress stages
    progress.initializeStages([
      { id: 'transcription', name: 'Transcription', icon: '📝' },
      {
        id: 'analysis',
        name: 'AI Analysis',
        icon: '🧠',
      },
    ]);

    // Call Python bridge analyze command
    const result = await bridge.runAnalyze(
      {
        videoPath: absoluteVideoPath,
        outputFile,
        minDuration: options.min ? parseInt(options.min) : undefined,
        maxDuration: options.max ? parseInt(options.max) : undefined,
        clipCount: options.numClips ? parseInt(options.numClips) : undefined,
        editorialModel: options.editorialModel,
        ...selectors,
        transcriptPath: options.transcript,
        sceneDetection: options.sceneDetection || false,
      },
      (update) => {
        progress.updateStage(update.stage, update.progress, update.message);
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
