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
import { validateOllamaReadiness } from './ollama.js';
import { validateLocalReadiness } from './local.js';
import {
  providerSupportsCapability,
  SUPPORTED_PROVIDERS,
  type ProviderName,
  type RequiredProviderBinding,
} from './providers.js';

export interface PreflightOptions {
  videoPath: string;
  outputDir: string;
  numClips?: string;
  minDuration?: string;
  maxDuration?: string;
  padding?: string;
  skipApiKeyCheck?: boolean;
  requiredProviders?: string[];
  requiredProviderBindings?: RequiredProviderBinding[];
  enginePath?: string;
}

export interface PreflightResult {
  passed: boolean;
  errors: PreflightError[];
  warnings: string[];
  pythonVersion?: string;
}

function providerError(options: PreflightOptions): PreflightError | undefined {
  const required = [
    ...(options.requiredProviders || ['openai']),
    ...(options.requiredProviderBindings || []).map((binding) => binding.provider),
  ];
  const unsupported = required.find(
    (provider) => !SUPPORTED_PROVIDERS.includes(provider as (typeof SUPPORTED_PROVIDERS)[number])
  );
  if (unsupported) {
    return new PreflightError(
      'UNSUPPORTED_PROVIDER',
      `Unsupported inference provider: ${unsupported}`,
      `Supported providers: ${SUPPORTED_PROVIDERS.join(', ')}`
    );
  }

  const unsupportedBinding = options.requiredProviderBindings?.find(
    (binding) => !providerSupportsCapability(binding.provider as ProviderName, binding.capability)
  );
  if (unsupportedBinding) {
    const flag =
      unsupportedBinding.capability === 'transcription'
        ? '--transcription-provider local'
        : `--${unsupportedBinding.capability}-provider openai`;
    return new PreflightError(
      'PROVIDER_CAPABILITY_UNSUPPORTED',
      `Provider '${unsupportedBinding.provider}' does not support ${unsupportedBinding.capability}`,
      `Select a supported provider for that capability, for example: ${flag}`
    );
  }
  return undefined;
}

function shouldValidateOpenAI(options: PreflightOptions): boolean {
  const providers = options.requiredProviderBindings?.length
    ? options.requiredProviderBindings.map((binding) => binding.provider)
    : options.requiredProviders || ['openai'];
  return !options.skipApiKeyCheck && providers.includes('openai');
}

function requiredOllamaModels(options: PreflightOptions): string[] {
  return (options.requiredProviderBindings || [])
    .filter((binding) => binding.provider === 'ollama' && binding.model)
    .map((binding) => binding.model as string);
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

  const providerValidationError = providerError(options);
  if (providerValidationError) errors.push(providerValidationError);

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
  if (shouldValidateOpenAI(options)) {
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

  const ollamaModels = requiredOllamaModels(options);
  if (!providerValidationError && ollamaModels.length > 0) {
    try {
      await validateOllamaReadiness(ollamaModels);
    } catch (error) {
      if (error instanceof PreflightError) {
        errors.push(error);
      }
    }
  }

  if (!providerValidationError && pythonVersion) {
    try {
      await validateLocalReadiness(options.requiredProviderBindings || []);
    } catch (error) {
      if (error instanceof PreflightError) errors.push(error);
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

  const unsupportedProvider = providerError(options);
  if (unsupportedProvider) {
    spinner.fail(chalk.red('Provider validation failed'));
    return { passed: false, errors: [unsupportedProvider], warnings: [] };
  }

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

  const ollamaModels = requiredOllamaModels(options);
  if (ollamaModels.length > 0) {
    spinner.text = 'Checking Ollama and required models...';
    try {
      await validateOllamaReadiness(ollamaModels);
    } catch (error) {
      spinner.fail(chalk.red('Ollama readiness check failed'));
      if (error instanceof PreflightError) {
        return {
          passed: false,
          errors: [error],
          warnings: [],
          pythonVersion,
        };
      }
    }
  }

  if ((options.requiredProviderBindings || []).some((binding) => binding.provider === 'local')) {
    spinner.text = 'Checking local inference runtimes and verified models...';
    try {
      await validateLocalReadiness(options.requiredProviderBindings || []);
    } catch (error) {
      spinner.fail(chalk.red('Local inference readiness check failed'));
      if (error instanceof PreflightError) {
        return { passed: false, errors: [error], warnings: [], pythonVersion };
      }
    }
  }

  // API key check (optional)
  if (shouldValidateOpenAI(options)) {
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
