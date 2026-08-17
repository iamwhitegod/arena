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
  progressMode?: 'determinate' | 'indeterminate';
  message?: string;
  startTime?: number;
  stateStartTime?: number;
  endTime?: number;
}

export class ProgressTracker {
  private spinner: Ora;
  private stages: Map<string, Stage>;
  private currentStage: string | null;
  private overallProgress: number;
  private elapsedTimer: ReturnType<typeof setInterval> | null;
  private simpleElapsedTimer: ReturnType<typeof setInterval> | null;
  private simpleIndeterminateMessage: string | null;
  private simpleIndeterminateStartTime: number | null;

  constructor() {
    this.spinner = ora();
    this.stages = new Map();
    this.currentStage = null;
    this.overallProgress = 0;
    this.elapsedTimer = null;
    this.simpleElapsedTimer = null;
    this.simpleIndeterminateMessage = null;
    this.simpleIndeterminateStartTime = null;
  }

  /**
   * Initialize stages for the pipeline
   */
  initializeStages(stageConfigs: Array<{ id: string; name: string; icon?: string }>): void {
    this.clearElapsedTimer();
    this.clearSimpleElapsedTimer();
    this.stages.clear();

    stageConfigs.forEach((config) => {
      this.stages.set(config.id, {
        id: config.id,
        name: config.name,
        icon: config.icon || '▪',
        status: 'pending',
        progress: 0,
        progressMode: 'determinate',
      });
    });
  }

  /**
   * Activate a stage without rendering it.
   *
   * Keeping activation separate from rendering lets updateStageProgress apply
   * the first progress value before the terminal is redrawn. Previously the
   * first event only started the stage and returned, so a real 5% update was
   * displayed as 0% until the next event arrived.
   */
  private activateStage(stageId: string, message?: string): Stage | undefined {
    const stage = this.stages.get(stageId);
    if (!stage) {
      return undefined;
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
    stage.stateStartTime = stage.startTime;
    stage.message = message;
    this.currentStage = stageId;

    return stage;
  }

  /**
   * Start a stage
   */
  startStage(stageId: string, message?: string): void {
    const stage = this.activateStage(stageId, message);
    if (!stage) {
      return;
    }

    stage.progressMode = 'determinate';

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
    stage.progressMode = 'determinate';
    if (message) {
      stage.message = message;
    }

    this.updateDisplay();
  }

  /**
   * Update progress for a specific stage
   */
  updateStageProgress(stageId: string, progress: number | null, message?: string): void {
    let stage = this.stages.get(stageId);
    if (!stage) {
      return;
    }

    if (stage.status === 'completed' || stage.status === 'failed') {
      return;
    }

    // Auto-start the stage, but render only after applying this first update.
    if (stage.status === 'pending') {
      stage = this.activateStage(stageId, message);
      if (!stage) {
        return;
      }
    }

    if (progress === null) {
      const stateChanged = stage.progressMode !== 'indeterminate' || stage.message !== message;
      stage.progressMode = 'indeterminate';
      if (message) {
        stage.message = message;
      }
      if (stateChanged) {
        stage.stateStartTime = Date.now();
      }
      this.updateDisplay();
      return;
    }

    // Progress events can arrive from multiple output streams. Never let a
    // delayed event move a stage backwards.
    const nextProgress = Math.min(100, Math.max(0, progress));
    stage.progress = Math.max(stage.progress ?? 0, nextProgress);
    stage.progressMode = 'determinate';
    if (message) {
      stage.message = message;
    }

    // Auto-complete if progress reaches 100
    if (stage.progress >= 100) {
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
    stage.progressMode = 'determinate';
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
    this.clearElapsedTimer();
  }

  private clearElapsedTimer(): void {
    if (this.elapsedTimer) {
      clearInterval(this.elapsedTimer);
      this.elapsedTimer = null;
    }
  }

  private clearSimpleElapsedTimer(): void {
    if (this.simpleElapsedTimer) {
      clearInterval(this.simpleElapsedTimer);
      this.simpleElapsedTimer = null;
    }
    this.simpleIndeterminateMessage = null;
    this.simpleIndeterminateStartTime = null;
  }

  private renderSimpleIndeterminate(): void {
    if (!this.simpleIndeterminateMessage || this.simpleIndeterminateStartTime === null) {
      return;
    }
    const elapsed = formatDuration((Date.now() - this.simpleIndeterminateStartTime) / 1000);
    this.spinner.text = chalk.cyan(
      `${this.simpleIndeterminateMessage} ${chalk.gray(`· ${elapsed} elapsed`)}`
    );
  }

  private syncElapsedTimer(stageList: Stage[]): void {
    const hasIndeterminateStage = stageList.some(
      (stage) => stage.status === 'in_progress' && stage.progressMode === 'indeterminate'
    );

    if (!hasIndeterminateStage) {
      this.clearElapsedTimer();
      return;
    }

    if (!this.elapsedTimer) {
      this.elapsedTimer = setInterval(() => this.updateDisplay(), 1000);
      this.elapsedTimer.unref?.();
    }
  }

  /**
   * Update the display with current stage information
   */
  private updateDisplay(): void {
    if (this.stages.size === 0) {
      return;
    }

    const stageList = Array.from(this.stages.values());
    const verifiedProgress = stageList.reduce(
      (total, stage) => total + (stage.status === 'completed' ? 100 : (stage.progress ?? 0)),
      0
    );
    this.overallProgress = verifiedProgress / stageList.length;

    // Build multi-line display
    const overallBar = formatProgressBar(this.overallProgress / 100, 16);
    const lines: string[] = [
      `${chalk.gray('Overall')} ${chalk.cyan(overallBar)} ${chalk.gray('(verified)')}`,
    ];

    stageList.forEach((stage, index) => {
      const stageNumber = `[${index + 1}/${stageList.length}]`;

      if (stage.status === 'pending') {
        lines.push(chalk.gray(`${stageNumber} ⏳ ${stage.name} - Pending`));
      } else if (stage.status === 'in_progress') {
        const progress = stage.progress || 0;
        const stageHeader = `${chalk.cyan(stageNumber)} ${chalk.bold(chalk.white(stage.name))}`;
        if (stage.progressMode === 'indeterminate') {
          const stateStartedAt = stage.stateStartTime || stage.startTime || Date.now();
          const elapsed = formatDuration((Date.now() - stateStartedAt) / 1000);
          const message = stage.message || 'Working';
          lines.push(
            `${stageHeader}\n     ${chalk.cyan('◐')} ${chalk.gray(`${message} · ${elapsed} elapsed`)}`
          );
        } else {
          const bar = formatProgressBar(progress / 100, 16);
          const message = stage.message ? chalk.gray(` - ${stage.message}`) : '';
          lines.push(`${stageHeader}\n     ${chalk.cyan(bar)}${message}`);
        }
      } else if (stage.status === 'completed') {
        const elapsed =
          stage.endTime && stage.startTime
            ? formatDuration((stage.endTime - stage.startTime) / 1000)
            : '';
        const message = stage.message || 'Complete';
        lines.push(
          chalk.green(`${stageNumber} ✓ ${stage.icon} ${stage.name}`) +
            chalk.gray(` - ${message}`) +
            (elapsed ? chalk.gray(` (${elapsed})`) : '')
        );
      } else if (stage.status === 'failed') {
        const message = stage.message || 'Failed';
        lines.push(chalk.red(`${stageNumber} ✗ ${stage.icon} ${stage.name} - ${message}`));
      }
    });

    // Update spinner with multi-line text
    this.spinner.text = '\n' + lines.join('\n');

    if (!this.spinner.isSpinning) {
      this.spinner.start();
    }
    this.syncElapsedTimer(stageList);
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
    this.clearSimpleElapsedTimer();
    this.spinner.start(chalk.cyan(message));
  }

  /**
   * Simple succeed method (backward compatible)
   */
  succeed(message: string): void {
    this.clearSimpleElapsedTimer();
    this.spinner.succeed(chalk.green(message));
  }

  /**
   * Simple fail method (backward compatible)
   */
  fail(message: string): void {
    this.clearSimpleElapsedTimer();
    this.spinner.fail(chalk.red(message));
  }

  /**
   * Info message
   */
  info(message: string): void {
    this.clearSimpleElapsedTimer();
    this.spinner.info(chalk.blue(message));
  }

  /**
   * Warning message
   */
  warn(message: string): void {
    this.clearSimpleElapsedTimer();
    this.spinner.warn(chalk.yellow(message));
  }

  /**
   * Stop spinner
   */
  stop(): void {
    this.clearElapsedTimer();
    this.clearSimpleElapsedTimer();
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
  updateStage(stageId: string, progress: number | null, message: string): void {
    this.updateStageProgress(stageId, progress, message);
  }

  /**
   * Show indeterminate progress
   */
  showIndeterminate(message: string): void {
    if (this.simpleIndeterminateMessage !== message) {
      this.simpleIndeterminateMessage = message;
      this.simpleIndeterminateStartTime = Date.now();
    }
    this.renderSimpleIndeterminate();
    if (!this.spinner.isSpinning) {
      this.spinner.start();
    }
    if (!this.simpleElapsedTimer) {
      this.simpleElapsedTimer = setInterval(() => this.renderSimpleIndeterminate(), 1000);
      this.simpleElapsedTimer.unref?.();
    }
  }

  /**
   * Show determinate progress
   */
  showDeterminate(percent: number, message: string): void {
    this.clearSimpleElapsedTimer();
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
