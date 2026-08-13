import chalk from 'chalk';
import path from 'path';
import { formatCost, formatDuration, formatDurationCompact } from './formatters.js';
import { printRows, success } from './output.js';

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
  layerStats?: Record<string, number | undefined>;
}

export function displayProcessingSummary(data: ProcessingSummary): void {
  success(
    `Done — generated ${data.clipsGenerated} clip${data.clipsGenerated === 1 ? '' : 's'} in ${formatDuration(data.processingTime)}`,
    [
      ['Input', path.basename(data.videoPath)],
      ['Output', path.resolve(data.outputDir)],
      ['API cost', data.totalCost === undefined ? undefined : formatCost(data.totalCost)],
    ]
  );

  if (data.clips?.length) {
    console.log(chalk.bold('Clips'));
    data.clips.forEach((clip, index) => {
      const score =
        clip.interestScore === undefined ? '' : ` · ${Math.round(clip.interestScore * 100)}%`;
      console.log(
        `  ${chalk.gray(`${index + 1}.`)} ${clip.title} ${chalk.gray(`${formatDurationCompact(clip.duration)}${score}`)}`
      );
    });
    console.log();
  }
}

export function displayAnalysisSummary(data: {
  videoPath: string;
  videoDuration: number;
  transcriptWordCount?: number;
  momentsFound: number;
  estimatedClips: number;
  processingTime: number;
  outputFile?: string;
}): void {
  success(
    `Analysis complete — ${data.momentsFound} candidate${data.momentsFound === 1 ? '' : 's'} found`,
    [
      ['Duration', formatDuration(data.videoDuration)],
      ['Words', data.transcriptWordCount],
      ['Elapsed', formatDuration(data.processingTime)],
      ['Output', data.outputFile ? path.resolve(data.outputFile) : undefined],
    ]
  );
}

export function displayTranscriptionSummary(data: {
  videoPath: string;
  duration: number;
  wordCount: number;
  outputFile: string;
  processingTime: number;
  cost?: number;
}): void {
  success(`Transcription complete — ${data.wordCount.toLocaleString()} words`, [
    ['Duration', formatDuration(data.duration)],
    ['Elapsed', formatDuration(data.processingTime)],
    ['Cost', data.cost === undefined ? undefined : formatCost(data.cost)],
    ['Output', path.resolve(data.outputFile)],
  ]);
}

export function displayErrorSummary(message: string, suggestions: string[]): void {
  console.error(`\n${chalk.red('✗')} ${message}`);
  if (suggestions.length) {
    console.error();
    printRows(suggestions.map((suggestion, index) => [`Try ${index + 1}`, suggestion]));
  }
  console.error();
}

export function displayWarning(message: string): void {
  console.log(`\n${chalk.yellow('!')} ${message}\n`);
}

export function displayInfo(message: string): void {
  console.log(`\n${chalk.cyan('i')} ${message}\n`);
}
