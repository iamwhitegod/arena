/**
 * Pre-flight checks for Arena CLI
 * Runs all validations before starting video processing
 */

import chalk from 'chalk';
import ora from 'ora';
import { PreflightError } from '../errors/index.js';
import {
  validateVideoFile,
  validateOutputDir,
  validateNumericOption,
  validateApiKey,
  validatePython,
  validateDependencies,
  validateDurationRange,
} from '../validation/index.js';

export interface PreflightOptions {
  videoPath: string;
  outputDir: string;
  numClips?: string;
  minDuration?: string;
  maxDuration?: string;
  padding?: string;
  skipApiKeyCheck?: boolean;
  enginePath?: string;
}

export interface PreflightResult {
  passed: boolean;
  errors: PreflightError[];
  warnings: string[];
  pythonVersion?: string;
}

/**
 * Run all pre-flight checks
 * @param options - Options to validate
 * @returns Result with any errors or warnings
 */
export async function runPreflightChecks(options: PreflightOptions): Promise<PreflightResult> {
  const errors: PreflightError[] = [];
  const warnings: string[] = [];
  let pythonVersion: string | undefined;

  // Video file validation
  try {
    await validateVideoFile(options.videoPath);
  } catch (error) {
    if (error instanceof PreflightError) {
      errors.push(error);
    }
  }

  // Output directory validation
  try {
    await validateOutputDir(options.outputDir);
  } catch (error) {
    if (error instanceof PreflightError) {
      errors.push(error);
    }
  }

  // Numeric options validation
  try {
    validateNumericOption(options.numClips, 'num-clips', 1, 100);
  } catch (error) {
    if (error instanceof PreflightError) {
      errors.push(error);
    }
  }

  try {
    const min = validateNumericOption(options.minDuration, 'min', 5, 600);
    const max = validateNumericOption(options.maxDuration, 'max', 10, 1200);
    validateDurationRange(min, max);
  } catch (error) {
    if (error instanceof PreflightError) {
      errors.push(error);
    }
  }

  try {
    validateNumericOption(options.padding, 'padding', 0, 10);
  } catch (error) {
    if (error instanceof PreflightError) {
      errors.push(error);
    }
  }

  // API key validation (optional)
  if (!options.skipApiKeyCheck) {
    try {
      validateApiKey();
    } catch (error) {
      if (error instanceof PreflightError) {
        errors.push(error);
      }
    }
  }

  // Python validation
  try {
    pythonVersion = await validatePython();
  } catch (error) {
    if (error instanceof PreflightError) {
      errors.push(error);
    }
  }

  // Python dependencies validation (only if Python is available and enginePath provided)
  if (pythonVersion && options.enginePath) {
    try {
      await validateDependencies(options.enginePath);
    } catch (error) {
      if (error instanceof PreflightError) {
        errors.push(error);
      }
    }
  }

  return {
    passed: errors.length === 0,
    errors,
    warnings,
    pythonVersion,
  };
}

/**
 * Run pre-flight checks with progress display
 * Shows spinners for each check
 */
export async function runPreflightChecksWithProgress(
  options: PreflightOptions
): Promise<PreflightResult> {
  const spinner = ora();
  spinner.start('Running preflight checks...');

  // Video file check
  spinner.text = 'Validating input...';
  try {
    await validateVideoFile(options.videoPath);
  } catch (error) {
    spinner.fail(chalk.red('Video file validation failed'));
    if (error instanceof PreflightError) {
      return {
        passed: false,
        errors: [error],
        warnings: [],
      };
    }
  }

  // Output directory check
  spinner.text = 'Checking output directory...';
  try {
    await validateOutputDir(options.outputDir);
  } catch (error) {
    spinner.fail(chalk.red('Output directory check failed'));
    if (error instanceof PreflightError) {
      return {
        passed: false,
        errors: [error],
        warnings: [],
      };
    }
  }

  // Python check
  spinner.text = 'Checking processing runtime...';
  let pythonVersion: string | undefined;
  try {
    pythonVersion = await validatePython();
  } catch (error) {
    spinner.fail(chalk.red('Python check failed'));
    if (error instanceof PreflightError) {
      return {
        passed: false,
        errors: [error],
        warnings: [],
      };
    }
  }

  // Dependencies check
  if (options.enginePath) {
    spinner.text = 'Checking engine dependencies...';
    try {
      await validateDependencies(options.enginePath);
    } catch (error) {
      spinner.fail(chalk.red('Dependencies check failed'));
      if (error instanceof PreflightError) {
        return {
          passed: false,
          errors: [error],
          warnings: [],
        };
      }
    }
  }

  // API key check (optional)
  if (!options.skipApiKeyCheck) {
    spinner.text = 'Checking OpenAI API key...';
    try {
      validateApiKey();
    } catch (error) {
      spinner.fail(chalk.red('API key check failed'));
      if (error instanceof PreflightError) {
        return {
          passed: false,
          errors: [error],
          warnings: [],
        };
      }
    }
  }

  // Options validation (silent, no spinner)
  const errors: PreflightError[] = [];
  try {
    validateNumericOption(options.numClips, 'num-clips', 1, 100);
    const min = validateNumericOption(options.minDuration, 'min', 5, 600);
    const max = validateNumericOption(options.maxDuration, 'max', 10, 1200);
    validateDurationRange(min, max);
    validateNumericOption(options.padding, 'padding', 0, 10);
  } catch (error) {
    if (error instanceof PreflightError) {
      errors.push(error);
    }
  }

  if (errors.length > 0) {
    return {
      passed: false,
      errors,
      warnings: [],
      pythonVersion,
    };
  }

  spinner.succeed(chalk.green('Preflight passed'));
  return {
    passed: true,
    errors: [],
    warnings: [],
    pythonVersion,
  };
}
