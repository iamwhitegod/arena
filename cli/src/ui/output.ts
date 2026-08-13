import chalk from 'chalk';
import path from 'path';

export type OutputRow = [label: string, value: string | number | undefined];

export function commandHeader(title: string, rows: OutputRow[] = []): void {
  console.log(`\n${chalk.bold(title)}\n`);
  printRows(rows);
  if (rows.some(([, value]) => value !== undefined)) console.log();
}

export function printRows(rows: OutputRow[]): void {
  const visible = rows.filter(([, value]) => value !== undefined);
  const width = Math.max(0, ...visible.map(([label]) => label.length));
  for (const [label, value] of visible) {
    console.log(`${chalk.gray(label.padEnd(width))}  ${value}`);
  }
}

export function success(title: string, rows: OutputRow[] = []): void {
  console.log(`\n${chalk.green('✓')} ${title}`);
  if (rows.length) {
    console.log();
    printRows(rows);
  }
  console.log();
}

export function warning(message: string): void {
  console.log(`${chalk.yellow('!')} ${message}`);
}

export function displayPath(value: string): string {
  const absolute = path.resolve(value);
  const cwd = process.cwd();
  return absolute.startsWith(`${cwd}${path.sep}`) ? path.relative(cwd, absolute) : absolute;
}
