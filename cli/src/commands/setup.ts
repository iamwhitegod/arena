/**
 * Setup command - Check and install dependencies
 */

import chalk from 'chalk';
import { promisify } from 'util';
import { exec } from 'child_process';
import ora from 'ora';
import inquirer from 'inquirer';
import { existsSync } from 'fs';
import { join } from 'path';
import { spawnWithErrorHandling, getUserFriendlyError } from '../utils/resilience.js';
import { logger, logCommand } from '../utils/logger.js';

const execAsync = promisify(exec);

interface DependencyCheck {
  name: string;
  command: string;
  versionCommand?: string;
  requiredVersion?: string;
  installInstructions: {
    [key: string]: string;
  };
  optional?: boolean;
}

const dependencies: DependencyCheck[] = [
  {
    name: 'Python 3.9+',
    command: 'python3 --version',
    requiredVersion: '3.9',
    installInstructions: {
      'darwin-brew': 'brew install python3',
      'darwin-port': 'sudo port install python311',
      'linux-apt': 'sudo apt-get update && sudo apt-get install -y python3 python3-pip',
      'linux-yum': 'sudo yum install -y python3 python3-pip',
      'linux-dnf': 'sudo dnf install -y python3 python3-pip',
      'linux-pacman': 'sudo pacman -S --noconfirm python python-pip',
      'linux-zypper': 'sudo zypper install -n python3 python3-pip',
      'win32-winget':
        'winget install --accept-source-agreements --accept-package-agreements Python.Python.3.11',
      'win32-choco': 'choco install -y python',
      'win32-manual': 'https://www.python.org/downloads/',
    },
  },
  {
    name: 'pip (Python package manager)',
    command: 'pip3 --version',
    installInstructions: {
      'darwin-brew': 'python3 -m ensurepip --upgrade',
      'darwin-port': 'python3 -m ensurepip --upgrade',
      'linux-apt': 'sudo apt-get install -y python3-pip',
      'linux-yum': 'sudo yum install -y python3-pip',
      'linux-dnf': 'sudo dnf install -y python3-pip',
      'linux-pacman': 'sudo pacman -S --noconfirm python-pip',
      'linux-zypper': 'sudo zypper install -n python3-pip',
      'win32-winget': 'python -m ensurepip --upgrade',
      'win32-choco': 'python -m ensurepip --upgrade',
      'win32-manual': 'python -m ensurepip --upgrade',
    },
  },
  {
    name: 'FFmpeg',
    command: 'ffmpeg -version',
    installInstructions: {
      'darwin-brew': 'brew install ffmpeg',
      'darwin-port': 'sudo port install ffmpeg',
      'linux-apt': 'sudo apt-get install -y ffmpeg',
      'linux-yum': 'sudo yum install -y ffmpeg',
      'linux-dnf': 'sudo dnf install -y ffmpeg',
      'linux-pacman': 'sudo pacman -S --noconfirm ffmpeg',
      'linux-zypper': 'sudo zypper install -n ffmpeg',
      'win32-winget':
        'winget install --accept-source-agreements --accept-package-agreements Gyan.FFmpeg',
      'win32-choco': 'choco install -y ffmpeg',
      'win32-manual': 'https://ffmpeg.org/download.html',
    },
  },
];

async function detectPackageManager(): Promise<string> {
  const platform = process.platform;

  if (platform === 'darwin') {
    // macOS: Check for brew or port
    try {
      await execAsync('which brew');
      return 'darwin-brew';
    } catch {
      try {
        await execAsync('which port');
        return 'darwin-port';
      } catch {
        return 'darwin-brew'; // Default to brew instructions
      }
    }
  } else if (platform === 'win32') {
    // Windows: Check for winget or choco
    try {
      await execAsync('winget --version');
      return 'win32-winget';
    } catch {
      try {
        await execAsync('choco --version');
        return 'win32-choco';
      } catch {
        return 'win32-manual';
      }
    }
  } else {
    // Linux: Check for various package managers
    const packageManagers = ['apt-get', 'yum', 'dnf', 'pacman', 'zypper'];

    for (const pm of packageManagers) {
      try {
        await execAsync(`which ${pm}`);
        return `linux-${pm === 'apt-get' ? 'apt' : pm}`;
      } catch {
        continue;
      }
    }

    return 'linux-apt'; // Default to apt
  }
}

async function checkCommand(command: string): Promise<{ installed: boolean; version?: string }> {
  try {
    const { stdout } = await execAsync(command);
    const versionMatch = stdout.match(/(\d+\.\d+\.\d+)/);
    return {
      installed: true,
      version: versionMatch ? versionMatch[1] : stdout.trim().split('\n')[0],
    };
  } catch {
    return { installed: false };
  }
}

async function checkPython(): Promise<{ installed: boolean; version?: string }> {
  // Try python commands in order of preference based on platform
  const pythonCommands =
    process.platform === 'win32'
      ? ['python --version', 'python3 --version', 'py --version']
      : ['python3 --version', 'python --version'];

  for (const cmd of pythonCommands) {
    try {
      const { stdout } = await execAsync(cmd);
      const versionMatch = stdout.match(/(\d+\.\d+\.\d+)/);
      return {
        installed: true,
        version: versionMatch ? versionMatch[1] : stdout.trim().split('\n')[0],
      };
    } catch {
      continue;
    }
  }

  return { installed: false };
}

async function checkPip(): Promise<{ installed: boolean; version?: string }> {
  // Try pip commands in order of preference based on platform
  const pipCommands =
    process.platform === 'win32'
      ? ['pip --version', 'pip3 --version', 'python -m pip --version', 'python3 -m pip --version']
      : ['pip3 --version', 'pip --version', 'python3 -m pip --version', 'python -m pip --version'];

  for (const cmd of pipCommands) {
    try {
      const { stdout } = await execAsync(cmd);
      const versionMatch = stdout.match(/(\d+\.\d+\.\d+)/);
      return {
        installed: true,
        version: versionMatch ? versionMatch[1] : stdout.trim().split('\n')[0],
      };
    } catch {
      continue;
    }
  }

  return { installed: false };
}

async function checkFFmpeg(): Promise<{
  installed: boolean;
  version?: string;
  foundPath?: string;
}> {
  // Try ffmpeg in PATH first
  try {
    const { stdout } = await execAsync('ffmpeg -version');
    const versionMatch = stdout.match(/ffmpeg version (\S+)/);
    return {
      installed: true,
      version: versionMatch ? versionMatch[1] : stdout.trim().split('\n')[0],
    };
  } catch {
    // On Windows, check common installation paths
    if (process.platform === 'win32') {
      const commonPaths = [
        'C:\\Program Files\\ffmpeg\\bin\\ffmpeg.exe',
        'C:\\Program Files (x86)\\ffmpeg\\bin\\ffmpeg.exe',
        'C:\\ffmpeg\\bin\\ffmpeg.exe',
      ];

      // Check ProgramData chocolatey path
      if (process.env.ProgramData) {
        commonPaths.push(join(process.env.ProgramData, 'chocolatey', 'bin', 'ffmpeg.exe'));
      }

      for (const ffmpegPath of commonPaths) {
        try {
          if (existsSync(ffmpegPath)) {
            const { stdout } = await execAsync(`"${ffmpegPath}" -version`);
            const versionMatch = stdout.match(/ffmpeg version (\S+)/);
            return {
              installed: true,
              version: versionMatch ? versionMatch[1] : 'found',
              foundPath: ffmpegPath,
            };
          }
        } catch {
          continue;
        }
      }
    }
  }

  return { installed: false };
}

async function getPipCommand(): Promise<string> {
  // Try pip commands in order of preference
  const pipCommands =
    process.platform === 'win32'
      ? ['pip', 'pip3', 'python -m pip', 'python3 -m pip']
      : ['pip3', 'pip', 'python3 -m pip', 'python -m pip'];

  for (const cmd of pipCommands) {
    try {
      await execAsync(`${cmd} --version`);
      return cmd;
    } catch {
      continue;
    }
  }

  // Fallback to pip3 on Unix, pip on Windows
  return process.platform === 'win32' ? 'pip' : 'pip3';
}

async function installPythonPackages(): Promise<boolean> {
  console.log(chalk.cyan('\n📦 Installing Python packages...\n'));

  const pipCommand = await getPipCommand();

  // Check if requirements.txt exists
  const requirementsPath = join(process.cwd(), '../../engine/requirements.txt');
  const hasRequirementsFile = existsSync(requirementsPath);

  if (hasRequirementsFile) {
    console.log(chalk.gray('   Using engine/requirements.txt\n'));
  }

  // On Windows, show warning about installation time
  if (process.platform === 'win32') {
    console.log(
      chalk.yellow('⏱️  Note: This may take 5-10 minutes (torch, librosa are large packages)')
    );
    console.log(chalk.gray('   You can watch progress below...\n'));
  }

  const spinner = ora('Installing Python dependencies').start();

  logger.info('Installing Python packages', {
    source: hasRequirementsFile ? 'requirements.txt' : 'hardcoded packages',
  });

  try {
    // Handle "python -m pip" vs "pip" command format
    let command: string;
    let args: string[];

    if (hasRequirementsFile) {
      // Install from requirements.txt
      if (pipCommand.includes(' -m ')) {
        const parts = pipCommand.split(' ');
        command = parts[0];
        args = [...parts.slice(1), 'install', '-r', requirementsPath];
      } else {
        command = pipCommand;
        args = ['install', '-r', requirementsPath];
      }
    } else {
      // Fallback to hardcoded packages
      const fallbackPackages = [
        'openai-whisper',
        'openai',
        'ffmpeg-python',
        'torch',
        'numpy',
        'scipy',
      ];
      if (pipCommand.includes(' -m ')) {
        const parts = pipCommand.split(' ');
        command = parts[0];
        args = [...parts.slice(1), 'install', ...fallbackPackages];
      } else {
        command = pipCommand;
        args = ['install', ...fallbackPackages];
      }
    }

    // Add --user flag on Windows to avoid permission issues
    if (process.platform === 'win32') {
      args.push('--user');
    }

    // Add flags to avoid cache and hash issues
    args.push('--no-cache-dir'); // Avoid stale cache causing hash mismatches
    args.push('--upgrade'); // Ensure we get latest compatible versions

    const result = await spawnWithErrorHandling(command, args, {
      shell: false, // Avoid shell for security (args are properly escaped)
      onStdout: (data) => {
        // Update spinner with current package
        const match = data.match(/Collecting (\S+)/);
        if (match) {
          spinner.text = `Installing ${match[1]}...`;
        }
      },
      onError: (error) => {
        logger.error('Python package installation spawn error', error);
      },
    });

    if (result.code === 0) {
      spinner.succeed('Python packages installed successfully');
      logger.info('Python packages installed successfully');
      return true;
    } else {
      spinner.fail('Failed to install Python packages');
      logger.error('Python package installation failed', undefined, {
        stdout: result.stdout,
        stderr: result.stderr,
      });

      console.log(chalk.red('\nError output:'));
      console.log(chalk.gray(result.stderr || result.stdout));

      // Detect specific errors and provide solutions
      const output = (result.stderr || result.stdout).toLowerCase();

      if (output.includes('access is denied') || output.includes('permission denied')) {
        console.log(chalk.yellow('\n⚠️  Permission Error Detected:'));
        if (process.platform === 'win32') {
          console.log(chalk.white('Solution 1 (Recommended): Install to user directory'));
          console.log(chalk.cyan(`  ${pipCommand} install --user -r requirements.txt\n`));
          console.log(chalk.white('Solution 2: Run PowerShell as Administrator'));
          console.log(chalk.gray('  Right-click PowerShell → "Run as Administrator"'));
          console.log(chalk.cyan(`  ${pipCommand} install -r requirements.txt\n`));
        } else {
          console.log(chalk.white('Try with --user flag:'));
          console.log(chalk.cyan(`  ${pipCommand} install --user -r requirements.txt\n`));
        }
      } else if (output.includes('timeout') || output.includes('timed out')) {
        console.log(chalk.yellow('\n⚠️  Network Timeout:'));
        console.log(chalk.white('The installation timed out. Try again with:'));
        const userFlag = process.platform === 'win32' ? ' --user' : '';
        console.log(
          chalk.cyan(`  ${pipCommand} install${userFlag} --timeout 300 -r requirements.txt\n`)
        );
      } else if (output.includes('hash') || output.includes('these packages do not match')) {
        console.log(chalk.yellow('\n⚠️  Corrupted Cache Detected:'));
        console.log(
          chalk.white('Pip cache has corrupted or outdated files. Clear it and retry:\n')
        );
        console.log(chalk.cyan(`  ${pipCommand} cache purge`));
        const userFlag = process.platform === 'win32' ? ' --user' : '';
        console.log(
          chalk.cyan(`  ${pipCommand} install${userFlag} --no-cache-dir -r requirements.txt\n`)
        );
        console.log(
          chalk.gray('Note: --no-cache-dir flag was added to avoid this issue in future.\n')
        );
      } else {
        console.log(chalk.yellow('\n💡 Tip: Try running manually:'));
        const userFlag = process.platform === 'win32' ? ' --user' : '';
        console.log(
          chalk.cyan(`  ${pipCommand} install${userFlag} --no-cache-dir -r requirements.txt\n`)
        );
      }

      return false;
    }
  } catch (error) {
    spinner.fail('Failed to start pip');
    logger.error('Python package installation error', error as Error);
    console.log(chalk.red(`\nError: ${getUserFriendlyError(error as Error)}`));
    console.log(chalk.yellow('\n💡 Try installing manually:'));
    const userFlag = process.platform === 'win32' ? ' --user' : '';
    console.log(
      chalk.cyan(`  ${pipCommand} install${userFlag} --no-cache-dir -r requirements.txt\n`)
    );
    return false;
  }
}

/**
 * Install Arena engine package
 */
async function installArenaEngine(): Promise<boolean> {
  console.log(chalk.cyan('\n📦 Installing Arena engine package...\n'));

  const pipCommand = await getPipCommand();
  const spinner = ora('Installing Arena engine').start();

  try {
    // Get engine path
    const enginePath = join(process.cwd(), '../../engine');

    // Check if engine directory exists
    if (!existsSync(enginePath)) {
      spinner.warn('Engine directory not found, skipping');
      console.log(chalk.yellow('⚠️  Could not find engine directory'));
      console.log(chalk.gray('   Expected location: engine/'));
      console.log(chalk.gray('   This is optional if running from npm package\n'));
      return true; // Non-fatal, return true to continue
    }

    let command: string;
    let args: string[];

    if (pipCommand.includes(' -m ')) {
      const parts = pipCommand.split(' ');
      command = parts[0];
      args = [...parts.slice(1), 'install', '-e', enginePath];
    } else {
      command = pipCommand;
      args = ['install', '-e', enginePath];
    }

    // Add --user flag on Windows
    if (process.platform === 'win32') {
      args.push('--user');
    }

    args.push('--no-cache-dir');

    const result = await spawnWithErrorHandling(command, args, {
      shell: false,
      onStdout: (data) => {
        if (data.includes('Successfully installed')) {
          spinner.text = 'Arena engine installed';
        }
      },
    });

    if (result.code === 0) {
      spinner.succeed('Arena engine installed successfully');
      return true;
    } else {
      spinner.warn('Arena engine installation had issues');
      console.log(chalk.yellow('\n⚠️  Arena engine installation failed'));
      console.log(chalk.gray('   You can install it manually:'));
      console.log(chalk.cyan(`   cd engine && ${pipCommand} install -e .`));
      return true; // Non-fatal, return true to continue
    }
  } catch (error) {
    spinner.warn('Could not install Arena engine');
    console.log(chalk.yellow('\n⚠️  Arena engine installation skipped'));
    console.log(chalk.gray('   You can install it manually:'));
    console.log(chalk.cyan(`   cd engine && ${pipCommand} install -e .`));
    return true; // Non-fatal, return true to continue
  }
}

async function autoInstallDependency(
  dep: DependencyCheck,
  packageManager: string
): Promise<boolean> {
  const installCommand =
    dep.installInstructions[packageManager] ||
    dep.installInstructions[`${packageManager.split('-')[0]}-manual`];

  if (!installCommand || installCommand.startsWith('http')) {
    console.log(chalk.yellow(`\n📥 ${dep.name} requires manual installation:`));
    console.log(chalk.cyan(`   ${installCommand}\n`));
    return false;
  }

  console.log(chalk.cyan(`\n📥 Installing ${dep.name}...\n`));
  console.log(chalk.gray(`Command: ${installCommand}\n`));

  const spinner = ora(`Installing ${dep.name}`).start();

  try {
    // Use shell mode for better compatibility (especially on Windows)
    await execAsync(installCommand);
    spinner.succeed(`${dep.name} installed successfully`);
    return true;
  } catch (error) {
    spinner.fail(`Failed to install ${dep.name}`);

    const err = error as { stderr?: string; stdout?: string; message?: string };
    const errorMessage = err.stderr || err.stdout || err.message || '';

    if (errorMessage) {
      console.log(chalk.red('\nError details:'));
      console.log(chalk.gray(errorMessage));
    }

    console.log(chalk.yellow('\n💡 Please install manually:'));
    console.log(chalk.cyan(`  ${installCommand}\n`));

    // Detect and provide specific solutions for common errors
    const errorLower = errorMessage.toLowerCase();

    // Repository/package not found errors
    if (errorLower.includes('unable to locate package') || errorLower.includes('no package')) {
      console.log(chalk.yellow('Repository Issue Detected:'));
      if (process.platform === 'linux') {
        console.log(chalk.gray('Ubuntu/Debian: Enable universe repository:'));
        console.log(chalk.cyan('  sudo add-apt-repository universe'));
        console.log(chalk.cyan('  sudo apt-get update\n'));
      }
    }

    // EPEL needed (RHEL/CentOS)
    if (errorLower.includes('no match for argument') && installCommand.includes('yum')) {
      console.log(chalk.yellow('EPEL Repository Needed:'));
      console.log(chalk.gray('RHEL/CentOS: Install EPEL first:'));
      console.log(chalk.cyan('  sudo yum install -y epel-release\n'));
    }

    // RPM Fusion needed (Fedora)
    if (
      errorLower.includes('no match') &&
      installCommand.includes('ffmpeg') &&
      installCommand.includes('dnf')
    ) {
      console.log(chalk.yellow('RPM Fusion Repository Needed:'));
      console.log(chalk.gray('Fedora: Enable RPM Fusion:'));
      console.log(
        chalk.cyan(
          '  sudo dnf install -y https://download1.rpmfusion.org/free/fedora/rpmfusion-free-release-$(rpm -E %fedora).noarch.rpm\n'
        )
      );
    }

    // Permission denied
    if (errorLower.includes('permission denied') || errorLower.includes('access denied')) {
      console.log(chalk.yellow('Permission Issue:'));
      if (process.platform === 'win32') {
        console.log(chalk.gray('Run PowerShell/CMD as Administrator:'));
        console.log(chalk.gray('  Right-click → "Run as Administrator"\n'));
      } else {
        console.log(chalk.gray('This command needs sudo privileges'));
        console.log(chalk.gray('Make sure your user has sudo access\n'));
      }
    }

    // Command not found
    if (errorLower.includes('command not found') || errorLower.includes('not recognized')) {
      if (installCommand.includes('brew') && process.platform === 'darwin') {
        console.log(chalk.yellow('Homebrew Not Installed:'));
        console.log(chalk.gray('Install Homebrew first:'));
        console.log(
          chalk.cyan(
            '  /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"\n'
          )
        );
      } else if (installCommand.includes('choco') && process.platform === 'win32') {
        console.log(chalk.yellow('Chocolatey Not Installed:'));
        console.log(chalk.gray('Install Chocolatey first:'));
        console.log(chalk.cyan('  Visit: https://chocolatey.org/install\n'));
      }
    }

    // Show additional help for common issues
    if (
      installCommand.includes('sudo') &&
      process.platform !== 'win32' &&
      !errorLower.includes('password')
    ) {
      console.log(chalk.gray('Note: This command requires administrator privileges (sudo)'));
    } else if (installCommand.includes('winget') && process.platform === 'win32') {
      console.log(chalk.gray('Note: winget requires Windows 10 1809 or later'));
      console.log(chalk.gray('      You may need to run PowerShell/CMD as Administrator'));
    }

    return false;
  }
}

export async function setupCommand(): Promise<void> {
  logCommand('setup', {});
  const startTime = Date.now();

  console.log(chalk.cyan('\n🔧 ARENA SETUP\n'));
  console.log(chalk.white('Checking system dependencies...\n'));

  try {
    const packageManager = await detectPackageManager();
    console.log(
      chalk.gray(`Detected package manager: ${packageManager.split('-')[1] || 'manual'}\n`)
    );

    const results: Array<{ dep: DependencyCheck; installed: boolean; version?: string }> = [];

    // Check all dependencies
    for (const dep of dependencies) {
      const spinner = ora(`Checking ${dep.name}`).start();

      // Use special checks for Python, pip, and FFmpeg to handle cross-platform variations
      let result;
      if (dep.name.includes('Python')) {
        result = await checkPython();
      } else if (dep.name.includes('pip')) {
        result = await checkPip();
      } else if (dep.name.includes('FFmpeg')) {
        result = await checkFFmpeg();
      } else {
        result = await checkCommand(dep.command);
      }

      if (result.installed) {
        spinner.succeed(`${dep.name} ${chalk.gray(result.version || '')}`);
      } else {
        spinner.fail(`${dep.name} not found`);
      }

      results.push({ dep, ...result });
    }

    // Check if FFmpeg was found on Windows but not in PATH
    if (process.platform === 'win32') {
      const ffmpegResult = results.find((r) => r.dep.name.includes('FFmpeg'));
      const ffmpegPath =
        ffmpegResult && 'foundPath' in ffmpegResult
          ? (ffmpegResult as { foundPath?: string }).foundPath
          : undefined;
      if (ffmpegResult && ffmpegResult.installed && ffmpegPath) {
        console.log(chalk.yellow('\n⚠️  FFmpeg found but not in PATH'));
        console.log(chalk.white('FFmpeg is installed at:'));
        console.log(chalk.cyan(`  ${ffmpegPath}\n`));
        console.log(chalk.white('To use it from anywhere, add it to your PATH:'));
        console.log(chalk.gray('  1. Open System Properties → Environment Variables'));
        console.log(chalk.gray(`  2. Add to PATH: ${ffmpegPath.replace('\\ffmpeg.exe', '')}\n`));
        console.log(chalk.white('Or restart your terminal after installation.\n'));
      }
    }

    // Summary
    const missing = results.filter((r) => !r.installed);

    console.log(chalk.cyan('\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n'));

    if (missing.length === 0) {
      console.log(chalk.green('✓ All system dependencies installed!\n'));

      // Check Python packages
      console.log(chalk.cyan('Checking Python packages...\n'));

      const { installPackages } = await inquirer.prompt([
        {
          type: 'confirm',
          name: 'installPackages',
          message: 'Install/update required Python packages?',
          default: true,
        },
      ]);

      if (installPackages) {
        const success = await installPythonPackages();

        if (success) {
          // Install Arena engine package
          await installArenaEngine();

          console.log(chalk.green('\n✓ Setup complete! Arena is ready to use.\n'));
          console.log(chalk.cyan('Try it out:'));
          console.log(chalk.white('  arena process video.mp4 -p tiktok\n'));
        } else {
          console.log(chalk.yellow('\n⚠️  Setup completed with errors'));
          console.log(chalk.white('You may need to install Python packages manually:\n'));
          console.log(chalk.gray(`  pip3 install -r engine/requirements.txt\n`));
        }
      } else {
        console.log(chalk.yellow('\nSkipped Python package installation'));
        console.log(chalk.white('Install them later with:\n'));
        console.log(chalk.gray(`  pip3 install -r engine/requirements.txt\n`));
      }
    } else {
      console.log(chalk.red(`✗ Missing ${missing.length} dependencies:\n`));

      missing.forEach(({ dep }) => {
        console.log(chalk.white(`  • ${dep.name}`));
        const instruction =
          dep.installInstructions[packageManager] ||
          dep.installInstructions[`${packageManager.split('-')[0]}-manual`] ||
          'Manual installation required';
        console.log(chalk.gray(`    ${instruction}\n`));
      });

      // Show platform-specific notes
      if (process.platform === 'win32') {
        console.log(chalk.yellow('⚠️  Windows Note:'));
        console.log(chalk.gray('   Automatic installation may require running as Administrator'));
        console.log(chalk.gray('   Right-click PowerShell/CMD → "Run as Administrator"\n'));
      } else if (process.platform === 'linux') {
        console.log(chalk.yellow('⚠️  Linux Note:'));
        console.log(chalk.gray('   Automatic installation requires sudo privileges'));
        console.log(chalk.gray('   You may be prompted for your password\n'));
      }

      // Ask if user wants to auto-install
      const { autoInstall } = await inquirer.prompt([
        {
          type: 'confirm',
          name: 'autoInstall',
          message: 'Would you like to try automatic installation?',
          default: true,
        },
      ]);

      if (autoInstall) {
        const installResults = new Map<string, boolean>();

        // Install dependencies with smart sequencing
        // Install Python first if needed (pip depends on it)
        const pythonDep = missing.find(({ dep }) => dep.name.includes('Python'));
        if (pythonDep && !pythonDep.installed) {
          const success = await autoInstallDependency(pythonDep.dep, packageManager);
          installResults.set('Python', success);

          if (success) {
            console.log(chalk.yellow('\n⏳ Waiting for Python to be available in PATH...'));
            console.log(chalk.gray('   (This may take a few seconds)\n'));

            // Wait and retry to detect Python
            let pythonFound = false;
            for (let i = 0; i < 5; i++) {
              await new Promise((resolve) => setTimeout(resolve, 2000)); // Wait 2 seconds
              const result = await checkPython();
              if (result.installed) {
                console.log(chalk.green('✓ Python is now available!\n'));
                pythonFound = true;
                break;
              }
            }

            if (!pythonFound) {
              console.log(chalk.yellow('⚠️  Python installed but not yet in PATH\n'));
              console.log(
                chalk.white('You need to restart your terminal for Python to be available.\n')
              );

              const { restartNow } = await inquirer.prompt([
                {
                  type: 'confirm',
                  name: 'restartNow',
                  message: 'Do you want to restart your terminal now and continue setup later?',
                  default: true,
                },
              ]);

              if (restartNow) {
                console.log(chalk.cyan('\n📋 After restarting your terminal, run:\n'));
                console.log(chalk.white('  arena setup\n'));
                console.log(chalk.yellow('Instructions to restart:'));
                if (process.platform === 'win32') {
                  console.log(chalk.gray('  1. Close this PowerShell/CMD window'));
                  console.log(chalk.gray('  2. Open a new PowerShell/CMD window'));
                  console.log(chalk.gray('  3. Run: arena setup\n'));
                } else {
                  console.log(chalk.gray('  1. Close this terminal'));
                  console.log(chalk.gray('  2. Open a new terminal'));
                  console.log(chalk.gray('  3. Run: arena setup\n'));
                }
                return;
              } else {
                console.log(chalk.yellow('\nContinuing anyway (pip installation may fail)...\n'));
              }
            }
          }
        }

        // Install remaining dependencies
        for (const { dep, installed } of missing) {
          if (!installed && !dep.name.includes('Python')) {
            const success = await autoInstallDependency(dep, packageManager);
            installResults.set(dep.name, success);

            // If pip was just installed, wait for it to be available
            if (success && dep.name.includes('pip')) {
              console.log(chalk.yellow('\n⏳ Verifying pip is available...\n'));
              await new Promise((resolve) => setTimeout(resolve, 1000));
            }
          }
        }

        // Re-check
        console.log(chalk.cyan('\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n'));
        console.log(chalk.white('Re-checking dependencies...\n'));

        let allInstalled = true;
        const stillMissing: string[] = [];

        for (const { dep } of missing) {
          // Use cross-platform detection for re-check
          let result;
          if (dep.name.includes('Python')) {
            result = await checkPython();
          } else if (dep.name.includes('pip')) {
            result = await checkPip();
          } else if (dep.name.includes('FFmpeg')) {
            result = await checkFFmpeg();
          } else {
            result = await checkCommand(dep.command);
          }

          if (result.installed) {
            console.log(chalk.green(`✓ ${dep.name} ${chalk.gray(result.version || '')}`));
          } else {
            console.log(chalk.red(`✗ ${dep.name} still not found`));
            stillMissing.push(dep.name);
            allInstalled = false;
          }
        }

        if (allInstalled) {
          console.log(chalk.green('\n✓ All dependencies installed!\n'));

          // Install Python packages
          const success = await installPythonPackages();

          if (success) {
            // Install Arena engine package
            await installArenaEngine();

            console.log(chalk.green('\n✓ Setup complete! Arena is ready to use.\n'));
            console.log(chalk.cyan('Try it out:'));
            console.log(chalk.white('  arena process video.mp4 -p tiktok\n'));
          }
        } else {
          console.log(
            chalk.yellow('\n⚠️  Some dependencies could not be installed automatically\n')
          );

          // Check if any were actually installed but not found (PATH issue)
          const installedButNotFound = stillMissing.filter((name) => installResults.get(name));

          if (installedButNotFound.length > 0) {
            console.log(chalk.yellow(`⚠️  These were installed but not found in PATH:`));
            installedButNotFound.forEach((name) => {
              console.log(chalk.white(`   • ${name}`));
            });
            console.log();

            console.log(chalk.white('This usually means you need to restart your terminal.\n'));
            console.log(chalk.cyan('To fix this:\n'));

            if (process.platform === 'win32') {
              console.log(chalk.white('  1. Close this PowerShell/CMD window'));
              console.log(chalk.white('  2. Open a new PowerShell/CMD window'));
              console.log(chalk.white('  3. Run: arena setup\n'));
            } else {
              console.log(chalk.white('  Option 1 (Recommended):'));
              console.log(chalk.gray('    - Close and reopen your terminal'));
              console.log(chalk.gray('    - Run: arena setup\n'));

              console.log(chalk.white('  Option 2 (Quick):'));
              if (existsSync(`${process.env.HOME}/.zshrc`)) {
                console.log(chalk.gray('    - Run: source ~/.zshrc && arena setup'));
              } else if (existsSync(`${process.env.HOME}/.bashrc`)) {
                console.log(chalk.gray('    - Run: source ~/.bashrc && arena setup'));
              } else {
                console.log(chalk.gray('    - Run: source ~/.profile && arena setup'));
              }
              console.log();
            }
          } else {
            console.log(chalk.white('Please install them manually using the commands above.\n'));

            // Show PATH restart warning
            console.log(chalk.yellow('💡 After manual installation:'));
            console.log(chalk.gray('   Restart your terminal to update PATH'));
            if (process.platform === 'win32') {
              console.log(chalk.gray('   - Close and reopen PowerShell/CMD'));
            } else {
              console.log(chalk.gray('   - Or run: source ~/.bashrc (or ~/.zshrc)'));
            }
            console.log(chalk.gray('   Then run: arena setup\n'));
          }
        }
      } else {
        console.log(chalk.yellow('\nPlease install the missing dependencies manually, then run:'));
        console.log(chalk.cyan('  arena setup\n'));
      }
    }

    const duration = Date.now() - startTime;
    logger.info('Setup completed', { durationMs: duration });
  } catch (error) {
    logger.error('Setup failed with unexpected error', error as Error);
    console.log(chalk.red('\n✗ Setup failed with unexpected error:'));
    console.log(chalk.gray(getUserFriendlyError(error as Error)));
    console.log(chalk.yellow('\n💡 For help, run:'));
    console.log(chalk.cyan('  arena diagnose\n'));
    process.exit(1);
  }
}
