import { spawn, ChildProcess } from 'child_process';
import path from 'path';
import { fileURLToPath } from 'url';
import chalk from 'chalk';
import fs from 'fs-extra';
import { ProcessingError, SystemError } from '../errors/index.js';
import {
  getActiveBinDir,
  getActivePythonPath,
  getArenaHome,
  prependPath,
  resolveEnginePath,
} from '../core/runtime.js';

export interface ProcessOptions {
  videoPath: string;
  outputDir: string;
  minDuration?: number;
  maxDuration?: number;
  clipCount?: number;
  editorialModel?: 'gpt-4o' | 'gpt-4o-mini';
  exportLayers?: boolean;
  fast?: boolean;
  noCache?: boolean;
  padding?: number;
  sceneDetection?: boolean;
  platform?: string;
  cropStrategy?: string;
  padStrategy?: string;
  padColor?: string;
  captions?: boolean;
  captionFontSize?: number;
  captionColor?: string;
  captionPosition?: string;
  cookiesFromBrowser?: string;
}

export interface AnalyzeOptions {
  videoPath: string;
  outputFile: string;
  minDuration?: number;
  maxDuration?: number;
  clipCount?: number;
  editorialModel?: 'gpt-4o' | 'gpt-4o-mini';
  transcriptPath?: string;
  sceneDetection?: boolean;
}

export interface TranscribeOptions {
  videoPath: string;
  outputFile: string;
  noCache?: boolean;
  cookiesFromBrowser?: string;
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
  cookiesFromBrowser?: string;
}

export interface FormatOptions {
  inputPath: string;
  outputDir: string;
  platform: string;
  cropStrategy?: 'center' | 'smart' | 'top' | 'bottom';
  padStrategy?: 'blur' | 'black' | 'white' | 'color';
  padColor?: string;
  maintainQuality?: boolean;
  captions?: string;
  captionFontSize?: number;
  captionColor?: string;
  captionPosition?: string;
}

export interface DetectScenesOptions {
  videoPath: string;
  outputFile: string;
  threshold?: number;
  minSceneDuration?: number;
  generateReport?: boolean;
}

export interface ProgressUpdate {
  stage: string;
  progress: number;
  message: string;
}

export class PythonBridge {
  private enginePath: string | null;
  private currentProcess: ChildProcess | null = null;
  private isShuttingDown = false;

  constructor() {
    // Path to the Python engine (relative to CLI directory)
    // ES module equivalent of __dirname
    const __filename = fileURLToPath(import.meta.url);
    const __dirname = path.dirname(__filename);
    this.enginePath = resolveEnginePath(__dirname);

    // Setup graceful shutdown handlers
    this.setupShutdownHandlers();
  }

  /**
   * Helper to ensure all packaged dependencies (arena-engine sidecar, ffmpeg, ffprobe)
   * are extracted to user's home directory.
   */
  private ensureBinariesExtracted(): string {
    const targetBinDir = path.join(getArenaHome(), 'bin');
    fs.ensureDirSync(targetBinDir);

    const binaries = [
      process.platform === 'win32' ? 'arena-engine.exe' : 'arena-engine',
      process.platform === 'win32' ? 'ffmpeg.exe' : 'ffmpeg',
      process.platform === 'win32' ? 'ffprobe.exe' : 'ffprobe',
    ];

    // __dirname is dist/bridge/ inside package or workspace
    // So relative from bridge to bin folder inside dist is ../bin
    const __filename = fileURLToPath(import.meta.url);
    const __dirname = path.dirname(__filename);

    for (const binName of binaries) {
      const targetPath = path.join(targetBinDir, binName);
      const sourcePath = path.join(__dirname, '../bin', binName);

      if (!fs.existsSync(targetPath)) {
        if (fs.existsSync(sourcePath)) {
          console.log(chalk.cyan(`📦 Extracting bundled dependency: ${binName}...`));
          try {
            fs.copySync(sourcePath, targetPath);
            fs.chmodSync(targetPath, 0o755);
          } catch (err: any) {
            console.error(chalk.red(`❌ Failed to extract ${binName}: ${err.message}`));
          }
        }
      }
    }

    return targetBinDir;
  }

  /**
   * Get the command and args to run arena-cli
   * On Windows, explicitly use python. On Unix, use the script directly.
   */
  private getArenaCommand(subcommand: string, args: string[]): { command: string; args: string[] } {
    const isPackaged = typeof (process as any).pkg !== 'undefined';

    if (isPackaged) {
      const targetBinDir = this.ensureBinariesExtracted();
      const targetEnginePath = path.join(
        targetBinDir,
        process.platform === 'win32' ? 'arena-engine.exe' : 'arena-engine'
      );
      return {
        command: targetEnginePath,
        args: [subcommand, ...args],
      };
    }

    const managedPython = getActivePythonPath();
    if (fs.existsSync(managedPython)) {
      return {
        command: managedPython,
        args: ['-m', 'arena.cli.main', subcommand, ...args],
      };
    }

    const enginePath = this.enginePath;
    if (!enginePath) {
      throw new SystemError(
        'ENGINE_NOT_FOUND',
        'The Arena engine is missing from this installation',
        'Reinstall Arena, then run "arena setup --check"'
      );
    }
    const arenaCliPath = path.join(enginePath, 'arena-cli');

    if (process.platform === 'win32') {
      // Windows: Use python command
      return {
        command: 'python',
        args: [arenaCliPath, subcommand, ...args],
      };
    } else {
      // Unix: Use script directly with shebang
      return {
        command: arenaCliPath,
        args: [subcommand, ...args],
      };
    }
  }

  /**
   * Get the engine path for external use
   */
  getEnginePath(): string {
    const isPackaged = typeof (process as any).pkg !== 'undefined';
    if (isPackaged) {
      return path.join(getArenaHome(), 'bin');
    }
    return this.enginePath ?? '';
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

      // Build command args
      const cmdArgs = [options.videoPath, '-o', options.outputDir];

      if (options.clipCount) {
        cmdArgs.push('-n', options.clipCount.toString());
      }
      if (options.minDuration) {
        cmdArgs.push('--min', options.minDuration.toString());
      }
      if (options.maxDuration) {
        cmdArgs.push('--max', options.maxDuration.toString());
      }
      if (options.editorialModel) {
        cmdArgs.push('--editorial-model', options.editorialModel);
      }
      if (options.exportLayers) {
        cmdArgs.push('--export-editorial-layers');
      }
      if (options.fast) {
        cmdArgs.push('--fast');
      }
      if (options.noCache) {
        cmdArgs.push('--no-cache');
      }
      if (options.padding !== undefined) {
        cmdArgs.push('--padding', options.padding.toString());
      }
      if (options.sceneDetection) {
        cmdArgs.push('--scene-detection');
      }
      if (options.platform) {
        cmdArgs.push('--platform', options.platform);
      }
      if (options.cropStrategy) {
        cmdArgs.push('--crop', options.cropStrategy);
      }
      if (options.padStrategy) {
        cmdArgs.push('--pad', options.padStrategy);
      }
      if (options.padColor) {
        cmdArgs.push('--pad-color', options.padColor);
      }
      if (options.captions) {
        cmdArgs.push('--captions');
      }
      if (options.captionFontSize) {
        cmdArgs.push('--caption-font-size', options.captionFontSize.toString());
      }
      if (options.captionColor) {
        cmdArgs.push('--caption-color', options.captionColor);
      }
      if (options.captionPosition) {
        cmdArgs.push('--caption-position', options.captionPosition);
      }
      if (options.cookiesFromBrowser) {
        cmdArgs.push('--cookies-from-browser', options.cookiesFromBrowser);
      }

      const { command, args } = this.getArenaCommand('process', cmdArgs);
      this.runCommand(command, args, resolve, reject, onProgress, onError);
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

      const cmdArgs = [options.videoPath, '-o', options.outputFile];

      if (options.clipCount) {
        cmdArgs.push('-n', options.clipCount.toString());
      }
      if (options.minDuration) {
        cmdArgs.push('--min', options.minDuration.toString());
      }
      if (options.maxDuration) {
        cmdArgs.push('--max', options.maxDuration.toString());
      }
      if (options.editorialModel) {
        cmdArgs.push('--editorial-model', options.editorialModel);
      }
      if (options.transcriptPath) {
        cmdArgs.push('--transcript', options.transcriptPath);
      }
      if (options.sceneDetection) {
        cmdArgs.push('--scene-detection');
      }

      const { command, args } = this.getArenaCommand('analyze', cmdArgs);
      this.runCommand(command, args, resolve, reject, onProgress, onError);
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

      const cmdArgs = [options.videoPath, '-o', options.outputFile];

      if (options.noCache) {
        cmdArgs.push('--no-cache');
      }
      if (options.cookiesFromBrowser) {
        cmdArgs.push('--cookies-from-browser', options.cookiesFromBrowser);
      }

      const { command, args } = this.getArenaCommand('transcribe', cmdArgs);
      this.runCommand(command, args, resolve, reject, onProgress, onError);
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

      const cmdArgs = [options.videoPath, options.analysisPath, '-o', options.outputDir];

      if (options.clipCount) {
        cmdArgs.push('-n', options.clipCount.toString());
      }
      if (options.selectedIndices && options.selectedIndices.length > 0) {
        cmdArgs.push('--select', options.selectedIndices.join(','));
      }
      if (options.fast) {
        cmdArgs.push('--fast');
      }
      if (options.padding !== undefined) {
        cmdArgs.push('--padding', options.padding.toString());
      }

      const { command, args } = this.getArenaCommand('generate', cmdArgs);
      this.runCommand(command, args, resolve, reject, onProgress, onError);
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

      const cmdArgs = [options.videoPath, '-o', options.outputFile, '--format', options.format];

      if (options.bitrate) {
        cmdArgs.push('--bitrate', options.bitrate);
      }
      if (options.sampleRate) {
        cmdArgs.push('--sample-rate', options.sampleRate.toString());
      }
      if (options.mono) {
        cmdArgs.push('--mono');
      }
      if (options.cookiesFromBrowser) {
        cmdArgs.push('--cookies-from-browser', options.cookiesFromBrowser);
      }

      const { command, args } = this.getArenaCommand('extract-audio', cmdArgs);
      this.runCommand(command, args, resolve, reject, onProgress, onError);
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
    const isPackaged = typeof (process as any).pkg !== 'undefined';
    const binDir = path.join(getArenaHome(), 'bin');
    const managedBinDir = getActiveBinDir();
    const hasManagedRuntime = fs.existsSync(getActivePythonPath());

    // Put the runtime's console scripts (including yt-dlp) on PATH. Standalone
    // builds use ~/.arena/bin for their extracted sidecars.
    const updatedPath = isPackaged
      ? prependPath(process.env.PATH, binDir)
      : hasManagedRuntime
        ? prependPath(process.env.PATH, managedBinDir)
        : process.env.PATH || '';

    // Windows-specific spawn options to avoid job object errors
    const spawnOptions: any = {
      cwd: isPackaged ? binDir : (this.enginePath ?? process.cwd()),
      env: {
        ...process.env,
        ...(isPackaged || hasManagedRuntime ? { PATH: updatedPath } : {}),
      },
    };

    // Fix for Windows "AssignProcessToJobObject" error
    // This error occurs when the parent process is already in a job object
    if (process.platform === 'win32') {
      // Don't create a new window console
      spawnOptions.windowsHide = true;
      // Create new process group to avoid job object assignment
      spawnOptions.detached = true;
      // Use shell to ensure proper process handling
      spawnOptions.shell = false;
      // Enable UTF-8 encoding for Python output (emoji support)
      spawnOptions.env.PYTHONUTF8 = '1';
      spawnOptions.env.PYTHONIOENCODING = 'utf-8';
    }

    const pythonProcess = spawn(arenaCliPath, args, spawnOptions);

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
          } catch {
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
          'Run "arena setup --force" to repair the Arena runtime'
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
      const cmdArgs = [
        options.inputPath,
        '--output',
        options.outputDir,
        '--platform',
        options.platform,
      ];

      if (options.cropStrategy) {
        cmdArgs.push('--crop', options.cropStrategy);
      }

      if (options.padStrategy) {
        cmdArgs.push('--pad', options.padStrategy);
      }

      if (options.padColor) {
        cmdArgs.push('--pad-color', options.padColor);
      }

      if (options.maintainQuality === false) {
        cmdArgs.push('--no-quality');
      }

      if (options.captions) {
        cmdArgs.push('--captions', options.captions);
      }
      if (options.captionFontSize) {
        cmdArgs.push('--caption-font-size', options.captionFontSize.toString());
      }
      if (options.captionColor) {
        cmdArgs.push('--caption-color', options.captionColor);
      }
      if (options.captionPosition) {
        cmdArgs.push('--caption-position', options.captionPosition);
      }

      const { command, args } = this.getArenaCommand('format', cmdArgs);
      this.runCommand(command, args, resolve, reject, onProgress, onError);
    });
  }

  async runDetectScenes(
    options: DetectScenesOptions,
    onProgress?: (update: ProgressUpdate) => void,
    onError?: (error: string) => void
  ): Promise<any> {
    return new Promise((resolve, reject) => {
      if (this.isShuttingDown) {
        reject(new SystemError('INTERRUPTED', 'Process was interrupted by user'));
        return;
      }

      const cmdArgs = [options.videoPath, '-o', options.outputFile];

      if (options.threshold !== undefined) {
        cmdArgs.push('--threshold', options.threshold.toString());
      }
      if (options.minSceneDuration !== undefined) {
        cmdArgs.push('--min-duration', options.minSceneDuration.toString());
      }
      if (options.generateReport) {
        cmdArgs.push('--report');
      }

      const { command, args } = this.getArenaCommand('detect-scenes', cmdArgs);
      this.runCommand(command, args, resolve, reject, onProgress, onError);
    });
  }

  async checkPythonEnvironment(): Promise<{
    available: boolean;
    version?: string;
    error?: string;
  }> {
    const isPackaged = typeof (process as any).pkg !== 'undefined';
    if (isPackaged) {
      return { available: true, version: 'Bundled Python Engine (PyInstaller)' };
    }

    return new Promise((resolve) => {
      const managedPython = getActivePythonPath();
      const pythonCmd = fs.existsSync(managedPython)
        ? managedPython
        : process.platform === 'win32'
          ? 'python'
          : 'python3';

      // Windows-specific spawn options to avoid job object errors
      const spawnOptions: any = {};
      if (process.platform === 'win32') {
        spawnOptions.windowsHide = true;
        spawnOptions.detached = true;
        spawnOptions.shell = false;
      }

      const pythonProcess = spawn(pythonCmd, ['--version'], spawnOptions);

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
            error: 'Arena runtime is unavailable; run "arena setup"',
          });
        }
      });

      pythonProcess.on('error', () => {
        resolve({
          available: false,
          error: 'Arena runtime is unavailable; run "arena setup"',
        });
      });
    });
  }

  async checkDependencies(): Promise<{ installed: boolean; missing?: string[] }> {
    const isPackaged = typeof (process as any).pkg !== 'undefined';
    if (isPackaged) {
      return { installed: true };
    }

    return new Promise((resolve) => {
      const managedPython = getActivePythonPath();
      const pythonCmd = fs.existsSync(managedPython)
        ? managedPython
        : process.platform === 'win32'
          ? 'python'
          : 'python3';

      // Windows-specific spawn options to avoid job object errors
      const spawnOptions: any = {
        cwd: this.enginePath ?? process.cwd(),
        env: {
          ...process.env,
          ...(this.enginePath ? { PYTHONPATH: this.enginePath } : {}),
        },
      };

      if (process.platform === 'win32') {
        spawnOptions.windowsHide = true;
        spawnOptions.detached = true;
        spawnOptions.shell = false;
      }

      const pythonProcess = spawn(pythonCmd, ['-c', 'import arena; print("ok")'], spawnOptions);

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
