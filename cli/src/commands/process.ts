import path from 'path';
import chalk from 'chalk';
import { PythonBridge } from '../bridge/python-bridge.js';
import { ProgressTracker } from '../ui/progress.js';
import { Workspace } from '../core/workspace.js';
import { ConfigManager } from '../core/config.js';
import { runPreflightChecksWithProgress } from '../core/preflight.js';
import { formatErrorWithHelp } from '../errors/formatter.js';
import { isArenaError } from '../errors/index.js';
import { isUrl } from '../utils/url.js';

interface ProcessOptions {
  output?: string;
  numClips?: string;
  min?: string;
  max?: string;
  editorialModel?: 'gpt-4o' | 'gpt-4o-mini';
  exportLayers?: boolean;
  fast?: boolean;
  cache?: boolean; // Note: commander negates --no-cache to cache: false
  padding?: string;
  sceneDetection?: boolean;
  platform?: string;
  crop?: 'center' | 'smart' | 'top' | 'bottom';
  pad?: 'blur' | 'black' | 'white' | 'color';
  padColor?: string;
  captions?: boolean;
  captionFontSize?: string;
  captionColor?: string;
  captionPosition?: string;
  cookiesFromBrowser?: string;
  debug?: boolean;
}

export async function processCommand(videoPath: string, options: ProcessOptions): Promise<void> {
  const startTime = Date.now();
  const progress = new ProgressTracker();
  const bridge = new PythonBridge();

  try {
    const absoluteVideoPath = isUrl(videoPath) ? videoPath : path.resolve(videoPath);
    const outputDir = options.output || '.arena/output';

    // Run pre-flight checks
    console.log(chalk.cyan('\n🔍 Running pre-flight checks...\n'));

    const preflightResult = await runPreflightChecksWithProgress({
      videoPath: absoluteVideoPath,
      outputDir,
      numClips: options.numClips,
      minDuration: options.min,
      maxDuration: options.max,
      padding: options.padding,
      skipApiKeyCheck: false,
      enginePath: bridge.getEnginePath(),
    });

    if (!preflightResult.passed) {
      // Display first error with help
      console.log(formatErrorWithHelp(preflightResult.errors[0], options.debug));
      process.exit(1);
    }

    console.log(chalk.green('✓ All pre-flight checks passed\n'));

    // Initialize workspace
    const workspace = new Workspace();
    await workspace.initialize();

    // Create config and load defaults
    const configManager = new ConfigManager();
    await configManager.ensureGlobalConfig();
    const globalConfig = await configManager.getGlobalConfig();
    await configManager.createProjectConfig(absoluteVideoPath);

    // Initialize processing stages for progress tracking
    progress.initializeStages([
      { id: 'transcription', name: 'Transcription', icon: '📝' },
      {
        id: 'analysis',
        name: 'AI Analysis',
        icon: '🧠',
      },
      { id: 'hybrid', name: 'Hybrid Analysis', icon: '⚡' },
      { id: 'generation', name: 'Clip Generation', icon: '✂️' },
    ]);

    console.log(chalk.cyan('\n🎬 Processing video...\n'));
    console.log(chalk.gray('This may take several minutes depending on video length...\n'));

    const _result = await bridge.runProcess(
      {
        videoPath: absoluteVideoPath,
        outputDir: path.resolve(outputDir),
        minDuration: options.min ? parseInt(options.min) : undefined,
        maxDuration: options.max ? parseInt(options.max) : undefined,
        clipCount: options.numClips ? parseInt(options.numClips) : undefined,
        editorialModel: options.editorialModel || 'gpt-4o',
        exportLayers: options.exportLayers || false,
        fast: options.fast || false,
        noCache: options.cache === false, // --no-cache sets cache to false
        padding: options.padding ? parseFloat(options.padding) : undefined,
        sceneDetection: options.sceneDetection || false,
        platform: options.platform,
        cropStrategy: options.crop || 'center',
        padStrategy: options.pad || 'blur',
        padColor: options.padColor || '#000000',
        captions: options.captions || false,
        captionFontSize: options.captionFontSize
          ? parseInt(options.captionFontSize)
          : globalConfig?.subtitle_style?.size,
        captionColor: options.captionColor || globalConfig?.subtitle_style?.color,
        captionPosition: options.captionPosition || globalConfig?.subtitle_style?.position,
        cookiesFromBrowser: options.cookiesFromBrowser,
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

    // Check if clips were generated
    const clipsDir = path.join(path.resolve(outputDir), 'clips');
    let clipsGenerated = 0;
    try {
      const fs = await import('fs-extra');
      if (await fs.pathExists(clipsDir)) {
        const files = await fs.readdir(clipsDir);
        clipsGenerated = files.filter((f) => f.endsWith('.mp4')).length;
      }
    } catch (error) {
      // Ignore errors
    }

    // Display summary
    progress.displaySummary({
      videoPath: path.basename(videoPath),
      clipsGenerated,
      outputDir: outputDir,
      processingTime,
    });
  } catch (error) {
    // Use our error formatter for beautiful, actionable error messages
    if (isArenaError(error)) {
      console.log(formatErrorWithHelp(error, options.debug));
    } else {
      // Fallback for unexpected errors
      console.error(chalk.red('\n✗ An unexpected error occurred\n'));
      console.error(chalk.white(`  ${error instanceof Error ? error.message : String(error)}\n`));

      if (options.debug && error instanceof Error && error.stack) {
        console.error(chalk.gray('\nStack trace:'));
        console.error(chalk.gray(error.stack));
      }
    }

    process.exit(1);
  }
}
