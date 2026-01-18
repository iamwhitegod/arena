import { spawn, ChildProcess } from 'child_process';
import path from 'path';
import chalk from 'chalk';
import { ProcessingError, SystemError } from '../errors/index.js';

export interface ProcessOptions {
  videoPath: string;
  outputDir: string;
  minDuration?: number;
  maxDuration?: number;
  clipCount?: number;
  use4Layer?: boolean;
  editorialModel?: 'gpt-4o' | 'gpt-4o-mini';
  exportLayers?: boolean;
  fast?: boolean;
  noCache?: boolean;
  padding?: number;
}

export interface AnalyzeOptions {
  videoPath: string;
  outputFile: string;
  minDuration?: number;
  maxDuration?: number;
  clipCount?: number;
  use4Layer?: boolean;
  editorialModel?: 'gpt-4o' | 'gpt-4o-mini';
  transcriptPath?: string;
}

export interface TranscribeOptions {
  videoPath: string;
  outputFile: string;
  noCache?: boolean;
}

export interface GenerateOptions {
  videoPath: string;
  analysisPath: string;
  outputDir: string;
  clipCount?: number;
  selectedIndices?: number[];
  fast?: boolean;
  padding?: number;
}

export interface ExtractAudioOptions {
  videoPath: string;
  outputFile: string;
  format: 'mp3' | 'wav' | 'aac' | 'flac';
  bitrate?: string;
  sampleRate?: number;
  mono: boolean;
}

export interface FormatOptions {
  inputPath: string;
  outputDir: string;
  platform: string;
  cropStrategy?: 'center' | 'smart' | 'top' | 'bottom';
  padStrategy?: 'blur' | 'black' | 'white' | 'color';
  padColor?: string;
  maintainQuality?: boolean;
}

export interface ProgressUpdate {
  stage: string;
  progress: number;
  message: string;
}

export class PythonBridge {
  private enginePath: string;
  private currentProcess: ChildProcess | null = null;
  private isShuttingDown = false;

  constructor() {
    // Path to the Python engine (relative to CLI directory)
    this.enginePath = path.join(__dirname, '../../../engine');

    // Setup graceful shutdown handlers
    this.setupShutdownHandlers();
  }

  /**
   * Get the engine path for external use
   */
  getEnginePath(): string {
    return this.enginePath;
  }

  /**
   * Setup handlers for graceful shutdown
   */
  private setupShutdownHandlers(): void {
    const shutdownHandler = async () => {
      if (this.isShuttingDown) {
        return;
      }

      this.isShuttingDown = true;
      console.log(chalk.yellow('\n\n⚠️  Interrupted by user. Cleaning up...\n'));

      if (this.currentProcess && !this.currentProcess.killed) {
        // Send SIGTERM to allow Python process to clean up
        this.currentProcess.kill('SIGTERM');

        // Give it 3 seconds to exit gracefully
        await new Promise((resolve) => setTimeout(resolve, 3000));

        // Force kill if still running
        if (this.currentProcess && !this.currentProcess.killed) {
          this.currentProcess.kill('SIGKILL');
        }
      }

      process.exit(130); // 128 + SIGINT
    };

    process.on('SIGINT', shutdownHandler);
    process.on('SIGTERM', shutdownHandler);
  }

  async runProcess(
    options: ProcessOptions,
    onProgress?: (update: ProgressUpdate) => void,
    onError?: (error: string) => void
  ): Promise<any> {
    return new Promise((resolve, reject) => {
      // Check if shutdown is in progress
      if (this.isShuttingDown) {
        reject(new SystemError('INTERRUPTED', 'Process was interrupted by user'));
        return;
      }

      // Use arena-cli directly
      const arenaCliPath = path.join(this.enginePath, 'arena-cli');

      const args = [
        'process',
        options.videoPath,
        '-o',
        options.outputDir,
      ];

      if (options.clipCount) {
        args.push('-n', options.clipCount.toString());
      }
      if (options.minDuration) {
        args.push('--min', options.minDuration.toString());
      }
      if (options.maxDuration) {
        args.push('--max', options.maxDuration.toString());
      }
      if (options.use4Layer) {
        args.push('--use-4layer');
      }
      if (options.editorialModel) {
        args.push('--editorial-model', options.editorialModel);
      }
      if (options.exportLayers) {
        args.push('--export-editorial-layers');
      }
      if (options.fast) {
        args.push('--fast');
      }
      if (options.noCache) {
        args.push('--no-cache');
      }
      if (options.padding !== undefined) {
        args.push('--padding', options.padding.toString());
      }

      this.runCommand(arenaCliPath, args, resolve, reject, onProgress, onError);
    });
  }

  async runAnalyze(
    options: AnalyzeOptions,
    onProgress?: (update: ProgressUpdate) => void,
    onError?: (error: string) => void
  ): Promise<any> {
    return new Promise((resolve, reject) => {
      if (this.isShuttingDown) {
        reject(new SystemError('INTERRUPTED', 'Process was interrupted by user'));
        return;
      }

      const arenaCliPath = path.join(this.enginePath, 'arena-cli');

      const args = [
        'analyze',
        options.videoPath,
        '-o',
        options.outputFile,
      ];

      if (options.clipCount) {
        args.push('-n', options.clipCount.toString());
      }
      if (options.minDuration) {
        args.push('--min', options.minDuration.toString());
      }
      if (options.maxDuration) {
        args.push('--max', options.maxDuration.toString());
      }
      if (options.use4Layer) {
        args.push('--use-4layer');
      }
      if (options.editorialModel) {
        args.push('--editorial-model', options.editorialModel);
      }
      if (options.transcriptPath) {
        args.push('--transcript', options.transcriptPath);
      }

      this.runCommand(arenaCliPath, args, resolve, reject, onProgress, onError);
    });
  }

  async runTranscribe(
    options: TranscribeOptions,
    onProgress?: (update: ProgressUpdate) => void,
    onError?: (error: string) => void
  ): Promise<any> {
    return new Promise((resolve, reject) => {
      if (this.isShuttingDown) {
        reject(new SystemError('INTERRUPTED', 'Process was interrupted by user'));
        return;
      }

      const arenaCliPath = path.join(this.enginePath, 'arena-cli');

      const args = [
        'transcribe',
        options.videoPath,
        '-o',
        options.outputFile,
      ];

      if (options.noCache) {
        args.push('--no-cache');
      }

      this.runCommand(arenaCliPath, args, resolve, reject, onProgress, onError);
    });
  }

  async runGenerate(
    options: GenerateOptions,
    onProgress?: (update: ProgressUpdate) => void,
    onError?: (error: string) => void
  ): Promise<any> {
    return new Promise((resolve, reject) => {
      if (this.isShuttingDown) {
        reject(new SystemError('INTERRUPTED', 'Process was interrupted by user'));
        return;
      }

      const arenaCliPath = path.join(this.enginePath, 'arena-cli');

      const args = [
        'generate',
        options.videoPath,
        options.analysisPath,
        '-o',
        options.outputDir,
      ];

      if (options.clipCount) {
        args.push('-n', options.clipCount.toString());
      }
      if (options.selectedIndices && options.selectedIndices.length > 0) {
        args.push('--select', options.selectedIndices.join(','));
      }
      if (options.fast) {
        args.push('--fast');
      }
      if (options.padding !== undefined) {
        args.push('--padding', options.padding.toString());
      }

      this.runCommand(arenaCliPath, args, resolve, reject, onProgress, onError);
    });
  }

  async runExtractAudio(
    options: ExtractAudioOptions,
    onProgress?: (update: ProgressUpdate) => void,
    onError?: (error: string) => void
  ): Promise<any> {
    return new Promise((resolve, reject) => {
      if (this.isShuttingDown) {
        reject(new SystemError('INTERRUPTED', 'Process was interrupted by user'));
        return;
      }

      const arenaCliPath = path.join(this.enginePath, 'arena-cli');

      const args = [
        'extract-audio',
        options.videoPath,
        '-o',
        options.outputFile,
        '--format',
        options.format,
      ];

      if (options.bitrate) {
        args.push('--bitrate', options.bitrate);
      }
      if (options.sampleRate) {
        args.push('--sample-rate', options.sampleRate.toString());
      }
      if (options.mono) {
        args.push('--mono');
      }

      this.runCommand(arenaCliPath, args, resolve, reject, onProgress, onError);
    });
  }

  /**
   * Common method to run Python CLI commands
   */
  private runCommand(
    arenaCliPath: string,
    args: string[],
    resolve: (value: any) => void,
    reject: (reason?: any) => void,
    onProgress?: (update: ProgressUpdate) => void,
    onError?: (error: string) => void
  ): void {
    const pythonProcess = spawn(arenaCliPath, args, {
      cwd: this.enginePath,
      env: { ...process.env },
    });

    // Store process for shutdown handling
    this.currentProcess = pythonProcess;

    let outputBuffer = '';
    let errorBuffer = '';

    pythonProcess.stdout.on('data', (data: Buffer) => {
      const text = data.toString();
      outputBuffer += text;

      // Try to parse progress updates (JSON on separate lines)
      const lines = outputBuffer.split('\n');
      outputBuffer = lines.pop() || ''; // Keep incomplete line in buffer

      for (const line of lines) {
        if (line.trim().startsWith('{')) {
          try {
            const update = JSON.parse(line);
            if (update.type === 'progress' && onProgress) {
              onProgress({
                stage: update.stage,
                progress: update.progress,
                message: update.message,
              });
            } else if (update.type === 'result') {
              resolve(update.data);
            }
          } catch (e) {
            // Not JSON, just regular output
            console.log(chalk.gray(line));
          }
        } else if (line.trim()) {
          console.log(chalk.gray(line));
        }
      }
    });

    pythonProcess.stderr.on('data', (data: Buffer) => {
      const text = data.toString();
      errorBuffer += text;
      if (onError) {
        onError(text);
      } else {
        console.error(chalk.red(text));
      }
    });

    pythonProcess.on('close', (code: number) => {
      // Clear current process
      this.currentProcess = null;

      if (code === 0) {
        resolve({ success: true });
      } else if (code === 130 || this.isShuttingDown) {
        // User interrupted (SIGINT)
        reject(
          new SystemError(
            'INTERRUPTED',
            'Process was interrupted by user',
            'This is normal if you pressed Ctrl+C'
          )
        );
      } else {
        // Parse error from Python output
        const errorMessage = this.parseErrorFromOutput(errorBuffer);

        reject(
          new ProcessingError(
            'PROCESSING_FAILED',
            errorMessage || `Processing failed with exit code ${code}`,
            'Check the error message above for details'
          )
        );
      }
    });

    pythonProcess.on('error', (error: Error) => {
      // Clear current process
      this.currentProcess = null;

      reject(
        new SystemError(
          'PYTHON_START_FAILED',
          `Failed to start Python process: ${error.message}`,
          'Ensure the arena-cli script is executable: chmod +x engine/arena-cli'
        )
      );
    });
  }

  /**
   * Parse error message from Python output
   */
  private parseErrorFromOutput(errorOutput: string): string {
    // Try to extract meaningful error from Python traceback
    const lines = errorOutput.trim().split('\n');

    // Look for common error patterns
    for (const line of lines) {
      if (line.includes('Error:') || line.includes('Exception:')) {
        return line.trim();
      }
    }

    // Return last non-empty line as error
    for (let i = lines.length - 1; i >= 0; i--) {
      const line = lines[i].trim();
      if (line && !line.startsWith('File ') && !line.startsWith('  ')) {
        return line;
      }
    }

    return errorOutput.trim();
  }

  async runFormat(
    options: FormatOptions,
    onProgress?: (update: ProgressUpdate) => void,
    onError?: (error: string) => void
  ): Promise<any> {
    return new Promise((resolve, reject) => {
      const arenaCliPath = path.join(this.enginePath, 'arena-cli');

      const args = [
        'format',
        options.inputPath,
        '--output', options.outputDir,
        '--platform', options.platform,
      ];

      if (options.cropStrategy) {
        args.push('--crop', options.cropStrategy);
      }

      if (options.padStrategy) {
        args.push('--pad', options.padStrategy);
      }

      if (options.padColor) {
        args.push('--pad-color', options.padColor);
      }

      if (options.maintainQuality === false) {
        args.push('--no-quality');
      }

      this.runCommand(arenaCliPath, args, resolve, reject, onProgress, onError);
    });
  }

  async checkPythonEnvironment(): Promise<{ available: boolean; version?: string; error?: string }> {
    return new Promise((resolve) => {
      const pythonProcess = spawn('python3', ['--version']);

      let output = '';

      pythonProcess.stdout.on('data', (data: Buffer) => {
        output += data.toString();
      });

      pythonProcess.stderr.on('data', (data: Buffer) => {
        output += data.toString();
      });

      pythonProcess.on('close', (code: number) => {
        if (code === 0) {
          const version = output.trim();
          resolve({ available: true, version });
        } else {
          resolve({
            available: false,
            error: 'Python 3 is not installed or not in PATH',
          });
        }
      });

      pythonProcess.on('error', () => {
        resolve({
          available: false,
          error: 'Python 3 is not installed or not in PATH',
        });
      });
    });
  }

  async checkDependencies(): Promise<{ installed: boolean; missing?: string[] }> {
    return new Promise((resolve) => {
      const pythonProcess = spawn('python3', ['-c', 'import arena; print("ok")'], {
        cwd: this.enginePath,
        env: { ...process.env, PYTHONPATH: this.enginePath },
      });

      let output = '';

      pythonProcess.stdout.on('data', (data: Buffer) => {
        output += data.toString();
      });

      pythonProcess.on('close', (code: number) => {
        if (code === 0 && output.includes('ok')) {
          resolve({ installed: true });
        } else {
          resolve({
            installed: false,
            missing: ['arena engine dependencies'],
          });
        }
      });

      pythonProcess.on('error', () => {
        resolve({
          installed: false,
          missing: ['arena engine dependencies'],
        });
      });
    });
  }
}
