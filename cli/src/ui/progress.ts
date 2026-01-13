import ora, { Ora } from 'ora';
import chalk from 'chalk';

export class ProgressTracker {
  private spinner: Ora;
  private stages: Map<string, { completed: boolean; message: string }>;

  constructor() {
    this.spinner = ora();
    this.stages = new Map();
  }

  start(message: string): void {
    this.spinner.start(chalk.cyan(message));
  }

  updateStage(stage: string, progress: number, message: string): void {
    this.stages.set(stage, { completed: progress >= 100, message });

    const progressBar = this.createProgressBar(progress);
    const stageText = chalk.cyan(`[${stage}]`);
    const text = `${stageText} ${progressBar} ${message}`;

    this.spinner.text = text;

    if (progress >= 100) {
      this.spinner.succeed(chalk.green(`✓ ${stage}: ${message}`));
      this.spinner = ora(); // Create new spinner for next stage
      this.spinner.start();
    }
  }

  succeed(message: string): void {
    this.spinner.succeed(chalk.green(message));
  }

  fail(message: string): void {
    this.spinner.fail(chalk.red(message));
  }

  info(message: string): void {
    this.spinner.info(chalk.blue(message));
  }

  warn(message: string): void {
    this.spinner.warn(chalk.yellow(message));
  }

  stop(): void {
    this.spinner.stop();
  }

  private createProgressBar(progress: number, width: number = 20): string {
    const filled = Math.round((progress / 100) * width);
    const empty = width - filled;
    const bar = '█'.repeat(filled) + '░'.repeat(empty);
    const percentage = `${Math.round(progress)}%`;
    return chalk.cyan(`${bar}`) + ` ${percentage}`;
  }

  displaySummary(data: {
    videoPath: string;
    clipsGenerated: number;
    outputDir: string;
    processingTime?: number;
  }): void {
    console.log('\n' + chalk.bold.green('✓ Processing Complete!') + '\n');
    console.log(chalk.gray('─'.repeat(50)));
    console.log(chalk.bold('Summary:'));
    console.log(`  Video: ${chalk.cyan(data.videoPath)}`);
    console.log(`  Clips Generated: ${chalk.green(data.clipsGenerated)}`);
    console.log(`  Output Directory: ${chalk.cyan(data.outputDir)}`);
    if (data.processingTime) {
      const minutes = Math.floor(data.processingTime / 60);
      const seconds = Math.round(data.processingTime % 60);
      console.log(`  Processing Time: ${chalk.yellow(`${minutes}m ${seconds}s`)}`);
    }
    console.log(chalk.gray('─'.repeat(50)) + '\n');
    console.log(chalk.bold('What\'s next?'));
    console.log(`  • View clips: ${chalk.cyan(`cd ${data.outputDir}/clips`)}`);
    console.log(`  • Check metadata: ${chalk.cyan(`cat ${data.outputDir}/metadata.json`)}`);
    console.log(`  • Review transcript: ${chalk.cyan(`cat ${data.outputDir}/transcript.json`)}\n`);
  }
}
