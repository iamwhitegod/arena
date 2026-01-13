import { spawn, ChildProcess } from 'child_process';
import path from 'path';
import chalk from 'chalk';

export interface ProcessOptions {
  videoPath: string;
  outputDir: string;
  minDuration?: number;
  maxDuration?: number;
  clipCount?: number;
}

export interface ProgressUpdate {
  stage: string;
  progress: number;
  message: string;
}

export class PythonBridge {
  private enginePath: string;

  constructor() {
    // Path to the Python engine (relative to CLI directory)
    this.enginePath = path.join(__dirname, '../../../engine');
  }

  async runProcess(
    options: ProcessOptions,
    onProgress?: (update: ProgressUpdate) => void,
    onError?: (error: string) => void
  ): Promise<any> {
    return new Promise((resolve, reject) => {
      const args = [
        '-m',
        'arena.main',
        'process',
        options.videoPath,
        '--output-dir',
        options.outputDir,
      ];

      if (options.minDuration) {
        args.push('--min-duration', options.minDuration.toString());
      }
      if (options.maxDuration) {
        args.push('--max-duration', options.maxDuration.toString());
      }
      if (options.clipCount) {
        args.push('--clip-count', options.clipCount.toString());
      }

      const pythonProcess = spawn('python3', args, {
        cwd: this.enginePath,
        env: { ...process.env, PYTHONPATH: this.enginePath },
      });

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
        if (code === 0) {
          resolve({ success: true });
        } else {
          reject(
            new Error(`Python process exited with code ${code}\n${errorBuffer}`)
          );
        }
      });

      pythonProcess.on('error', (error: Error) => {
        reject(new Error(`Failed to start Python process: ${error.message}`));
      });
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
