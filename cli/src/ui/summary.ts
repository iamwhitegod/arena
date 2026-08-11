/**
 * Summary display for Arena CLI
 * Shows beautiful summaries after processing completes
 */

import chalk from 'chalk';
import path from 'path';
import {
  formatDuration,
  formatCost,
  formatPercentage,
  formatDurationCompact,
  formatTerminalLink,
  formatBox,
} from './formatters.js';

export interface ClipSummary {
  title: string;
  duration: number;
  startTime: number;
  endTime: number;
  interestScore?: number;
  contentType?: string;
}

export interface ProcessingSummary {
  videoPath: string;
  videoDuration?: number;
  clipsGenerated: number;
  clips?: ClipSummary[];
  outputDir: string;
  processingTime: number;
  totalCost?: number;
  passRate?: number;
  editorialModel?: string;
  layerStats?: {
    layer1Moments?: number;
    layer2Boundaries?: number;
    layer3Validated?: number;
    layer4Packaged?: number;
  };
}

/**
 * Display processing summary
 */
export function displayProcessingSummary(summary: ProcessingSummary): void {
  const absoluteOutputDir = path.resolve(summary.outputDir);
  const linkedOutputDir = formatTerminalLink(`${summary.outputDir}/`, absoluteOutputDir);

  // Success message
  console.log(chalk.green('\n✓ Processing Complete!\n'));

  // 1. Gather stats for Summary Box
  const summaryLines: string[] = [];
  summaryLines.push(
    `${chalk.bold(chalk.white('Video File:'))}  ${path.basename(summary.videoPath)}`
  );

  if (summary.videoDuration) {
    summaryLines.push(
      `${chalk.bold(chalk.white('Duration:'))}    ${formatDuration(summary.videoDuration)}`
    );
  }

  summaryLines.push(
    `${chalk.bold(chalk.white('Clips Net:'))}   ${summary.clipsGenerated} viral hook${summary.clipsGenerated !== 1 ? 's' : ''} generated`
  );
  summaryLines.push(
    `${chalk.bold(chalk.white('Time Cost:'))}   ${formatDuration(summary.processingTime)}`
  );

  if (summary.totalCost !== undefined) {
    summaryLines.push(
      `${chalk.bold(chalk.white('API Cost:'))}    ${formatCost(summary.totalCost)}${summary.editorialModel ? ` (${summary.editorialModel})` : ''}`
    );
  }

  if (summary.passRate !== undefined) {
    summaryLines.push(
      `${chalk.bold(chalk.white('Pass Rate:'))}   ${formatPercentage(summary.passRate)} (strict quality gate)`
    );
  }

  summaryLines.push(
    `${chalk.bold(chalk.white('Output Dir:'))}  ${chalk.cyan(linkedOutputDir)} ${chalk.gray('(Ctrl/Cmd + Click to Open Folder)')}`
  );

  console.log(formatBox('📊 RUN SUMMARY', summaryLines));
  console.log('');

  // 2. 4-Layer stats (if available)
  if (summary.layerStats) {
    const layerLines: string[] = [];
    if (summary.layerStats.layer1Moments) {
      layerLines.push(`Layer 1: Found ${summary.layerStats.layer1Moments} candidate moments`);
    }
    if (summary.layerStats.layer2Boundaries) {
      layerLines.push(`Layer 2: Analyzed ${summary.layerStats.layer2Boundaries} boundaries`);
    }
    if (summary.layerStats.layer3Validated) {
      layerLines.push(
        `Layer 3: Validated ${summary.layerStats.layer3Validated} standalone thoughts`
      );
    }
    if (summary.layerStats.layer4Packaged) {
      layerLines.push(`Layer 4: Packaged ${summary.layerStats.layer4Packaged} professional clips`);
    }
    console.log(formatBox('🧠 4-LAYER EDITORIAL SYSTEM', layerLines));
    console.log('');
  }

  // 3. Clip details
  if (summary.clips && summary.clips.length > 0) {
    const clipsLines: string[] = [];

    summary.clips.forEach((clip, index) => {
      const number = chalk.gray(`${index + 1}.`);

      // Resolve click-to-play absolute video clip path
      const filename = clip.title.toLowerCase().endsWith('.mp4') ? clip.title : `${clip.title}.mp4`;
      const absoluteClipPath = path.resolve(summary.outputDir, 'clips', filename);
      const linkedClipTitle = formatTerminalLink(filename, absoluteClipPath);

      const durationStr = chalk.gray(`(${formatDurationCompact(clip.duration)})`);
      const timeRange = chalk.gray(
        `[${formatDurationCompact(clip.startTime)} - ${formatDurationCompact(clip.endTime)}]`
      );

      let line = `  ${number} ${chalk.cyan(linkedClipTitle)} ${durationStr} ${timeRange}`;

      if (clip.interestScore !== undefined) {
        const score = chalk.yellow(`★ ${(clip.interestScore * 100).toFixed(0)}%`);
        // Simple visual waveform representing the relative score level
        let wave = '▃▅▆▇█▆▅▃';
        if (clip.interestScore < 0.8) {
          wave = '▃▅▅▃    ';
        } else if (clip.interestScore < 0.9) {
          wave = '▃▅▆▆▅▃  ';
        }
        line += ` ${score} ${chalk.gray(wave)}`;
      }

      clipsLines.push(line);
    });

    clipsLines.push('');
    clipsLines.push(
      `  ${chalk.gray('* Ctrl/Cmd + Click on any clip filename above to play it directly!')}`
    );

    console.log(formatBox('✂️  GENERATED HIGHLIGHTS', clipsLines));
    console.log('');
  }

  // 4. Next steps / tips
  const tips: string[] = [
    `${chalk.white('Review clips locally:')}       ${chalk.cyan(`ls ${summary.outputDir}/`)}`,
  ];

  if (summary.editorialModel === 'gpt-4o') {
    tips.push(
      `${chalk.white('Try cost-optimized:')}   ${chalk.cyan('--editorial-model gpt-4o-mini')}`
    );
  }

  tips.push(`${chalk.white('Debug layers:')}         ${chalk.cyan('--export-layers')}`);

  tips.push(`${chalk.white('Adjust duration:')}       ${chalk.cyan('--min 20 --max 60')}`);

  console.log(formatBox('💡 RECOMMENDED NEXT STEPS', tips));
  console.log('');
}

/**
 * Display analysis summary (for analyze command)
 */
export function displayAnalysisSummary(data: {
  videoPath: string;
  videoDuration: number;
  transcriptWordCount?: number;
  momentsFound: number;
  estimatedClips: number;
  processingTime: number;
  outputFile?: string;
}): void {
  console.log(chalk.green('\n✓ Analysis complete!\n'));

  const stats: string[] = [
    `Video: ${data.videoPath}`,
    `Duration: ${formatDuration(data.videoDuration)}`,
  ];

  if (data.transcriptWordCount) {
    stats.push(`Words: ${data.transcriptWordCount}`);
  }

  stats.push(`Moments Found: ${data.momentsFound}`);
  stats.push(`Estimated Clips: ${data.estimatedClips}`);
  stats.push(`Processing Time: ${formatDuration(data.processingTime)}`);

  console.log(formatBox('📊 VIDEO ANALYSIS', stats));
  console.log('');

  if (data.outputFile) {
    const absoluteOutputFile = path.resolve(data.outputFile);
    const linkedOutputFile = formatTerminalLink(data.outputFile, absoluteOutputFile);
    console.log(formatBox('📁 OUTPUT FILE', [`File Location: ${chalk.cyan(linkedOutputFile)}`]));
    console.log('');
  }

  console.log(
    formatBox('💡 NEXT STEP', [
      `Generate clips: ${chalk.cyan(`arena generate ${data.videoPath} ${data.outputFile || 'analysis.json'}`)}`,
    ])
  );
  console.log('');
}

/**
 * Display transcription summary
 */
export function displayTranscriptionSummary(data: {
  videoPath: string;
  duration: number;
  wordCount: number;
  outputFile: string;
  processingTime: number;
  cost?: number;
}): void {
  console.log(chalk.green('\n✓ Transcription complete!\n'));

  const stats: string[] = [
    `Video: ${data.videoPath}`,
    `Duration: ${formatDuration(data.duration)}`,
    `Words: ${data.wordCount}`,
    `Processing Time: ${formatDuration(data.processingTime)}`,
  ];

  if (data.cost) {
    stats.push(`Cost: ${formatCost(data.cost)}`);
  }

  console.log(formatBox('📝 TRANSCRIPT STATS', stats));
  console.log('');

  const absoluteOutputFile = path.resolve(data.outputFile);
  const linkedOutputFile = formatTerminalLink(data.outputFile, absoluteOutputFile);
  console.log(formatBox('📁 OUTPUT FILE', [`File Location: ${chalk.cyan(linkedOutputFile)}`]));
  console.log('');

  console.log(
    formatBox('💡 NEXT STEP', [
      `Analyze: ${chalk.cyan(`arena analyze ${data.videoPath} -t ${data.outputFile}`)}`,
    ])
  );
  console.log('');
}

/**
 * Display error summary with suggestions
 */
export function displayErrorSummary(message: string, suggestions: string[]): void {
  console.log(chalk.red('\n✗ Processing Failed!\n'));

  console.log(formatBox('⚠️  ERROR DETAILS', [chalk.white(message)]));
  console.log('');

  if (suggestions.length > 0) {
    console.log(formatBox('💡 SUGGESTED REMEDIES', suggestions));
    console.log('');
  }
}

/**
 * Display warning banner
 */
export function displayWarning(message: string): void {
  console.log(chalk.yellow('\n⚠️  Warning: ') + chalk.white(message) + '\n');
}

/**
 * Display info banner
 */
export function displayInfo(message: string): void {
  console.log(chalk.cyan('\nℹ️  ') + chalk.white(message) + '\n');
}
