/**
 * URL detection utility for Arena CLI
 */

export function isUrl(input: string): boolean {
  return input.startsWith('http://') || input.startsWith('https://');
}
