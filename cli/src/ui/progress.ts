/**
 * Advanced progress tracking for Arena CLI
 * Multi-stage progress with beautiful visualization
 */

import ora, { Ora } from 'ora';
import chalk from 'chalk';
import { formatProgressBar, formatDuration } from './formatters.js';
import { displayProcessingSummary, ProcessingSummary } from './summary.js';

export interface Stage {
  id: string;
  name: string;
  icon: string;
  status: 'pending' | 'in_progress' | 'completed' | 'failed';
  progress?: number;
  message?: string;
  startTime?: number;
  endTime?: number;
}

export class ProgressTracker {
  private spinner: Ora;
  private stages: Map<string, Stage>;
  private currentStage: string | null;
  private overallProgress: number;

  constructor() {
    this.spinner = ora();
    this.stages = new Map();
    this.currentStage = null;
    this.overallProgress = 0;
  }

  /**
   * Initialize stages for the pipeline
   */
  initializeStages(stageConfigs: Array<{ id: string; name: string; icon?: string }>): void {
    this.stages.clear();

    stageConfigs.forEach((config) => {
      this.stages.set(config.id, {
        id: config.id,
        name: config.name,
        icon: config.icon || '▪',
        status: 'pending',
        progress: 0,
      });
    });
  }

  /**
   * Start a stage
   */
  startStage(stageId: string, message?: string): void {
    const stage = this.stages.get(stageId);
    if (!stage) {
      return;
    }

    // Mark previous stage as complete
    if (this.currentStage && this.currentStage !== stageId) {
      const prevStage = this.stages.get(this.currentStage);
      if (prevStage && prevStage.status === 'in_progress') {
        prevStage.status = 'completed';
        prevStage.endTime = Date.now();
        prevStage.progress = 100;
      }
    }

    stage.status = 'in_progress';
    stage.startTime = Date.now();
    stage.message = message;
    this.currentStage = stageId;

    this.updateDisplay();
  }

  /**
   * Update progress for current stage
   */
  updateProgress(progress: number, message?: string): void {
    if (!this.currentStage) {
      return;
    }

    const stage = this.stages.get(this.currentStage);
    if (!stage) {
      return;
    }

    stage.progress = Math.min(100, Math.max(0, progress));
    if (message) {
      stage.message = message;
    }

    this.updateDisplay();
  }

  /**
   * Update progress for a specific stage
   */
  updateStageProgress(stageId: string, progress: number, message?: string): void {
    const stage = this.stages.get(stageId);
    if (!stage) {
      return;
    }

    // Auto-start stage if not started
    if (stage.status === 'pending') {
      this.startStage(stageId, message);
      return;
    }

    stage.progress = Math.min(100, Math.max(0, progress));
    if (message) {
      stage.message = message;
    }

    // Auto-complete if progress reaches 100
    if (progress >= 100) {
      stage.status = 'completed';
      stage.endTime = Date.now();
    }

    this.updateDisplay();
  }

  /**
   * Complete current stage
   */
  completeStage(message?: string): void {
    if (!this.currentStage) {
      return;
    }

    const stage = this.stages.get(this.currentStage);
    if (!stage) {
      return;
    }

    stage.status = 'completed';
    stage.progress = 100;
    stage.endTime = Date.now();
    if (message) {
      stage.message = message;
    }

    this.updateDisplay();
  }

  /**
   * Mark stage as failed
   */
  failStage(stageId?: string, message?: string): void {
    const targetStage = stageId || this.currentStage;
    if (!targetStage) {
      return;
    }

    const stage = this.stages.get(targetStage);
    if (!stage) {
      return;
    }

    stage.status = 'failed';
    stage.endTime = Date.now();
    if (message) {
      stage.message = message;
    }

    this.spinner.fail(chalk.red(`${stage.icon} ${stage.name}: ${message || 'Failed'}`));
  }

  /**
   * Update the display with current stage information
   */
  private updateDisplay(): void {
    if (this.stages.size === 0) {
      return;
    }

    const stageList = Array.from(this.stages.values());
    const completedCount = stageList.filter((s) => s.status === 'completed').length;
    this.overallProgress = (completedCount / stageList.length) * 100;

    // Build multi-line display
    const lines: string[] = [];

    stageList.forEach((stage, index) => {
      const stageNumber = `[${index + 1}/${stageList.length}]`;
      const icon = this.getStageIcon(stage);
      const stageName = `${icon} ${stage.name}`;

      if (stage.status === 'pending') {
        lines.push(chalk.gray(`${stageNumber} ${stageName} - Pending`));
      } else if (stage.status === 'in_progress') {
        const progress = stage.progress || 0;
        const bar = formatProgressBar(progress / 100, 10);
        const message = stage.message ? chalk.gray(` - ${stage.message}`) : '';
        lines.push(`${chalk.cyan(stageNumber)} ${chalk.white(stageName)}\n  ${bar}${message}`);
      } else if (stage.status === 'completed') {
        const elapsed = stage.endTime && stage.startTime
          ? formatDuration((stage.endTime - stage.startTime) / 1000)
          : '';
        const message = stage.message || 'Complete';
        lines.push(chalk.green(`${stageNumber} ✓ ${stageName}`) + chalk.gray(` - ${message}`) + (elapsed ? chalk.gray(` (${elapsed})`) : ''));
      } else if (stage.status === 'failed') {
        const message = stage.message || 'Failed';
        lines.push(chalk.red(`${stageNumber} ✗ ${stageName} - ${message}`));
      }
    });

    // Update spinner with multi-line text
    this.spinner.text = '\n' + lines.join('\n');

    if (!this.spinner.isSpinning) {
      this.spinner.start();
    }
  }

  /**
   * Get icon for stage based on status
   */
  private getStageIcon(stage: Stage): string {
    switch (stage.status) {
      case 'pending':
        return chalk.gray('⏳');
      case 'in_progress':
        return stage.icon;
      case 'completed':
        return chalk.green('✓');
      case 'failed':
        return chalk.red('✗');
      default:
        return stage.icon;
    }
  }

  /**
   * Simple start method (backward compatible)
   */
  start(message: string): void {
    this.spinner.start(chalk.cyan(message));
  }

  /**
   * Simple succeed method (backward compatible)
   */
  succeed(message: string): void {
    this.spinner.succeed(chalk.green(message));
  }

  /**
   * Simple fail method (backward compatible)
   */
  fail(message: string): void {
    this.spinner.fail(chalk.red(message));
  }

  /**
   * Info message
   */
  info(message: string): void {
    this.spinner.info(chalk.blue(message));
  }

  /**
   * Warning message
   */
  warn(message: string): void {
    this.spinner.warn(chalk.yellow(message));
  }

  /**
   * Stop spinner
   */
  stop(): void {
    this.spinner.stop();
  }

  /**
   * Display processing summary (delegates to summary module)
   */
  displaySummary(summary: ProcessingSummary): void {
    this.stop();
    displayProcessingSummary(summary);
  }

  /**
   * Update stage by name or ID
   */
  updateStage(stageId: string, progress: number, message: string): void {
    this.updateStageProgress(stageId, progress, message);
  }

  /**
   * Show indeterminate progress
   */
  showIndeterminate(message: string): void {
    this.spinner.text = chalk.cyan(message);
    if (!this.spinner.isSpinning) {
      this.spinner.start();
    }
  }

  /**
   * Show determinate progress
   */
  showDeterminate(percent: number, message: string): void {
    const bar = formatProgressBar(percent / 100, 20);
    this.spinner.text = `${bar} ${chalk.cyan(message)}`;
    if (!this.spinner.isSpinning) {
      this.spinner.start();
    }
  }

  /**
   * Show multi-stage progress (main method for complex pipelines)
   */
  showMultiStage(stages: Stage[]): void {
    // Update internal stages
    stages.forEach((stage) => {
      this.stages.set(stage.id, stage);
    });

    this.updateDisplay();
  }

  /**
   * Get overall progress percentage
   */
  getOverallProgress(): number {
    return this.overallProgress;
  }
}
