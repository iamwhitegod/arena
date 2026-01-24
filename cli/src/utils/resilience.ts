/**
 * Resilience utilities - Retry logic, timeouts, and error recovery
 */

import { exec, spawn } from 'child_process';
import { promisify } from 'util';

const execAsync = promisify(exec);

export interface RetryOptions {
  maxAttempts?: number;
  delayMs?: number;
  backoffMultiplier?: number;
  timeoutMs?: number;
  onRetry?: (attempt: number, error: Error) => void;
}

export interface ExecResult {
  stdout: string;
  stderr: string;
}

/**
 * Retry a function with exponential backoff
 */
export async function retryWithBackoff<T>(
  fn: () => Promise<T>,
  options: RetryOptions = {}
): Promise<T> {
  const {
    maxAttempts = 3,
    delayMs = 1000,
    backoffMultiplier = 2,
    timeoutMs = 30000,
    onRetry,
  } = options;

  let lastError: Error | undefined;

  for (let attempt = 1; attempt <= maxAttempts; attempt++) {
    try {
      // Add timeout to the operation
      return await withTimeout(fn(), timeoutMs);
    } catch (error) {
      lastError = error as Error;

      // Don't retry on last attempt
      if (attempt === maxAttempts) {
        break;
      }

      // Call retry callback if provided
      if (onRetry) {
        onRetry(attempt, lastError);
      }

      // Calculate delay with exponential backoff
      const delay = delayMs * Math.pow(backoffMultiplier, attempt - 1);
      await sleep(delay);
    }
  }

  throw lastError;
}

/**
 * Add timeout to a promise
 */
export async function withTimeout<T>(promise: Promise<T>, timeoutMs: number): Promise<T> {
  return Promise.race([
    promise,
    new Promise<T>((_, reject) =>
      setTimeout(() => reject(new Error(`Operation timed out after ${timeoutMs}ms`)), timeoutMs)
    ),
  ]);
}

/**
 * Sleep for specified milliseconds
 */
export function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

/**
 * Execute command with retry and timeout
 */
export async function execWithRetry(
  command: string,
  options: RetryOptions = {}
): Promise<ExecResult> {
  return retryWithBackoff(
    async () => {
      try {
        return await execAsync(command);
      } catch (error: unknown) {
        const err = error as { code?: number; stderr?: string; stdout?: string };
        // Don't retry on certain error codes (command not found, etc.)
        if (err.code === 127) {
          throw error;
        }
        throw error;
      }
    },
    {
      maxAttempts: 3,
      delayMs: 500,
      timeoutMs: 10000,
      ...options,
    }
  );
}

/**
 * Spawn process with better error handling
 */
export function spawnWithErrorHandling(
  command: string,
  args: string[],
  options: {
    shell?: boolean;
    onStdout?: (data: string) => void;
    onStderr?: (data: string) => void;
    onError?: (error: Error) => void;
  } = {}
): Promise<{ code: number; stdout: string; stderr: string }> {
  return new Promise((resolve, reject) => {
    // Build spawn options with Windows-specific settings
    const spawnOptions: {
      stdio: ['inherit', 'pipe', 'pipe'];
      shell?: boolean;
      windowsHide?: boolean;
      detached?: boolean;
    } = {
      stdio: ['inherit', 'pipe', 'pipe'],
      shell: options.shell ?? false,
    };

    // Windows-specific spawn options to avoid job object errors
    if (process.platform === 'win32') {
      spawnOptions.windowsHide = true;
      spawnOptions.detached = true;
      // Keep shell: false for security unless explicitly set
      if (options.shell === undefined) {
        spawnOptions.shell = false;
      }
    }

    const proc = spawn(command, args, spawnOptions);

    let stdout = '';
    let stderr = '';

    proc.stdout?.on('data', (data: Buffer) => {
      const text = data.toString();
      stdout += text;
      if (options.onStdout) {
        options.onStdout(text);
      }
    });

    proc.stderr?.on('data', (data: Buffer) => {
      const text = data.toString();
      stderr += text;
      if (options.onStderr) {
        options.onStderr(text);
      }
    });

    proc.on('error', (error: Error) => {
      if (options.onError) {
        options.onError(error);
      }
      reject(error);
    });

    proc.on('close', (code: number | null) => {
      resolve({ code: code || 0, stdout, stderr });
    });
  });
}

/**
 * Check network connectivity
 */
export async function checkNetworkConnectivity(): Promise<boolean> {
  try {
    // Try to reach OpenAI API
    const { default: fetch } = await import('node-fetch');
    const response = await withTimeout(
      fetch('https://api.openai.com', {
        method: 'HEAD',
        signal: AbortSignal.timeout(5000),
      }),
      5000
    );
    return response.ok || response.status === 401; // 401 means we reached the API
  } catch {
    return false;
  }
}

/**
 * Validate OpenAI API key format
 */
export function validateApiKeyFormat(apiKey: string): boolean {
  // OpenAI keys start with sk- and are typically 48-51 characters
  return /^sk-[a-zA-Z0-9]{20,}$/.test(apiKey);
}

/**
 * Test OpenAI API key
 */
export async function testApiKey(apiKey: string): Promise<{ valid: boolean; error?: string }> {
  try {
    const { default: fetch } = await import('node-fetch');
    const response = await withTimeout(
      fetch('https://api.openai.com/v1/models', {
        method: 'GET',
        headers: {
          Authorization: `Bearer ${apiKey}`,
        },
        signal: AbortSignal.timeout(10000),
      }),
      10000
    );

    if (response.ok) {
      return { valid: true };
    } else if (response.status === 401) {
      return { valid: false, error: 'Invalid API key' };
    } else {
      return { valid: false, error: `HTTP ${response.status}` };
    }
  } catch (error) {
    return { valid: false, error: (error as Error).message };
  }
}

/**
 * Check available disk space
 */
export async function checkDiskSpace(path: string): Promise<{ available: number; total: number }> {
  try {
    if (process.platform === 'win32') {
      // Windows: Use wmic
      const { stdout } = await execAsync(
        `wmic logicaldisk where "DeviceID='${path[0]}:'" get FreeSpace,Size`
      );
      const lines = stdout.trim().split('\n');
      if (lines.length >= 2) {
        const [available, total] = lines[1]
          .trim()
          .split(/\s+/)
          .map((s) => parseInt(s, 10));
        return { available, total };
      }
      // Fallback if parsing fails
      return { available: 0, total: 0 };
    } else {
      // Unix: Use df
      const { stdout } = await execAsync(`df -k "${path}" | tail -1`);
      const parts = stdout.trim().split(/\s+/);
      const available = parseInt(parts[3], 10) * 1024; // Convert KB to bytes
      const total = parseInt(parts[1], 10) * 1024;
      return { available, total };
    }
  } catch {
    // Return dummy values if check fails
    return { available: 0, total: 0 };
  }
}

/**
 * Format bytes to human readable
 */
export function formatBytes(bytes: number): string {
  const units = ['B', 'KB', 'MB', 'GB', 'TB'];
  let size = bytes;
  let unitIndex = 0;

  while (size >= 1024 && unitIndex < units.length - 1) {
    size /= 1024;
    unitIndex++;
  }

  return `${size.toFixed(2)} ${units[unitIndex]}`;
}

/**
 * Detect transient errors that should be retried
 */
export function isTransientError(error: Error): boolean {
  const message = error.message.toLowerCase();
  const transientPatterns = [
    'timeout',
    'timed out',
    'network',
    'econnrefused',
    'econnreset',
    'enotfound',
    'etimedout',
    'socket hang up',
    'rate limit',
    'too many requests',
    '429',
    '500',
    '502',
    '503',
    '504',
  ];

  return transientPatterns.some((pattern) => message.includes(pattern));
}

/**
 * Create user-friendly error message
 */
export function getUserFriendlyError(error: Error): string {
  const message = error.message.toLowerCase();

  if (message.includes('econnrefused') || message.includes('enotfound')) {
    return 'Network connection failed. Check your internet connection.';
  }

  if (message.includes('timeout') || message.includes('timed out')) {
    return 'Operation timed out. Try again or check your network.';
  }

  if (message.includes('eacces') || message.includes('permission denied')) {
    return 'Permission denied. Try running with appropriate permissions.';
  }

  if (message.includes('enospc')) {
    return 'Not enough disk space. Free up some space and try again.';
  }

  if (message.includes('enoent')) {
    return 'File or directory not found.';
  }

  if (message.includes('401') || message.includes('unauthorized')) {
    return 'API authentication failed. Check your API key.';
  }

  if (message.includes('429') || message.includes('rate limit')) {
    return 'API rate limit exceeded. Wait a moment and try again.';
  }

  if (message.includes('500') || message.includes('502') || message.includes('503')) {
    return 'Service temporarily unavailable. Try again in a moment.';
  }

  return error.message;
}
