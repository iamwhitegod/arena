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
import { requiredProviders, type ProviderSelectors } from '../core/providers.js';

interface AnalyzeOptions extends ProviderSelectors {
  output?: string;
  numClips?: string;
  min?: string;
  max?: string;
  editorialModel?: 'gpt-4o' | 'gpt-4o-mini';
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
    const globalConfig = await new ConfigManager().getGlobalConfig();
    const selectors: ProviderSelectors = {
      provider: options.provider || globalConfig.provider,
      chatProvider: options.chatProvider || globalConfig.chat_provider,
      chatModel: options.chatModel || options.editorialModel || globalConfig.chat_model || 'gpt-4o',
      overviewChatProvider: options.overviewChatProvider || globalConfig.overview_chat_provider,
      overviewChatModel: options.overviewChatModel || globalConfig.overview_chat_model,
      embeddingProvider: options.embeddingProvider || globalConfig.embedding_provider,
      embeddingModel: options.embeddingModel || globalConfig.embedding_model,
      transcriptionProvider: options.transcriptionProvider || globalConfig.transcription_provider,
      transcriptionModel: options.transcriptionModel || globalConfig.transcription_model,
    };

    commandHeader('Analyze video', [
      ['Input', path.basename(absoluteVideoPath)],
      ['Output', outputFile],
      ['Model', selectors.chatModel || 'gpt-4o'],
    ]);

    const preflightResult = await runPreflightChecksWithProgress({
      videoPath: absoluteVideoPath,
      outputDir: path.dirname(outputFile),
      numClips: options.numClips,
      minDuration: options.min,
      maxDuration: options.max,
      requiredProviders: requiredProviders(
        selectors,
        options.transcript
          ? ['chat', 'overviewChat', 'embedding']
          : ['chat', 'overviewChat', 'embedding', 'transcription']
      ),
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
