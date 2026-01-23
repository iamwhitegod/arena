#!/usr/bin/env node

/**
 * Post-install script
 * Checks dependencies and provides setup guidance
 */

const { promisify } = require('util');
const { exec } = require('child_process');

const execAsync = promisify(exec);

const platform = process.platform;

// ANSI color codes (chalk alternative for CommonJS)
const colors = {
  cyan: (text) => `\x1b[36m${text}\x1b[0m`,
  green: (text) => `\x1b[32m${text}\x1b[0m`,
  red: (text) => `\x1b[31m${text}\x1b[0m`,
  yellow: (text) => `\x1b[33m${text}\x1b[0m`,
  white: (text) => `\x1b[37m${text}\x1b[0m`,
  gray: (text) => `\x1b[90m${text}\x1b[0m`,
};

async function checkCommand(command) {
  try {
    await execAsync(`${command} --version`);
    return true;
  } catch {
    return false;
  }
}

async function checkPython() {
  // Try python commands in order of preference based on platform
  const pythonCommands = platform === 'win32'
    ? ['python', 'python3', 'py']
    : ['python3', 'python'];

  for (const cmd of pythonCommands) {
    if (await checkCommand(cmd)) {
      return true;
    }
  }
  return false;
}

async function checkFFmpeg() {
  // Try ffmpeg in PATH first
  if (await checkCommand('ffmpeg')) {
    return true;
  }

  // On Windows, check common installation paths
  if (platform === 'win32') {
    const fs = require('fs');
    const path = require('path');

    const commonPaths = [
      'C:\\Program Files\\ffmpeg\\bin\\ffmpeg.exe',
      'C:\\Program Files (x86)\\ffmpeg\\bin\\ffmpeg.exe',
      'C:\\ffmpeg\\bin\\ffmpeg.exe',
    ];

    // Check if ProgramData chocolatey path exists
    if (process.env.ProgramData) {
      commonPaths.push(path.join(process.env.ProgramData, 'chocolatey', 'bin', 'ffmpeg.exe'));
    }

    for (const ffmpegPath of commonPaths) {
      if (fs.existsSync(ffmpegPath)) {
        return true;
      }
    }
  }

  return false;
}

async function main() {
  console.log('\n');
  console.log(colors.cyan('🎉 Arena CLI installed successfully!\n'));

  // Check dependencies
  const pythonExists = await checkPython();
  const ffmpegExists = await checkFFmpeg();

  const allInstalled = pythonExists && ffmpegExists;

  if (allInstalled) {
    console.log(colors.green('✓ All dependencies found!\n'));
    console.log(colors.white('Quick start:'));
    console.log(colors.gray('  1. Set your OpenAI API key:'));
    console.log(colors.cyan('     export OPENAI_API_KEY="sk-..."\n'));
    console.log(colors.gray('  2. Process a video:'));
    console.log(colors.cyan('     arena process video.mp4 -p tiktok\n'));
  } else {
    console.log(colors.yellow('⚠️  Some dependencies are missing:\n'));

    if (!pythonExists) {
      console.log(colors.red('  ✗ Python 3.9+'));
    } else {
      console.log(colors.green('  ✓ Python 3.9+'));
    }

    if (!ffmpegExists) {
      console.log(colors.red('  ✗ FFmpeg'));
    } else {
      console.log(colors.green('  ✓ FFmpeg'));
    }

    console.log('\n' + colors.cyan('📦 Easy Installation (Works on ALL platforms):\n'));
    console.log(colors.white('  Run the automated setup command:'));
    console.log(colors.cyan('    arena setup\n'));
    console.log(colors.gray('  This will automatically install missing dependencies'));
    console.log(colors.gray('  on Windows, macOS, and Linux.\n'));

    // Show platform-specific manual instructions as alternative
    console.log(colors.white('  Or install manually:\n'));

    if (platform === 'darwin') {
      console.log(colors.gray('  macOS (Homebrew):'));
      if (!pythonExists) console.log(colors.gray('    brew install python3'));
      if (!ffmpegExists) console.log(colors.gray('    brew install ffmpeg'));
    } else if (platform === 'linux') {
      console.log(colors.gray('  Linux (apt):'));
      if (!pythonExists) console.log(colors.gray('    sudo apt-get install python3 python3-pip'));
      if (!ffmpegExists) console.log(colors.gray('    sudo apt-get install ffmpeg'));
      console.log(colors.gray('\n  Linux (yum/dnf):'));
      if (!pythonExists) console.log(colors.gray('    sudo yum install python3 python3-pip'));
      if (!ffmpegExists) console.log(colors.gray('    sudo yum install ffmpeg'));
      console.log(colors.gray('\n  Linux (pacman):'));
      if (!pythonExists) console.log(colors.gray('    sudo pacman -S python python-pip'));
      if (!ffmpegExists) console.log(colors.gray('    sudo pacman -S ffmpeg'));
    } else if (platform === 'win32') {
      console.log(colors.gray('  Windows (winget):'));
      if (!pythonExists) console.log(colors.gray('    winget install Python.Python.3.11'));
      if (!ffmpegExists) console.log(colors.gray('    winget install Gyan.FFmpeg'));
      console.log(colors.gray('\n  Windows (chocolatey):'));
      if (!pythonExists) console.log(colors.gray('    choco install python'));
      if (!ffmpegExists) console.log(colors.gray('    choco install ffmpeg'));
      console.log(colors.gray('\n  Windows (manual):'));
      if (!pythonExists) console.log(colors.gray('    https://www.python.org/downloads/'));
      if (!ffmpegExists) console.log(colors.gray('    https://ffmpeg.org/download.html'));
    } else {
      // Other platforms
      console.log(colors.gray('  Visit:'));
      if (!pythonExists) console.log(colors.gray('    https://www.python.org/downloads/'));
      if (!ffmpegExists) console.log(colors.gray('    https://ffmpeg.org/download.html'));
    }

    console.log('');
  }
}

main().catch((error) => {
  console.error('Setup check failed:', error.message);
  // Don't fail npm install
  process.exit(0);
});
