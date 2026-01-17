/**
 * Input validation utilities for Arena CLI
 * Validates user inputs before processing
 */

import fs from 'fs-extra';
import path from 'path';
import { spawn } from 'child_process';
import { PreflightError } from '../errors/index.js';

/**
 * Validate video file exists and is readable
 */
export async function validateVideoFile(videoPath: string): Promise<void> {
  const absolutePath = path.resolve(videoPath);

  // Check if file exists
  if (!(await fs.pathExists(absolutePath))) {
    throw new PreflightError(
      'VIDEO_NOT_FOUND',
      `Video file not found: ${videoPath}`,
      `Check the file path and try again:\n    arena process ${chalk.cyan('<correct-path>')}`
    );
  }

  // Check if it's a file (not directory)
  const stats = await fs.stat(absolutePath);
  if (!stats.isFile()) {
    throw new PreflightError(
      'INVALID_VIDEO_FORMAT',
      `Path is not a file: ${videoPath}`,
      'Provide a path to a video file, not a directory'
    );
  }

  // Check if file is readable
  try {
    await fs.access(absolutePath, fs.constants.R_OK);
  } catch {
    throw new PreflightError(
      'VIDEO_NOT_READABLE',
      `Cannot read video file: ${videoPath}`,
      'Check file permissions: chmod +r <file>'
    );
  }

  // Basic video format validation (by extension)
  const validExtensions = ['.mp4', '.mov', '.avi', '.mkv', '.webm', '.flv', '.m4v'];
  const ext = path.extname(absolutePath).toLowerCase();

  if (!validExtensions.includes(ext)) {
    throw new PreflightError(
      'INVALID_VIDEO_FORMAT',
      `Unsupported video format: ${ext}`,
      `Supported formats: ${validExtensions.join(', ')}`
    );
  }
}

/**
 * Validate output directory is writable
 * Creates directory if it doesn't exist
 */
export async function validateOutputDir(outputDir: string): Promise<void> {
  const absolutePath = path.resolve(outputDir);

  // Try to create directory if it doesn't exist
  try {
    await fs.ensureDir(absolutePath);
  } catch (error) {
    throw new PreflightError(
      'OUTPUT_DIR_NOT_WRITABLE',
      `Cannot create output directory: ${outputDir}`,
      `Check parent directory permissions: ls -ld ${path.dirname(absolutePath)}`
    );
  }

  // Check if directory is writable
  try {
    await fs.access(absolutePath, fs.constants.W_OK);
  } catch {
    throw new PreflightError(
      'OUTPUT_DIR_NOT_WRITABLE',
      `Output directory is not writable: ${outputDir}`,
      `Fix permissions: chmod +w ${absolutePath}`
    );
  }
}

/**
 * Validate numeric option is within range
 */
export function validateNumericOption(
  value: string | undefined,
  optionName: string,
  min?: number,
  max?: number
): number | undefined {
  if (value === undefined) {
    return undefined;
  }

  const num = parseFloat(value);

  if (isNaN(num)) {
    throw new PreflightError(
      'INVALID_OPTION',
      `Invalid value for --${optionName}: ${value}`,
      `Provide a valid number: --${optionName} <number>`
    );
  }

  if (min !== undefined && num < min) {
    throw new PreflightError(
      'INVALID_OPTION',
      `Value for --${optionName} must be at least ${min}, got ${num}`,
      `Use a value >= ${min}: --${optionName} ${min}`
    );
  }

  if (max !== undefined && num > max) {
    throw new PreflightError(
      'INVALID_OPTION',
      `Value for --${optionName} must be at most ${max}, got ${num}`,
      `Use a value <= ${max}: --${optionName} ${max}`
    );
  }

  return num;
}

/**
 * Validate OpenAI API key is present
 */
export function validateApiKey(): void {
  const apiKey = process.env.OPENAI_API_KEY;

  if (!apiKey) {
    throw new PreflightError(
      'API_KEY_MISSING',
      'OpenAI API key not found',
      undefined,
      'https://platform.openai.com/api-keys'
    );
  }

  // Basic format validation (should start with sk-)
  if (!apiKey.startsWith('sk-')) {
    throw new PreflightError(
      'API_KEY_INVALID',
      'OpenAI API key has invalid format',
      'API keys should start with "sk-"',
      'https://platform.openai.com/api-keys'
    );
  }

  // Check minimum length (OpenAI keys are typically 51 chars)
  if (apiKey.length < 40) {
    throw new PreflightError(
      'API_KEY_INVALID',
      'OpenAI API key appears to be incomplete',
      'Check that you copied the full key',
      'https://platform.openai.com/api-keys'
    );
  }
}

/**
 * Validate Python is installed and accessible
 */
export async function validatePython(): Promise<string> {
  return new Promise((resolve, reject) => {
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
        // Extract version
        const versionMatch = output.match(/Python (\d+)\.(\d+)\.(\d+)/);
        if (versionMatch) {
          const [, major, minor] = versionMatch.map(Number);

          // Check minimum version (Python 3.9+)
          if (major < 3 || (major === 3 && minor < 9)) {
            reject(
              new PreflightError(
                'PYTHON_VERSION_TOO_OLD',
                `Python 3.9 or higher is required, found Python ${major}.${minor}`,
                'Upgrade Python: brew install python3 (macOS) or apt install python3 (Ubuntu)'
              )
            );
            return;
          }

          resolve(output.trim());
        } else {
          resolve(output.trim());
        }
      } else {
        reject(
          new PreflightError(
            'PYTHON_NOT_FOUND',
            'Python 3 is not installed or not in PATH',
            undefined,
            'https://www.python.org/downloads/'
          )
        );
      }
    });

    pythonProcess.on('error', () => {
      reject(
        new PreflightError(
          'PYTHON_NOT_FOUND',
          'Python 3 is not installed or not in PATH',
          undefined,
          'https://www.python.org/downloads/'
        )
      );
    });
  });
}

/**
 * Validate Python dependencies are installed
 */
export async function validateDependencies(enginePath: string): Promise<void> {
  return new Promise((resolve, reject) => {
    const pythonProcess = spawn('python3', ['-c', 'import arena; print("ok")'], {
      cwd: enginePath,
      env: { ...process.env, PYTHONPATH: enginePath },
    });

    let output = '';

    pythonProcess.stdout.on('data', (data: Buffer) => {
      output += data.toString();
    });

    pythonProcess.on('close', (code: number) => {
      if (code === 0 && output.includes('ok')) {
        resolve();
      } else {
        reject(
          new PreflightError(
            'DEPENDENCIES_MISSING',
            'Python dependencies are not installed',
            undefined,
            'https://github.com/YOUR_USERNAME/arena#installation'
          )
        );
      }
    });

    pythonProcess.on('error', () => {
      reject(
        new PreflightError(
          'DEPENDENCIES_MISSING',
          'Failed to check Python dependencies',
          'Ensure Python and pip are properly installed'
        )
      );
    });
  });
}

/**
 * Validate duration range makes sense
 */
export function validateDurationRange(min?: number, max?: number): void {
  if (min !== undefined && max !== undefined && min >= max) {
    throw new PreflightError(
      'INVALID_OPTION',
      `Minimum duration (${min}s) must be less than maximum duration (${max}s)`,
      `Example: --min 20 --max 60`
    );
  }
}

// Import chalk at the top after ensuring it's available
import chalk from 'chalk';
