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
import {
  requiredProviders,
  type ProviderCapability,
  type ProviderSelectors,
} from '../core/providers.js';

const PYTHON_ENV_ALLOWLIST = [
  'APPDATA',
  'COMSPEC',
  'HOME',
  'LANG',
  'LC_ALL',
  'LC_CTYPE',
  'LOCALAPPDATA',
  'PATHEXT',
  'SSL_CERT_DIR',
  'SSL_CERT_FILE',
  'SYSTEMROOT',
  'TEMP',
  'TMP',
  'TMPDIR',
  'TZ',
  'USERPROFILE',
  'WINDIR',
  'XDG_CACHE_HOME',
  'XDG_CONFIG_HOME',
] as const;

const PROVIDER_CREDENTIAL_ENV: Readonly<Record<string, readonly string[]>> = {
  openai: ['OPENAI_API_KEY'],
};

function pythonChildEnvironment(
  pathValue: string,
  providerNames: readonly string[] = [],
  extra: NodeJS.ProcessEnv = {}
): NodeJS.ProcessEnv {
  const env: NodeJS.ProcessEnv = {
    ARENA_MODEL_ROOT: path.join(getArenaHome(), 'models'),
    PATH: pathValue,
    PYTHONIOENCODING: 'utf-8',
    PYTHONUNBUFFERED: '1',
    PYTHONUTF8: '1',
  };
  for (const key of PYTHON_ENV_ALLOWLIST) {
    if (process.env[key] !== undefined) env[key] = process.env[key];
  }
  for (const provider of new Set(providerNames)) {
    for (const key of PROVIDER_CREDENTIAL_ENV[provider] || []) {
      if (process.env[key] !== undefined) env[key] = process.env[key];
    }
  }
  return { ...env, ...extra };
}

function providersFor(selectors: ProviderSelectors, capabilities: ProviderCapability[]): string[] {
  return requiredProviders(selectors, capabilities);
}

export interface ProcessOptions extends ProviderSelectors {
  videoPath: string;
  outputDir: string;
  minDuration?: number;
  maxDuration?: number;
  clipCount?: number;
  editorialModel?: string;
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

export interface AnalyzeOptions extends ProviderSelectors {
  videoPath: string;
  outputFile: string;
  minDuration?: number;
  maxDuration?: number;
  clipCount?: number;
  editorialModel?: string;
  transcriptPath?: string;
  sceneDetection?: boolean;
}

export interface TranscribeOptions extends ProviderSelectors {
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
  progress: number | null;
  message: string;
}

function appendProviderArgs(args: string[], selectors: ProviderSelectors): void {
  const values: Array<[string, string | undefined]> = [
    ['--provider', selectors.provider],
    ['--chat-provider', selectors.chatProvider],
    ['--chat-model', selectors.chatModel],
    ['--overview-chat-provider', selectors.overviewChatProvider],
    ['--overview-chat-model', selectors.overviewChatModel],
    ['--embedding-provider', selectors.embeddingProvider],
    ['--embedding-model', selectors.embeddingModel],
    ['--transcription-provider', selectors.transcriptionProvider],
    ['--transcription-model', selectors.transcriptionModel],
  ];
  for (const [flag, value] of values) {
    if (value) args.push(flag, value);
  }
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
      appendProviderArgs(cmdArgs, options);
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
      this.runCommand(
        command,
        args,
        resolve,
        reject,
        onProgress,
        onError,
        providersFor(options, ['chat', 'overviewChat', 'embedding', 'transcription'])
      );
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
      appendProviderArgs(cmdArgs, options);

      const { command, args } = this.getArenaCommand('analyze', cmdArgs);
      this.runCommand(
        command,
        args,
        resolve,
        reject,
        onProgress,
        onError,
        providersFor(
          options,
          options.transcriptPath
            ? ['chat', 'overviewChat', 'embedding']
            : ['chat', 'overviewChat', 'embedding', 'transcription']
        )
      );
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
      appendProviderArgs(cmdArgs, {
        provider: options.provider,
        transcriptionProvider: options.transcriptionProvider,
        transcriptionModel: options.transcriptionModel,
      });

      const { command, args } = this.getArenaCommand('transcribe', cmdArgs);
      this.runCommand(
        command,
        args,
        resolve,
        reject,
        onProgress,
        onError,
        providersFor(options, ['transcription'])
      );
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
    onError?: (error: string) => void,
    providerNames: readonly string[] = []
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
      env: pythonChildEnvironment(updatedPath, providerNames),
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
    }

    const pythonProcess = spawn(arenaCliPath, args, spawnOptions);

    // Store process for shutdown handling
    this.currentProcess = pythonProcess;

    let outputBuffer = '';
    let errorBuffer = '';
    let diagnosticOutput = '';
    let commandResult: any = { success: true };

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
                progress: typeof update.progress === 'number' ? update.progress : null,
                message: update.message,
              });
            } else if (update.type === 'result') {
              commandResult = update.data;
            }
          } catch {
            // Human-readable engine output is intentionally hidden here. The
            // Node CLI owns presentation; stderr is retained for failures.
            diagnosticOutput += `${line}\n`;
          }
        } else if (line.trim()) {
          diagnosticOutput += `${line}\n`;
        }
      }
    });

    pythonProcess.stderr.on('data', (data: Buffer) => {
      const text = data.toString();
      errorBuffer += text;
    });

    pythonProcess.on('close', (code: number) => {
      // Clear current process
      this.currentProcess = null;

      if (code === 0) {
        resolve(commandResult);
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
        const diagnostics = `${errorBuffer}\n${diagnosticOutput}`.trim();
        // Parse error from Python output
        const errorMessage = this.parseErrorFromOutput(diagnostics);
        if (onError && errorMessage) {
          onError(errorMessage);
        }
        const isTimeout = /\[timeout;/i.test(errorMessage);
        const isResourceLimit = /\[local_resource_limit;/i.test(errorMessage);
        const timeoutSuggestion = /^Transcription failed/i.test(errorMessage)
          ? 'Retry once; if it repeats, use a faster transcription model or --transcription-provider openai'
          : /^Analysis failed/i.test(errorMessage)
            ? 'Retry with fewer clips, install a faster local model pack, or use --chat-provider openai'
            : 'Retry once; if it repeats, move the timed-out capability to a faster model or cloud provider';

        reject(
          new ProcessingError(
            isTimeout ? 'TIMEOUT' : isResourceLimit ? 'LOCAL_RESOURCE_LIMIT' : 'PROCESSING_FAILED',
            errorMessage || `Processing failed with exit code ${code}`,
            isTimeout
              ? timeoutSuggestion
              : isResourceLimit
                ? 'Close memory-intensive apps, use the lite model pack, or move one capability to a cloud provider'
                : 'Run again with --debug for CLI stack details'
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
    const lines = errorOutput
      .trim()
      .split(/[\r\n]+/)
      .map((line) => line.trim())
      .filter(Boolean);

    // Arena's public error contract is already sanitized and includes a
    // stable code plus a correlation reference. Prefer it over native model
    // diagnostics and terminal progress lines captured from stderr.
    for (const line of lines) {
      const marker = line.indexOf('❌');
      if (
        marker >= 0 &&
        /\[[a-z0-9_-]+;\s*retryable=(?:true|false);\s*ref=[a-z0-9]+\]:/i.test(line)
      ) {
        return line.slice(marker + 1).trim();
      }
    }

    // Look for common error patterns
    for (const line of lines) {
      if (line.includes('Error:') || line.includes('Exception:')) {
        return line.trim();
      }
    }

    // Return last non-empty line as error
    for (let i = lines.length - 1; i >= 0; i--) {
      const line = lines[i];
      if (line && !line.startsWith('File ') && !line.includes('%|') && !line.startsWith('ggml_')) {
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
      const spawnOptions: any = {
        env: pythonChildEnvironment(process.env.PATH || ''),
      };
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
        env: pythonChildEnvironment(
          process.env.PATH || '',
          [],
          this.enginePath ? { PYTHONPATH: this.enginePath } : {}
        ),
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
