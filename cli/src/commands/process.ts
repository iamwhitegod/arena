import fs from 'fs-extra';
import path from 'path';
import chalk from 'chalk';
import { PythonBridge } from '../bridge/python-bridge.js';
import { ProgressTracker } from '../ui/progress.js';
import { Workspace } from '../core/workspace.js';
import { ConfigManager } from '../core/config.js';

interface ProcessOptions {
  output?: string;
  clips?: string;
  minDuration?: string;
  maxDuration?: string;
}

export async function processCommand(
  videoPath: string,
  options: ProcessOptions
): Promise<void> {
  const startTime = Date.now();
  const progress = new ProgressTracker();

  try {
    // Validate video file exists
    progress.start('Validating video file...');
    const absoluteVideoPath = path.resolve(videoPath);

    if (!(await fs.pathExists(absoluteVideoPath))) {
      progress.fail(`Video file not found: ${videoPath}`);
      process.exit(1);
    }

    progress.succeed(`Video file found: ${chalk.cyan(path.basename(videoPath))}`);

    // Check Python environment
    progress.start('Checking Python environment...');
    const bridge = new PythonBridge();
    const pythonCheck = await bridge.checkPythonEnvironment();

    if (!pythonCheck.available) {
      progress.fail(pythonCheck.error || 'Python 3 is required');
      console.log(
        chalk.yellow(
          '\nPlease install Python 3.9+ and ensure it\'s in your PATH.'
        )
      );
      process.exit(1);
    }

    progress.succeed(`Python environment ready: ${chalk.gray(pythonCheck.version)}`);

    // Check dependencies
    progress.start('Checking Python dependencies...');
    const depsCheck = await bridge.checkDependencies();

    if (!depsCheck.installed) {
      progress.warn('Python dependencies not installed');
      console.log(
        chalk.yellow(
          '\nTo install dependencies, run:\n' +
            chalk.cyan('  cd engine && pip install -r requirements.txt\n')
        )
      );
      process.exit(1);
    }

    progress.succeed('Python dependencies installed');

    // Initialize workspace
    progress.start('Initializing workspace...');
    const outputDir = options.output || '.arena/output';
    const workspace = new Workspace();
    await workspace.initialize();

    // Create config
    const configManager = new ConfigManager();
    await configManager.ensureGlobalConfig();
    await configManager.createProjectConfig(absoluteVideoPath);

    progress.succeed('Workspace initialized');

    // Process video
    progress.start('Starting video processing...');
    console.log(chalk.gray('\nThis may take several minutes depending on video length...\n'));

    const result = await bridge.runProcess(
      {
        videoPath: absoluteVideoPath,
        outputDir: path.resolve(outputDir),
        minDuration: options.minDuration ? parseInt(options.minDuration) : undefined,
        maxDuration: options.maxDuration ? parseInt(options.maxDuration) : undefined,
        clipCount: options.clips ? parseInt(options.clips) : undefined,
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
    progress.displaySummary({
      videoPath: path.basename(videoPath),
      clipsGenerated: result?.clips?.length || 0,
      outputDir: outputDir,
      processingTime,
    });
  } catch (error) {
    progress.fail('Processing failed');
    console.error(
      chalk.red('\nError: ') +
        (error instanceof Error ? error.message : String(error))
    );
    process.exit(1);
  }
}
