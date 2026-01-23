/**
 * Logging system for debugging and troubleshooting
 */

import {
  appendFileSync,
  existsSync,
  mkdirSync,
  statSync,
  unlinkSync,
  readdirSync,
  renameSync,
  readFileSync,
} from 'fs';
import { join } from 'path';
import { homedir } from 'os';
import chalk from 'chalk';

export enum LogLevel {
  DEBUG = 0,
  INFO = 1,
  WARN = 2,
  ERROR = 3,
}

export interface LogEntry {
  timestamp: string;
  level: LogLevel;
  message: string;
  context?: Record<string, unknown>;
  error?: {
    name: string;
    message: string;
    stack?: string;
  };
}

class Logger {
  private logDir: string;
  private logFile: string;
  private maxLogSizeMB = 10;
  private maxLogFiles = 5;
  private minLevel: LogLevel = LogLevel.INFO;
  private enableConsole = false;

  constructor() {
    this.logDir = join(homedir(), '.arena', 'logs');
    this.logFile = join(this.logDir, `arena-${this.getDateString()}.log`);
    this.ensureLogDir();
    this.rotateLogsIfNeeded();
  }

  /**
   * Enable debug mode
   */
  enableDebug(enabled = true): void {
    if (enabled) {
      this.minLevel = LogLevel.DEBUG;
      this.enableConsole = true;
    }
  }

  /**
   * Log debug message
   */
  debug(message: string, context?: Record<string, unknown>): void {
    this.log(LogLevel.DEBUG, message, context);
  }

  /**
   * Log info message
   */
  info(message: string, context?: Record<string, unknown>): void {
    this.log(LogLevel.INFO, message, context);
  }

  /**
   * Log warning message
   */
  warn(message: string, context?: Record<string, unknown>): void {
    this.log(LogLevel.WARN, message, context);
  }

  /**
   * Log error message
   */
  error(message: string, error?: Error, context?: Record<string, unknown>): void {
    this.log(LogLevel.ERROR, message, {
      ...context,
      error: error
        ? {
            name: error.name,
            message: error.message,
            stack: error.stack,
          }
        : undefined,
    });
  }

  /**
   * Log with level
   */
  private log(level: LogLevel, message: string, context?: Record<string, unknown>): void {
    if (level < this.minLevel) {
      return;
    }

    const entry: LogEntry = {
      timestamp: new Date().toISOString(),
      level,
      message,
      context,
    };

    // Write to file
    try {
      const logLine = this.formatLogEntry(entry);
      appendFileSync(this.logFile, logLine + '\n', 'utf8');
    } catch {
      // Silently fail if can't write to log file
    }

    // Console output (if enabled)
    if (this.enableConsole) {
      this.logToConsole(entry);
    }
  }

  /**
   * Format log entry as JSON line
   */
  private formatLogEntry(entry: LogEntry): string {
    return JSON.stringify(entry);
  }

  /**
   * Log to console with colors
   */
  private logToConsole(entry: LogEntry): void {
    const levelColors = {
      [LogLevel.DEBUG]: chalk.gray,
      [LogLevel.INFO]: chalk.blue,
      [LogLevel.WARN]: chalk.yellow,
      [LogLevel.ERROR]: chalk.red,
    };

    const levelNames = {
      [LogLevel.DEBUG]: 'DEBUG',
      [LogLevel.INFO]: 'INFO ',
      [LogLevel.WARN]: 'WARN ',
      [LogLevel.ERROR]: 'ERROR',
    };

    const color = levelColors[entry.level];
    const levelName = levelNames[entry.level];
    const time = new Date(entry.timestamp).toLocaleTimeString();

    console.log(color(`[${time}] [${levelName}] ${entry.message}`));

    if (entry.context && Object.keys(entry.context).length > 0) {
      console.log(chalk.gray('  Context:'), entry.context);
    }
  }

  /**
   * Get log file path
   */
  getLogFile(): string {
    return this.logFile;
  }

  /**
   * Get log directory path
   */
  getLogDir(): string {
    return this.logDir;
  }

  /**
   * Ensure log directory exists
   */
  private ensureLogDir(): void {
    try {
      if (!existsSync(this.logDir)) {
        mkdirSync(this.logDir, { recursive: true });
      }
    } catch {
      // Can't create log dir, logs won't be written
    }
  }

  /**
   * Get date string for log file name
   */
  private getDateString(): string {
    const now = new Date();
    const year = now.getFullYear();
    const month = String(now.getMonth() + 1).padStart(2, '0');
    const day = String(now.getDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
  }

  /**
   * Rotate logs if current file is too large
   */
  private rotateLogsIfNeeded(): void {
    try {
      if (!existsSync(this.logFile)) {
        return;
      }

      const stats = statSync(this.logFile);
      const sizeMB = stats.size / (1024 * 1024);

      if (sizeMB > this.maxLogSizeMB) {
        // Rename current log with timestamp
        const timestamp = Date.now();
        const rotatedFile = this.logFile.replace('.log', `-${timestamp}.log`);
        renameSync(this.logFile, rotatedFile);
      }

      // Clean up old logs
      this.cleanupOldLogs();
    } catch {
      // Ignore rotation errors
    }
  }

  /**
   * Remove oldest log files if we have too many
   */
  private cleanupOldLogs(): void {
    try {
      const files = readdirSync(this.logDir)
        .filter((f) => f.startsWith('arena-') && f.endsWith('.log'))
        .map((f) => ({
          name: f,
          path: join(this.logDir, f),
          mtime: statSync(join(this.logDir, f)).mtime.getTime(),
        }))
        .sort((a, b) => b.mtime - a.mtime); // Newest first

      // Keep only maxLogFiles
      const filesToDelete = files.slice(this.maxLogFiles);

      for (const file of filesToDelete) {
        unlinkSync(file.path);
      }
    } catch {
      // Ignore cleanup errors
    }
  }

  /**
   * Read last N lines from current log
   */
  readLastLines(lines = 50): string[] {
    try {
      if (!existsSync(this.logFile)) {
        return [];
      }

      const content = readFileSync(this.logFile, 'utf8');
      const allLines = content.split('\n').filter((line: string) => line.trim());

      return allLines.slice(-lines);
    } catch {
      return [];
    }
  }

  /**
   * Get log statistics
   */
  getStats(): {
    logFile: string;
    sizeMB: number;
    lineCount: number;
    errorCount: number;
    warnCount: number;
  } {
    try {
      const stats = statSync(this.logFile);
      const lines = this.readLastLines(1000);

      return {
        logFile: this.logFile,
        sizeMB: stats.size / (1024 * 1024),
        lineCount: lines.length,
        errorCount: lines.filter((line) => line.includes('"level":3')).length,
        warnCount: lines.filter((line) => line.includes('"level":2')).length,
      };
    } catch {
      return {
        logFile: this.logFile,
        sizeMB: 0,
        lineCount: 0,
        errorCount: 0,
        warnCount: 0,
      };
    }
  }
}

// Export singleton instance
export const logger = new Logger();

/**
 * Log command execution
 */
export function logCommand(command: string, args: Record<string, unknown>): void {
  logger.info(`Command: ${command}`, { args });
}

/**
 * Log command completion
 */
export function logCommandComplete(command: string, durationMs: number): void {
  logger.info(`Command completed: ${command}`, { durationMs });
}

/**
 * Log command failure
 */
export function logCommandError(command: string, error: Error): void {
  logger.error(`Command failed: ${command}`, error);
}
