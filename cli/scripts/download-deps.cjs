#!/usr/bin/env node

/**
 * Download and bundle Python + FFmpeg
 * Makes Arena completely self-contained
 */

const https = require('https');
const fs = require('fs-extra');
const path = require('path');
const { promisify } = require('util');
const { exec, spawn } = require('child_process');
const { pipeline } = require('stream');
const { createWriteStream, createReadStream } = require('fs');

const execAsync = promisify(exec);
const streamPipeline = promisify(pipeline);

const platform = process.platform;
const arch = process.arch;

const DEPS_DIR = path.join(__dirname, '../.arena-deps');
const PYTHON_DIR = path.join(DEPS_DIR, 'python');
const FFMPEG_DIR = path.join(DEPS_DIR, 'ffmpeg');

// Color helpers
const colors = {
  cyan: (text) => `\x1b[36m${text}\x1b[0m`,
  green: (text) => `\x1b[32m${text}\x1b[0m`,
  yellow: (text) => `\x1b[33m${text}\x1b[0m`,
  gray: (text) => `\x1b[90m${text}\x1b[0m`,
};

console.log('\n' + colors.cyan('📦 Downloading Arena dependencies...\n'));

async function downloadFile(url, dest) {
  await fs.ensureDir(path.dirname(dest));

  return new Promise((resolve, reject) => {
    console.log(colors.gray(`  Downloading from ${url.substring(0, 60)}...`));

    https.get(url, (response) => {
      if (response.statusCode === 302 || response.statusCode === 301) {
        // Follow redirect
        downloadFile(response.headers.location, dest).then(resolve).catch(reject);
      } else if (response.statusCode === 200) {
        const file = createWriteStream(dest);
        response.pipe(file);
        file.on('finish', () => {
          file.close();
          console.log(colors.green(`  ✓ Downloaded to ${path.basename(dest)}\n`));
          resolve();
        });
        file.on('error', (err) => {
          fs.unlink(dest, () => reject(err));
        });
      } else {
        reject(new Error(`HTTP ${response.statusCode}: ${url}`));
      }
    }).on('error', reject);
  });
}

async function extractTarGz(tarPath, extractPath) {
  await fs.ensureDir(extractPath);
  console.log(colors.gray(`  Extracting ${path.basename(tarPath)}...`));

  return new Promise((resolve, reject) => {
    const tar = spawn('tar', ['-xzf', tarPath, '-C', extractPath, '--strip-components=1'], {
      stdio: 'inherit'
    });

    tar.on('close', (code) => {
      if (code === 0) {
        console.log(colors.green(`  ✓ Extracted\n`));
        resolve();
      } else {
        reject(new Error(`tar extraction failed with code ${code}`));
      }
    });

    tar.on('error', (err) => {
      // tar not available, try manual extraction
      console.log(colors.yellow('  tar command not found, trying alternative...\n'));
      extractWithNode(tarPath, extractPath).then(resolve).catch(reject);
    });
  });
}

async function extractWithNode(tarPath, extractPath) {
  // Fallback extraction using Node
  const zlib = require('zlib');
  const tar = require('tar-fs');

  return streamPipeline(
    createReadStream(tarPath),
    zlib.createGunzip(),
    tar.extract(extractPath, {
      strip: 1
    })
  );
}

async function extractZip(zipPath, extractPath) {
  await fs.ensureDir(extractPath);
  console.log(colors.gray(`  Extracting ${path.basename(zipPath)}...`));

  const unzipper = require('unzipper');

  return streamPipeline(
    createReadStream(zipPath),
    unzipper.Extract({ path: extractPath })
  ).then(() => {
    console.log(colors.green(`  ✓ Extracted\n`));
  });
}

async function downloadPython() {
  console.log(colors.cyan('🐍 Python Standalone Build\n'));

  let url, filename, extract;

  if (platform === 'win32') {
    // Windows - Python embeddable package
    url = arch === 'x64'
      ? 'https://www.python.org/ftp/python/3.11.7/python-3.11.7-embed-amd64.zip'
      : 'https://www.python.org/ftp/python/3.11.7/python-3.11.7-embed-win32.zip';
    filename = 'python.zip';
    extract = extractZip;
  } else if (platform === 'darwin') {
    // macOS - Python.org standalone build
    if (arch === 'arm64') {
      url = 'https://www.python.org/ftp/python/3.11.7/python-3.11.7-macos11.pkg';
    } else {
      url = 'https://www.python.org/ftp/python/3.11.7/python-3.11.7-macosx10.9.pkg';
    }

    // For macOS, we'll use system Python or guide user
    console.log(colors.yellow('  On macOS, using system Python is recommended\n'));
    return;
  } else {
    // Linux - Python standalone build
    url = 'https://github.com/indygreg/python-build-standalone/releases/download/20231002/cpython-3.11.6+20231002-x86_64-unknown-linux-gnu-install_only.tar.gz';
    filename = 'python.tar.gz';
    extract = extractTarGz;
  }

  const downloadPath = path.join(DEPS_DIR, filename);

  try {
    await downloadFile(url, downloadPath);
    await extract(downloadPath, PYTHON_DIR);
    await fs.remove(downloadPath);

    // On Windows, download and install pip
    if (platform === 'win32') {
      const getPipPath = path.join(PYTHON_DIR, 'get-pip.py');
      await downloadFile('https://bootstrap.pypa.io/get-pip.py', getPipPath);

      const pythonExe = path.join(PYTHON_DIR, 'python.exe');
      await execAsync(`"${pythonExe}" "${getPipPath}"`);
      console.log(colors.green('  ✓ pip installed\n'));
    }

    console.log(colors.green('✓ Python installed\n'));
  } catch (error) {
    console.log(colors.yellow(`  Could not download Python: ${error.message}\n`));
    console.log(colors.gray('  Will use system Python if available\n'));
  }
}

async function downloadFFmpeg() {
  console.log(colors.cyan('🎬 FFmpeg Standalone Build\n'));

  let url, filename, extract;

  if (platform === 'win32') {
    // Windows
    url = 'https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip';
    filename = 'ffmpeg.zip';
    extract = extractZip;
  } else if (platform === 'darwin') {
    // macOS
    url = arch === 'arm64'
      ? 'https://evermeet.cx/ffmpeg/getrelease/zip'
      : 'https://evermeet.cx/ffmpeg/getrelease/zip';
    filename = 'ffmpeg.zip';
    extract = extractZip;
  } else {
    // Linux
    url = 'https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz';
    filename = 'ffmpeg.tar.xz';

    // For .tar.xz we need xz-utils
    extract = async (tarPath, extractPath) => {
      await fs.ensureDir(extractPath);
      console.log(colors.gray(`  Extracting ${path.basename(tarPath)}...`));

      try {
        await execAsync(`tar -xJf "${tarPath}" -C "${extractPath}" --strip-components=1`);
        console.log(colors.green(`  ✓ Extracted\n`));
      } catch (error) {
        throw new Error('tar with xz support required. Install: sudo apt-get install xz-utils');
      }
    };
  }

  const downloadPath = path.join(DEPS_DIR, filename);

  try {
    await downloadFile(url, downloadPath);
    await extract(downloadPath, FFMPEG_DIR);
    await fs.remove(downloadPath);

    console.log(colors.green('✓ FFmpeg installed\n'));
  } catch (error) {
    console.log(colors.yellow(`  Could not download FFmpeg: ${error.message}\n`));
    console.log(colors.gray('  Will use system FFmpeg if available\n'));
  }
}

async function installPythonPackages() {
  console.log(colors.cyan('📦 Installing Python packages...\n'));

  const packages = [
    'openai-whisper',
    'openai',
    'ffmpeg-python',
    'torch',
    'numpy',
    'scipy',
  ];

  // Determine pip command
  let pipCmd = 'pip3';

  if (platform === 'win32' && await fs.pathExists(path.join(PYTHON_DIR, 'python.exe'))) {
    pipCmd = path.join(PYTHON_DIR, 'Scripts', 'pip.exe');
  } else if (await fs.pathExists(path.join(PYTHON_DIR, 'bin', 'pip3'))) {
    pipCmd = path.join(PYTHON_DIR, 'bin', 'pip3');
  }

  return new Promise((resolve) => {
    const pip = spawn(pipCmd, ['install', '--user', ...packages], {
      stdio: 'inherit',
    });

    pip.on('close', (code) => {
      if (code === 0) {
        console.log('\n' + colors.green('✓ Python packages installed\n'));
        resolve(true);
      } else {
        console.log('\n' + colors.yellow('⚠️  Some packages may need manual installation\n'));
        resolve(false);
      }
    });

    pip.on('error', () => {
      console.log('\n' + colors.yellow('⚠️  Could not install packages automatically\n'));
      resolve(false);
    });
  });
}

async function saveConfig() {
  // Save paths configuration
  const config = {
    pythonPath: platform === 'win32'
      ? path.join(PYTHON_DIR, 'python.exe')
      : path.join(PYTHON_DIR, 'bin', 'python3'),
    ffmpegPath: platform === 'win32'
      ? path.join(FFMPEG_DIR, 'bin', 'ffmpeg.exe')
      : path.join(FFMPEG_DIR, 'ffmpeg'),
    pipPath: platform === 'win32'
      ? path.join(PYTHON_DIR, 'Scripts', 'pip.exe')
      : path.join(PYTHON_DIR, 'bin', 'pip3'),
    bundled: true,
  };

  await fs.writeJson(path.join(__dirname, '../.arena-config.json'), config, {
    spaces: 2,
  });

  console.log(colors.green('✓ Configuration saved\n'));
}

async function main() {
  try {
    // Create deps directory
    await fs.ensureDir(DEPS_DIR);

    // Download Python
    await downloadPython();

    // Download FFmpeg
    await downloadFFmpeg();

    // Save configuration
    await saveConfig();

    // Install Python packages
    await installPythonPackages();

    console.log(colors.green('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n'));
    console.log(colors.green('✅ Arena is ready to use!\n'));
    console.log(colors.cyan('Quick start:\n'));
    console.log(colors.gray('  export OPENAI_API_KEY="sk-..."\n'));
    console.log(colors.gray('  arena process video.mp4 -p tiktok\n'));

  } catch (error) {
    console.error(colors.yellow('\n⚠️  Setup incomplete: ' + error.message + '\n'));
    console.log(colors.gray('Run "arena setup" to complete installation\n'));

    // Don't fail npm install
    process.exit(0);
  }
}

main();
