/**
 * Formatting utilities for Arena CLI
 * Formats durations, costs, file sizes, etc. for display
 */

/**
 * Format duration in seconds to human-readable string
 * Examples: "45s", "2m 30s", "1h 15m 30s"
 */
export function formatDuration(seconds: number): string {
  if (seconds < 60) {
    return `${Math.round(seconds)}s`;
  }

  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  const secs = Math.round(seconds % 60);

  if (hours > 0) {
    if (secs > 0) {
      return `${hours}h ${minutes}m ${secs}s`;
    }
    return `${hours}h ${minutes}m`;
  }

  if (secs > 0) {
    return `${minutes}m ${secs}s`;
  }

  return `${minutes}m`;
}

/**
 * Format duration in seconds to compact string
 * Examples: "45s", "2:30", "1:15:30"
 */
export function formatDurationCompact(seconds: number): string {
  if (seconds < 60) {
    return `${Math.round(seconds)}s`;
  }

  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  const secs = Math.round(seconds % 60);

  if (hours > 0) {
    return `${hours}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  }

  return `${minutes}:${secs.toString().padStart(2, '0')}`;
}

/**
 * Format cost in dollars
 * Examples: "$0.19", "$1.50", "$12.34"
 */
export function formatCost(dollars: number): string {
  return `$${dollars.toFixed(2)}`;
}

/**
 * Format percentage
 * Examples: "7.5%", "85.3%", "100%"
 */
export function formatPercentage(value: number, decimals = 1): string {
  return `${(value * 100).toFixed(decimals)}%`;
}

/**
 * Format file size in bytes to human-readable string
 * Examples: "1.5 MB", "245 KB", "3.2 GB"
 */
export function formatFileSize(bytes: number): string {
  const units = ['B', 'KB', 'MB', 'GB', 'TB'];
  let size = bytes;
  let unitIndex = 0;

  while (size >= 1024 && unitIndex < units.length - 1) {
    size /= 1024;
    unitIndex++;
  }

  if (unitIndex === 0) {
    return `${size} ${units[unitIndex]}`;
  }

  return `${size.toFixed(1)} ${units[unitIndex]}`;
}

/**
 * Format timestamp to readable string
 * Examples: "2:30 - 3:15", "0:45 - 1:20"
 */
export function formatTimeRange(startSeconds: number, endSeconds: number): string {
  return `${formatDurationCompact(startSeconds)} - ${formatDurationCompact(endSeconds)}`;
}

/**
 * Format a list of items with bullets
 */
export function formatList(items: string[], indent = '  '): string {
  return items.map((item) => `${indent}• ${item}`).join('\n');
}

/**
 * Format a number with thousands separator
 * Examples: "1,234", "1,234,567"
 */
export function formatNumber(num: number): string {
  return num.toLocaleString('en-US');
}

/**
 * Truncate string to max length with ellipsis
 */
export function truncate(str: string, maxLength: number): string {
  if (str.length <= maxLength) {
    return str;
  }
  return str.substring(0, maxLength - 3) + '...';
}

/**
 * Pad string to specific length (useful for alignment)
 */
export function padRight(str: string, length: number, char = ' '): string {
  return str.padEnd(length, char);
}

/**
 * Format progress bar
 * Example: "[████████░░] 80%"
 */
export function formatProgressBar(progress: number, width = 10): string {
  const filled = Math.round(progress * width);
  const empty = width - filled;
  const bar = '█'.repeat(filled) + '░'.repeat(empty);
  return `[${bar}] ${formatPercentage(progress, 0)}`;
}

/**
 * Format clip title from snake_case to Title Case
 * Example: "how-to-learn-programming" → "How To Learn Programming"
 */
export function formatClipTitle(slug: string): string {
  return slug
    .split(/[-_]/)
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
    .join(' ');
}

/**
 * Format rate (items per second/minute)
 */
export function formatRate(count: number, seconds: number, unit: 'second' | 'minute' = 'second'): string {
  const divisor = unit === 'minute' ? 60 : 1;
  const rate = count / (seconds / divisor);
  return `${rate.toFixed(1)}/${unit === 'minute' ? 'min' : 's'}`;
}
