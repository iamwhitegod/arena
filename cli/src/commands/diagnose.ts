/**
 * Diagnose command - System diagnostics and troubleshooting
 */

import chalk from 'chalk';
import ora from 'ora';
import { spawn } from 'child_process';
import { existsSync, statSync } from 'fs';
import { platform, arch, release, totalmem, freemem } from 'os';
import { join } from 'path';
import {
  checkNetworkConnectivity,
  testApiKey,
  checkDiskSpace,
  formatBytes,
} from '../utils/resilience.js';
import { getArenaHome, readRuntimeManifest } from '../core/runtime.js';

interface DiagnosticResult {
  category: string;
  checks: Array<{
    name: string;
    status: 'pass' | 'fail' | 'warn' | 'info';
    message: string;
    solution?: string;
  }>;
}

interface ProcessResult {
  code: number;
  output: string;
}

function runProcess(command: string, args: string[], timeoutMs = 15000): Promise<ProcessResult> {
  return new Promise((resolve) => {
    const child = spawn(command, args, {
      shell: false,
      windowsHide: true,
      stdio: ['ignore', 'pipe', 'pipe'],
    });
    let output = '';
    let settled = false;
    const finish = (result: ProcessResult) => {
      if (!settled) {
        settled = true;
        clearTimeout(timer);
        resolve(result);
      }
    };
    const timer = setTimeout(() => {
      child.kill();
      finish({ code: 1, output: `${output}\nTimed out` });
    }, timeoutMs);

    child.stdout?.on('data', (data: Buffer) => {
      output += data.toString();
    });
    child.stderr?.on('data', (data: Buffer) => {
      output += data.toString();
    });
    child.once('error', (error: Error) => finish({ code: 1, output: error.message }));
    child.once('close', (code: number | null) => finish({ code: code ?? 1, output }));
  });
}

export async function diagnoseCommand(): Promise<void> {
  console.log(chalk.cyan('\n🔍 ARENA DIAGNOSTICS\n'));
  console.log(chalk.white('Running comprehensive system checks...\n'));

  const results: DiagnosticResult[] = [];

  // 1. System Information
  results.push(await checkSystemInfo());

  // 2. Dependencies Check
  results.push(await checkDependencies());

  // 3. Python Environment
  results.push(await checkPythonEnvironment());

  // 4. Network & API
  results.push(await checkNetworkAndAPI());

  // 5. Disk Space
  results.push(await checkDiskSpaceStatus());

  // 6. Configuration
  results.push(await checkConfiguration());

  // Display results
  console.log(chalk.cyan('\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n'));
  console.log(chalk.bold('DIAGNOSTIC RESULTS\n'));

  let hasErrors = false;
  let hasWarnings = false;

  for (const result of results) {
    console.log(chalk.bold.white(`${result.category}\n`));

    for (const check of result.checks) {
      const icon =
        check.status === 'pass'
          ? chalk.green('✓')
          : check.status === 'fail'
            ? chalk.red('✗')
            : check.status === 'warn'
              ? chalk.yellow('⚠')
              : chalk.blue('ℹ');

      console.log(`${icon} ${check.name}`);
      console.log(chalk.gray(`  ${check.message}`));

      if (check.solution) {
        console.log(chalk.cyan(`  → ${check.solution}`));
      }

      console.log();

      if (check.status === 'fail') hasErrors = true;
      if (check.status === 'warn') hasWarnings = true;
    }
  }

  console.log(chalk.cyan('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n'));

  // Summary
  if (!hasErrors && !hasWarnings) {
    console.log(chalk.green('✓ All checks passed! Arena is ready to use.\n'));
    console.log(chalk.cyan('Try it out:'));
    console.log(chalk.white('  arena process video.mp4 -p tiktok\n'));
  } else if (hasErrors) {
    console.log(chalk.red('✗ Critical issues detected'));
    console.log(chalk.white('Please fix the errors above before using Arena.\n'));
    console.log(chalk.cyan('For help:'));
    console.log(chalk.white('  arena setup   # Install missing dependencies\n'));
  } else {
    console.log(chalk.yellow('⚠ Warnings detected'));
    console.log(chalk.white('Arena should work, but some features may be limited.\n'));
  }

  // Save diagnostic report
  const reportPath = join(process.cwd(), 'arena-diagnostics.txt');
  try {
    const { writeFileSync } = await import('fs');
    const report = generateTextReport(results);
    writeFileSync(reportPath, report);
    console.log(chalk.gray(`Diagnostic report saved: ${reportPath}\n`));
  } catch {
    // Ignore if can't save report
  }
}

async function checkSystemInfo(): Promise<DiagnosticResult> {
  const checks = [];

  // OS Info
  checks.push({
    name: 'Operating System',
    status: 'info' as const,
    message: `${platform()} ${release()} (${arch()})`,
  });

  // Node.js version
  checks.push({
    name: 'Node.js Version',
    status:
      Number(process.versions.node.split('.')[0]) >= 18 ? ('pass' as const) : ('fail' as const),
    message: `v${process.versions.node}`,
    solution:
      Number(process.versions.node.split('.')[0]) < 18
        ? 'Upgrade to Node.js 18.0.0 or later: https://nodejs.org'
        : undefined,
  });

  // Memory
  const totalMem = totalmem();
  const freeMem = freemem();
  const memoryStatus: 'pass' | 'warn' = freeMem > 1024 * 1024 * 1024 ? 'pass' : 'warn'; // 1GB free
  checks.push({
    name: 'Available Memory',
    status: memoryStatus,
    message: `${formatBytes(freeMem)} free of ${formatBytes(totalMem)}`,
    solution: memoryStatus === 'warn' ? 'Close some applications to free up memory' : undefined,
  });

  return {
    category: '📊 System Information',
    checks,
  };
}

async function checkDependencies(): Promise<DiagnosticResult> {
  const checks = [];
  const spinner = ora('Checking managed runtime and media tools...').start();
  const manifest = await readRuntimeManifest();
  const python = manifest
    ? await runProcess(manifest.pythonPath, ['--version'])
    : { code: 1, output: 'runtime manifest not found' };
  const [ffmpeg, ffprobe] = await Promise.all([
    runProcess('ffmpeg', ['-version']),
    runProcess('ffprobe', ['-version']),
  ]);
  spinner.stop();

  checks.push({
    name: 'Arena-managed Python',
    status: python.code === 0 ? ('pass' as const) : ('fail' as const),
    message:
      python.code === 0
        ? python.output.trim().split('\n')[0]
        : 'Private processing runtime is not ready',
    solution: python.code === 0 ? undefined : 'Run: arena setup',
  });
  checks.push({
    name: 'FFmpeg',
    status: ffmpeg.code === 0 ? ('pass' as const) : ('fail' as const),
    message:
      ffmpeg.code === 0
        ? ffmpeg.output.match(/ffmpeg version (\S+)/)?.[1] || 'Available'
        : 'Not found',
    solution: ffmpeg.code === 0 ? undefined : 'Run: arena setup',
  });
  checks.push({
    name: 'ffprobe',
    status: ffprobe.code === 0 ? ('pass' as const) : ('fail' as const),
    message: ffprobe.code === 0 ? 'Available' : 'Not found',
    solution: ffprobe.code === 0 ? undefined : 'Run: arena setup',
  });
  checks.push({
    name: 'yt-dlp JavaScript runtime',
    status: 'pass' as const,
    message: `Node.js v${process.versions.node}`,
  });

  return {
    category: '🔧 System Dependencies',
    checks,
  };
}

async function checkPythonEnvironment(): Promise<DiagnosticResult> {
  const checks = [];
  const manifest = await readRuntimeManifest();
  const spinner = ora('Verifying Arena engine imports...').start();
  const verification = manifest
    ? await runProcess(
        manifest.pythonPath,
        ['-c', 'import arena, cv2, librosa, numpy, openai, yt_dlp; print("ok")'],
        15000
      )
    : { code: 1, output: 'runtime manifest not found' };
  spinner.stop();

  checks.push({
    name: 'Arena engine imports',
    status: verification.code === 0 ? ('pass' as const) : ('fail' as const),
    message: verification.code === 0 ? 'Verified in the managed runtime' : 'Import check failed',
    solution: verification.code === 0 ? undefined : 'Run: arena setup --force',
  });

  return {
    category: '🐍 Python Environment',
    checks,
  };
}

async function checkNetworkAndAPI(): Promise<DiagnosticResult> {
  const checks = [];

  // Network connectivity
  const networkSpinner = ora('Checking network...').start();
  const hasNetwork = await checkNetworkConnectivity();
  networkSpinner.stop();

  checks.push({
    name: 'Internet Connectivity',
    status: hasNetwork ? ('pass' as const) : ('fail' as const),
    message: hasNetwork ? 'Connected' : 'No connection',
    solution: !hasNetwork ? 'Check your internet connection' : undefined,
  });

  // API key
  const apiKey = process.env.OPENAI_API_KEY;
  if (!apiKey) {
    checks.push({
      name: 'OpenAI API Key',
      status: 'warn' as const,
      message: 'Not set',
      solution: 'Set OPENAI_API_KEY environment variable',
    });
  } else {
    const apiSpinner = ora('Testing API key...').start();
    const { valid, error } = await testApiKey(apiKey);
    apiSpinner.stop();

    checks.push({
      name: 'OpenAI API Key',
      status: valid ? ('pass' as const) : ('fail' as const),
      message: valid ? 'Valid' : `Invalid: ${error}`,
      solution: !valid ? 'Check your API key at https://platform.openai.com/api-keys' : undefined,
    });
  }

  return {
    category: '🌐 Network & API',
    checks,
  };
}

async function checkDiskSpaceStatus(): Promise<DiagnosticResult> {
  const checks = [];

  const cwd = process.cwd();
  const spinner = ora('Checking disk space...').start();
  const { available, total } = await checkDiskSpace(cwd);
  spinner.stop();

  if (total > 0) {
    const percentFree = (available / total) * 100;
    const status: 'pass' | 'warn' | 'fail' =
      percentFree > 10 ? 'pass' : percentFree > 5 ? 'warn' : 'fail';

    checks.push({
      name: 'Disk Space',
      status,
      message: `${formatBytes(available)} available (${percentFree.toFixed(1)}% free)`,
      solution:
        status !== 'pass'
          ? 'Free up disk space - video processing requires significant storage'
          : undefined,
    });
  } else {
    checks.push({
      name: 'Disk Space',
      status: 'info' as const,
      message: 'Could not determine',
    });
  }

  return {
    category: '💾 Storage',
    checks,
  };
}

async function checkConfiguration(): Promise<DiagnosticResult> {
  const checks = [];

  // Check for config file
  const configPath = join(getArenaHome(), 'config.json');
  const hasConfig = existsSync(configPath);

  checks.push({
    name: 'Configuration File',
    status: 'info' as const,
    message: hasConfig ? `Found at ${configPath}` : 'Not configured (using defaults)',
    solution: !hasConfig ? 'Run: arena init' : undefined,
  });

  // Check workspace directory
  const workspaceDir = join(getArenaHome(), 'workspace');
  const hasWorkspace = existsSync(workspaceDir);

  checks.push({
    name: 'Workspace Directory',
    status: hasWorkspace ? ('pass' as const) : ('info' as const),
    message: hasWorkspace ? `${workspaceDir}` : 'Will be created on first use',
  });

  // Check for write permissions
  try {
    if (hasWorkspace) {
      const stats = statSync(workspaceDir);
      const writable = stats.mode & 0o200; // Check write permission
      checks.push({
        name: 'Workspace Writable',
        status: writable ? ('pass' as const) : ('fail' as const),
        message: writable ? 'Yes' : 'No write permission',
        solution: !writable ? `Fix permissions: chmod u+w ${workspaceDir}` : undefined,
      });
    }
  } catch {
    checks.push({
      name: 'Workspace Writable',
      status: 'info' as const,
      message: 'Cannot determine',
    });
  }

  return {
    category: '⚙️  Configuration',
    checks,
  };
}

function generateTextReport(results: DiagnosticResult[]): string {
  let report = 'ARENA DIAGNOSTICS REPORT\n';
  report += `Generated: ${new Date().toISOString()}\n`;
  report += `Platform: ${platform()} ${release()} (${arch()})\n`;
  report += `Node.js: v${process.versions.node}\n`;
  report += '='.repeat(60) + '\n\n';

  for (const result of results) {
    report += `${result.category}\n`;
    report += '-'.repeat(60) + '\n';

    for (const check of result.checks) {
      const statusSymbol = { pass: '✓', fail: '✗', warn: '⚠', info: 'ℹ' }[check.status];
      report += `${statusSymbol} ${check.name}: ${check.message}\n`;
      if (check.solution) {
        report += `  Solution: ${check.solution}\n`;
      }
    }

    report += '\n';
  }

  return report;
}
