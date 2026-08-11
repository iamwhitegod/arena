#!/usr/bin/env node

/**
 * Arena Standalone Binary Builder Orchestrator (Dependency-free version)
 * Coordinates compiling python engine, preparing sidecars, and packaging Node CLI.
 */

import path from 'path';
import fs from 'fs';
import { execSync, spawnSync } from 'child_process';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const ROOT_DIR = path.resolve(__dirname, '..');
const DIST_DIR = path.join(ROOT_DIR, 'dist');
const BUILD_DIR = path.join(ROOT_DIR, 'build');
const CLI_DIR = path.join(ROOT_DIR, 'cli');
const CLI_DIST_DIR = path.join(CLI_DIR, 'dist');
const CLI_BIN_DIR = path.join(CLI_DIST_DIR, 'bin');

// Color helpers for terminal output
const colors = {
  cyan: (text) => `\x1b[36m${text}\x1b[0m`,
  green: (text) => `\x1b[32m${text}\x1b[0m`,
  yellow: (text) => `\x1b[33m${text}\x1b[0m`,
  red: (text) => `\x1b[31m${text}\x1b[0m`,
  gray: (text) => `\x1b[90m${text}\x1b[0m`,
  bold: (text) => `\x1b[1m${text}\x1b[0m`,
  white: (text) => `\x1b[37m${text}\x1b[0m`,
};

console.log(colors.cyan('\n🔨 ARENA STANDALONE BINARY BUILDER\n'));

async function main() {
  try {
    // 1. Verify build toolchains
    console.log(colors.gray('1. Verifying toolchains...'));
    try {
      execSync('pyinstaller --version', { stdio: 'ignore' });
      console.log(colors.green('   ✓ PyInstaller is available'));
    } catch {
      throw new Error('PyInstaller is not installed or not in PATH. Please run: pip install pyinstaller');
    }

    // 2. Ensure clean root dist/ and build/ folders
    console.log(colors.gray('2. Preparing build environment...'));
    fs.mkdirSync(DIST_DIR, { recursive: true });
    fs.mkdirSync(BUILD_DIR, { recursive: true });
    console.log(colors.green('   ✓ Build directories verified'));

    // 3. Compile Python Engine with PyInstaller if missing or build is requested
    const engineBinName = process.platform === 'win32' ? 'arena-engine.exe' : 'arena-engine';
    const compiledEnginePath = path.join(DIST_DIR, engineBinName);

    if (fs.existsSync(compiledEnginePath)) {
      console.log(colors.green(`   ✓ Standalone Python engine already compiled at: ${compiledEnginePath}`));
    } else {
      console.log(colors.cyan('3. Compiling Python video engine with PyInstaller...'));
      console.log(colors.gray('   (This bundles PyTorch, Whisper, and Matplotlib. It may take a couple of minutes)'));
      
      const pyinstallerCmd = `pyinstaller --onefile --name arena-engine --paths=engine engine/arena-cli`;
      execSync(pyinstallerCmd, { cwd: ROOT_DIR, stdio: 'inherit' });
      console.log(colors.green('   ✓ Python engine successfully compiled!'));
    }

    // 4. Build TypeScript Node CLI
    console.log(colors.cyan('\n4. Compiling TypeScript CLI...'));
    execSync('npm run build', { cwd: CLI_DIR, stdio: 'inherit' });
    console.log(colors.green('   ✓ CLI TypeScript compiled to JS successfully'));

    // 5. Package sidecar assets (Engine + FFmpeg + FFprobe)
    console.log(colors.cyan('\n5. Preparing sidecar assets...'));
    fs.mkdirSync(CLI_BIN_DIR, { recursive: true });

    // Copy compiled engine sidecar
    const targetEnginePath = path.join(CLI_BIN_DIR, engineBinName);
    console.log(colors.gray(`   Copying engine sidecar to ${targetEnginePath}...`));
    fs.cpSync(compiledEnginePath, targetEnginePath);
    fs.chmodSync(targetEnginePath, 0o755);

    // Copy static FFmpeg and FFprobe sidecars
    const ffmpegBinName = process.platform === 'win32' ? 'ffmpeg.exe' : 'ffmpeg';
    const ffprobeBinName = process.platform === 'win32' ? 'ffprobe.exe' : 'ffprobe';
    
    const targetFfmpegPath = path.join(CLI_BIN_DIR, ffmpegBinName);
    const targetFfprobePath = path.join(CLI_BIN_DIR, ffprobeBinName);

    // Try to find system FFmpeg/FFprobe and bundle them
    let sysFfmpeg = '';
    let sysFfprobe = '';

    try {
      sysFfmpeg = execSync(process.platform === 'win32' ? 'where ffmpeg' : 'which ffmpeg').toString().trim().split('\n')[0];
      sysFfprobe = execSync(process.platform === 'win32' ? 'where ffprobe' : 'which ffprobe').toString().trim().split('\n')[0];
    } catch {
      console.log(colors.yellow('   ⚠️  System FFmpeg/FFprobe not found via PATH. Seeking common locations...'));
    }

    if (!sysFfmpeg && process.platform === 'darwin') {
      if (fs.existsSync('/opt/homebrew/bin/ffmpeg')) {
        sysFfmpeg = '/opt/homebrew/bin/ffmpeg';
        sysFfprobe = '/opt/homebrew/bin/ffprobe';
      } else if (fs.existsSync('/usr/local/bin/ffmpeg')) {
        sysFfmpeg = '/usr/local/bin/ffmpeg';
        sysFfprobe = '/usr/local/bin/ffprobe';
      }
    }

    if (sysFfmpeg && fs.existsSync(sysFfmpeg)) {
      console.log(colors.gray(`   Bundling system ffmpeg from: ${sysFfmpeg}`));
      fs.cpSync(sysFfmpeg, targetFfmpegPath);
      fs.chmodSync(targetFfmpegPath, 0o755);
    } else {
      console.log(colors.yellow('   ⚠️  Could not locate ffmpeg binary to package.'));
    }

    if (sysFfprobe && fs.existsSync(sysFfprobe)) {
      console.log(colors.gray(`   Bundling system ffprobe from: ${sysFfprobe}`));
      fs.cpSync(sysFfprobe, targetFfprobePath);
      fs.chmodSync(targetFfprobePath, 0o755);
    } else {
      console.log(colors.yellow('   ⚠️  Could not locate ffprobe binary to package.'));
    }

    console.log(colors.green('   ✓ Sidecar assets successfully prepared'));

    // 6. Run Vercel Pkg compiler to build final CLI binary
    console.log(colors.cyan('\n6. Executing Vercel Pkg compiler...'));
    
    // Build binary targeting current platform
    const platformMap = {
      darwin: 'macos',
      linux: 'linux',
      win32: 'win'
    };
    const arch = process.arch === 'arm64' ? 'arm64' : 'x64';
    const pkgTarget = `node18-${platformMap[process.platform] || 'macos'}-${arch}`;
    const outputBinaryName = process.platform === 'win32' ? 'arena.exe' : 'arena';
    const finalOutputPath = path.join(DIST_DIR, outputBinaryName);

    console.log(colors.gray(`   Target: ${pkgTarget}`));
    console.log(colors.gray(`   Output: ${finalOutputPath}`));

    const pkgResult = spawnSync('npx', ['pkg', 'package.json', '--targets', pkgTarget, '--out-path', DIST_DIR], {
      cwd: CLI_DIR,
      stdio: 'inherit'
    });

    if (pkgResult.status !== 0) {
      throw new Error(`pkg command failed with status ${pkgResult.status}`);
    }

    // Clean up temporary bin folders inside cli/dist
    console.log(colors.gray('\n7. Cleaning up temporary folders...'));
    fs.rmSync(path.join(CLI_DIST_DIR, 'bin'), { recursive: true, force: true });
    console.log(colors.green('   ✓ Cleaned up temporary files'));

    console.log(colors.bold(colors.green('\n🎉 SUCCESS! STANDALONE ARENA CLI COMPILED SUCCESSFULLY!')));
    console.log(colors.white(`   Location: ${colors.bold(finalOutputPath)}`));
    console.log(colors.gray(`   Size: ${(fs.statSync(finalOutputPath).size / (1024 * 1024)).toFixed(1)} MB`));
    console.log(colors.gray('   This single binary contains the Node CLI, Python Engine, Whisper, PyTorch, and FFmpeg sidecars.\n'));

  } catch (error) {
    console.error(colors.red(`\n❌ Build failed: ${error.message}\n`));
    process.exit(1);
  }
}

main();
