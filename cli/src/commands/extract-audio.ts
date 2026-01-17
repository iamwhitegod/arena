/**
 * Extract Audio command - Extract audio from video
 * Useful for audio-only processing or preview
 */

import path from 'path';
import fs from 'fs-extra';
import chalk from 'chalk';
import { PythonBridge } from '../bridge/python-bridge.js';
import { ProgressTracker } from '../ui/progress.js';
import { formatErrorWithHelp } from '../errors/formatter.js';
import { isArenaError, PreflightError } from '../errors/index.js';
import { formatFileSize, formatDuration } from '../ui/formatters.js';

interface ExtractAudioOptions {
  output?: string;
  format?: 'mp3' | 'wav' | 'aac' | 'flac';
  bitrate?: string;
  sampleRate?: string;
  mono?: boolean;
  debug?: boolean;
}

export async function extractAudioCommand(
  videoPath: string,
  options: ExtractAudioOptions
): Promise<void> {
  const startTime = Date.now();
  const progress = new ProgressTracker();
  const bridge = new PythonBridge();

  try {
    const absoluteVideoPath = path.resolve(videoPath);

    // Validate video file exists
    if (!(await fs.pathExists(absoluteVideoPath))) {
      throw new PreflightError(
        'VIDEO_NOT_FOUND',
        `Video file not found: ${videoPath}`,
        'Check the file path and try again'
      );
    }

    // Determine output path
    const format = options.format || 'mp3';
    const defaultOutput = path.join(
      path.dirname(absoluteVideoPath),
      `${path.basename(absoluteVideoPath, path.extname(absoluteVideoPath))}.${format}`
    );
    const outputFile = options.output || defaultOutput;

    // Ensure output directory exists
    await fs.ensureDir(path.dirname(path.resolve(outputFile)));

    console.log(chalk.cyan('\n🎵 Extracting audio from video...\n'));

    // Show configuration
    console.log(chalk.gray('  Configuration:'));
    console.log(chalk.white(`    Format: ${format}`));
    if (options.bitrate) {
      console.log(chalk.white(`    Bitrate: ${options.bitrate}`));
    }
    if (options.sampleRate) {
      console.log(chalk.white(`    Sample Rate: ${options.sampleRate} Hz`));
    }
    if (options.mono) {
      console.log(chalk.white(`    Channels: Mono`));
    }
    console.log();

    // Show progress
    progress.start(chalk.cyan(`Extracting audio as ${format.toUpperCase()}...`));

    // Call Python bridge extract-audio command
    const result = await bridge.runExtractAudio(
      {
        videoPath: absoluteVideoPath,
        outputFile: path.resolve(outputFile),
        format,
        bitrate: options.bitrate,
        sampleRate: options.sampleRate ? parseInt(options.sampleRate) : undefined,
        mono: options.mono || false,
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

    // Get file size
    const stats = await fs.stat(path.resolve(outputFile));
    const fileSize = stats.size;

    // Display summary
    progress.stop();
    displayExtractionSummary({
      videoPath: path.basename(videoPath),
      audioPath: outputFile,
      format,
      fileSize,
      duration: result?.duration,
      processingTime,
    });
  } catch (error) {
    progress.stop();

    // Use our error formatter
    if (isArenaError(error)) {
      console.log(formatErrorWithHelp(error, options.debug));
    } else {
      console.error(chalk.red('\n✗ Audio extraction failed\n'));
      console.error(chalk.white(`  ${error instanceof Error ? error.message : String(error)}\n`));

      if (options.debug && error instanceof Error && error.stack) {
        console.error(chalk.gray('\nStack trace:'));
        console.error(chalk.gray(error.stack));
      }
    }

    process.exit(1);
  }
}

/**
 * Display extraction summary
 */
function displayExtractionSummary(data: {
  videoPath: string;
  audioPath: string;
  format: string;
  fileSize: number;
  duration?: number;
  processingTime: number;
}): void {
  const separator = chalk.gray('━'.repeat(60));

  console.log('\n' + separator);
  console.log(chalk.green('✨ Audio extracted successfully!'));
  console.log(separator);

  console.log(chalk.cyan('\n🎵 Audio File:'));

  const stats: string[] = [
    `Video: ${data.videoPath}`,
    `Format: ${data.format.toUpperCase()}`,
    `File Size: ${formatFileSize(data.fileSize)}`,
  ];

  if (data.duration) {
    stats.push(`Duration: ${formatDuration(data.duration)}`);
  }

  stats.push(`Processing Time: ${formatDuration(data.processingTime)}`);

  stats.forEach((stat) => {
    console.log(`  • ${stat}`);
  });

  console.log(chalk.cyan('\n📁 Output:'));
  console.log(chalk.white(`  ${data.audioPath}`));

  console.log(chalk.cyan('\n💡 Next step:'));
  console.log(chalk.white(`  Play audio: open "${data.audioPath}"`));

  console.log('\n' + separator + '\n');
}
