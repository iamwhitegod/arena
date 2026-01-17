/**
 * Summary display for Arena CLI
 * Shows beautiful summaries after processing completes
 */

import chalk from 'chalk';
import {
  formatDuration,
  formatCost,
  formatPercentage,
  formatList,
  formatDurationCompact,
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
  use4Layer?: boolean;
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
  const separator = chalk.gray('━'.repeat(60));

  console.log('\n' + separator);
  console.log(chalk.green('✨ Success! ') + chalk.white(`Generated ${summary.clipsGenerated} professional clip${summary.clipsGenerated !== 1 ? 's' : ''}`));
  console.log(separator);

  // Main stats
  console.log(chalk.cyan('\n📊 Summary:'));

  const stats: string[] = [];

  if (summary.videoDuration) {
    stats.push(`Video Duration: ${formatDuration(summary.videoDuration)}`);
  }

  stats.push(`Clips Generated: ${summary.clipsGenerated}`);
  stats.push(`Processing Time: ${formatDuration(summary.processingTime)}`);

  if (summary.totalCost !== undefined) {
    stats.push(`Total Cost: ${formatCost(summary.totalCost)}${summary.editorialModel ? ` (${summary.editorialModel})` : ''}`);
  }

  if (summary.passRate !== undefined && summary.use4Layer) {
    stats.push(`Pass Rate: ${formatPercentage(summary.passRate)} (strict quality gate)`);
  }

  console.log(formatList(stats));

  // 4-Layer stats (if available)
  if (summary.use4Layer && summary.layerStats) {
    console.log(chalk.cyan('\n🧠 4-Layer Editorial System:'));
    const layerStats: string[] = [];

    if (summary.layerStats.layer1Moments) {
      layerStats.push(`Layer 1: Found ${summary.layerStats.layer1Moments} candidate moments`);
    }
    if (summary.layerStats.layer2Boundaries) {
      layerStats.push(`Layer 2: Analyzed ${summary.layerStats.layer2Boundaries} boundaries`);
    }
    if (summary.layerStats.layer3Validated) {
      layerStats.push(`Layer 3: Validated ${summary.layerStats.layer3Validated} standalone thoughts`);
    }
    if (summary.layerStats.layer4Packaged) {
      layerStats.push(`Layer 4: Packaged ${summary.layerStats.layer4Packaged} professional clips`);
    }

    console.log(formatList(layerStats));
  }

  // Output location
  console.log(chalk.cyan('\n📁 Output:'));
  console.log(chalk.white(`  ${summary.outputDir}/`));

  // Clip details
  if (summary.clips && summary.clips.length > 0) {
    console.log(chalk.cyan('\n✂️  Clips:'));
    summary.clips.forEach((clip, index) => {
      const number = chalk.gray(`${index + 1}.`);
      const title = chalk.white(clip.title);
      const duration = chalk.gray(`(${formatDurationCompact(clip.duration)})`);
      const timeRange = chalk.gray(`[${formatDurationCompact(clip.startTime)} - ${formatDurationCompact(clip.endTime)}]`);

      let line = `  ${number} ${title} ${duration} ${timeRange}`;

      if (clip.interestScore !== undefined) {
        const score = chalk.yellow(`★ ${(clip.interestScore * 100).toFixed(0)}%`);
        line += ` ${score}`;
      }

      console.log(line);
    });
  }

  // Next steps / tips
  console.log(chalk.cyan('\n💡 Next steps:'));
  const tips: string[] = [
    `Review clips: ${chalk.white(`ls ${summary.outputDir}/`)}`,
  ];

  if (summary.use4Layer && summary.editorialModel === 'gpt-4o') {
    tips.push(`Try cost-optimized: ${chalk.white('--editorial-model gpt-4o-mini')}`);
  }

  if (summary.use4Layer) {
    tips.push(`Debug layers: ${chalk.white('--export-layers')}`);
  } else {
    tips.push(`Try 4-layer system: ${chalk.white('--use-4layer')}`);
  }

  tips.push(`Adjust duration: ${chalk.white('--min 20 --max 60')}`);

  console.log(formatList(tips));

  console.log('\n' + separator + '\n');
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
  const separator = chalk.gray('━'.repeat(60));

  console.log('\n' + separator);
  console.log(chalk.green('✨ Analysis complete!'));
  console.log(separator);

  console.log(chalk.cyan('\n📊 Video Analysis:'));

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

  console.log(formatList(stats));

  if (data.outputFile) {
    console.log(chalk.cyan('\n📁 Output:'));
    console.log(chalk.white(`  ${data.outputFile}`));
  }

  console.log(chalk.cyan('\n💡 Next step:'));
  console.log(chalk.white(`  Generate clips: arena generate ${data.videoPath} ${data.outputFile || 'analysis.json'}`));

  console.log('\n' + separator + '\n');
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
  const separator = chalk.gray('━'.repeat(60));

  console.log('\n' + separator);
  console.log(chalk.green('✨ Transcription complete!'));
  console.log(separator);

  console.log(chalk.cyan('\n📝 Transcript:'));

  const stats: string[] = [
    `Video: ${data.videoPath}`,
    `Duration: ${formatDuration(data.duration)}`,
    `Words: ${data.wordCount}`,
    `Processing Time: ${formatDuration(data.processingTime)}`,
  ];

  if (data.cost) {
    stats.push(`Cost: ${formatCost(data.cost)}`);
  }

  console.log(formatList(stats));

  console.log(chalk.cyan('\n📁 Output:'));
  console.log(chalk.white(`  ${data.outputFile}`));

  console.log(chalk.cyan('\n💡 Next step:'));
  console.log(chalk.white(`  Analyze: arena analyze ${data.videoPath} -t ${data.outputFile}`));

  console.log('\n' + separator + '\n');
}

/**
 * Display error summary with suggestions
 */
export function displayErrorSummary(message: string, suggestions: string[]): void {
  const separator = chalk.gray('━'.repeat(60));

  console.log('\n' + separator);
  console.log(chalk.red('✗ Processing failed'));
  console.log(separator);

  console.log(chalk.white(`\n  ${message}\n`));

  if (suggestions.length > 0) {
    console.log(chalk.cyan('💡 Suggestions:'));
    console.log(formatList(suggestions));
  }

  console.log('\n' + separator + '\n');
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
