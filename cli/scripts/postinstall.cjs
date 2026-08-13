#!/usr/bin/env node

/**
 * Read-only npm lifecycle check.
 *
 * Heavy dependency installation belongs to the explicit `arena setup`
 * command, never to npm postinstall. This script does not use a shell, make
 * network requests, or modify the host system.
 */

const { spawn } = require('child_process');
const fs = require('fs');
const os = require('os');
const path = require('path');

const color = process.stdout.isTTY
  ? {
      cyan: (text) => `\x1b[36m${text}\x1b[0m`,
      green: (text) => `\x1b[32m${text}\x1b[0m`,
      yellow: (text) => `\x1b[33m${text}\x1b[0m`,
      gray: (text) => `\x1b[90m${text}\x1b[0m`,
    }
  : { cyan: String, green: String, yellow: String, gray: String };

function commandWorks(command, args) {
  return new Promise((resolve) => {
    // `where.exe` recognizes PATHEXT entries such as Chocolatey's .cmd
    // wrappers without executing them through a shell.
    const useWindowsLookup = process.platform === 'win32' && !path.isAbsolute(command);
    const child = spawn(
      useWindowsLookup ? 'where.exe' : command,
      useWindowsLookup ? [command] : args,
      {
        shell: false,
        stdio: 'ignore',
        windowsHide: true,
      }
    );
    let settled = false;
    const finish = (available) => {
      if (!settled) {
        settled = true;
        clearTimeout(timer);
        resolve(available);
      }
    };
    const timer = setTimeout(() => {
      child.kill();
      finish(false);
    }, 15000);
    child.once('error', () => finish(false));
    child.once('close', (code) => finish(code === 0));
  });
}

async function main() {
  const arenaHome = process.env.ARENA_HOME
    ? path.resolve(process.env.ARENA_HOME)
    : path.join(os.homedir(), '.arena');
  const manifestPath = path.join(arenaHome, 'runtime', 'install.json');
  let pythonPath = path.join(
    arenaHome,
    'runtime',
    'python',
    process.platform === 'win32' ? 'Scripts' : 'bin',
    process.platform === 'win32' ? 'python.exe' : 'python'
  );
  try {
    const manifest = JSON.parse(fs.readFileSync(manifestPath, 'utf8'));
    if (typeof manifest.pythonPath === 'string') {
      pythonPath = manifest.pythonPath;
    }
  } catch {
    // A missing manifest means setup has not completed yet.
  }

  const [ffmpeg, ffprobe] = await Promise.all([
    commandWorks('ffmpeg', ['-version']),
    commandWorks('ffprobe', ['-version']),
  ]);
  const runtime = fs.existsSync(pythonPath) && (await commandWorks(pythonPath, ['--version']));

  console.log(color.cyan('\nArena CLI installed.'));
  if (runtime && ffmpeg && ffprobe) {
    console.log(color.green('Your Arena processing runtime is ready.'));
    console.log(color.gray('Verify it with: arena setup --check\n'));
  } else {
    console.log(color.yellow('One explicit setup step remains:'));
    console.log('  arena setup');
    console.log(color.gray('This creates a private Python environment and verifies FFmpeg.\n'));
  }
}

main().catch(() => {
  // npm installation must not fail because a read-only advisory check failed.
  console.log('\nArena CLI installed. Run `arena setup` to finish installation.\n');
});
