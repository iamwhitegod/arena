import { createRequire } from 'node:module';
import path from 'node:path';

import { describe, expect, it } from 'vitest';

const require = createRequire(import.meta.url);
const {
  npmCliCandidates,
  parseArgs,
  packageBinEntry,
  resolveInvocation,
} = require('../../scripts/consumer-install-smoke.cjs');

describe('consumer install smoke command resolution', () => {
  it('keeps Windows paths with spaces and Unicode as distinct arguments', () => {
    const command = {
      executable: 'C:\\Program Files\\nodejs\\node.exe',
      args: ['C:\\Program Files\\nodejs\\node_modules\\npm\\bin\\npm-cli.js'],
      displayName: 'npm',
    };

    expect(
      resolveInvocation(command, [
        'install',
        '--prefix',
        'C:\\Temp\\arena consumer smoke\\npm prefix ø',
      ])
    ).toEqual({
      executable: command.executable,
      args: [
        command.args[0],
        'install',
        '--prefix',
        'C:\\Temp\\arena consumer smoke\\npm prefix ø',
      ],
      displayName: 'npm',
    });
  });

  it('prefers npm_execpath before the npm CLI beside node.exe', () => {
    expect(
      npmCliCandidates(
        'C:\\hostedtoolcache\\windows\\node\\24\\x64\\node.exe',
        'D:\\custom npm\\npm-cli.js',
        'win32'
      )
    ).toEqual([
      'D:\\custom npm\\npm-cli.js',
      'C:\\hostedtoolcache\\windows\\node\\24\\x64\\node_modules\\npm\\bin\\npm-cli.js',
      'C:\\hostedtoolcache\\windows\\node\\24\\lib\\node_modules\\npm\\bin\\npm-cli.js',
    ]);
  });

  it('resolves the packaged Arena launcher without accepting absolute bin paths', () => {
    expect(packageBinEntry({ bin: { arena: 'dist/launcher.js' } }, 'arena')).toBe(
      path.join('dist', 'launcher.js')
    );
    expect(() => packageBinEntry({ bin: { arena: '/tmp/launcher.js' } }, 'arena')).toThrow(
      'does not define a valid arena executable'
    );
    expect(() => packageBinEntry({ bin: { arena: '../launcher.js' } }, 'arena')).toThrow(
      'does not define a valid arena executable'
    );
  });

  it('requires one installation input and an exact registry version', () => {
    expect(() => parseArgs([])).toThrow('Exactly one of');
    expect(() => parseArgs(['--tarball', 'arena.tgz', '--source-dir', 'cli'])).toThrow(
      'Exactly one of'
    );
    expect(() =>
      parseArgs([
        '--package-spec',
        '@whitegodkingsley/arena-cli@next',
        '--expected-version',
        'next',
      ])
    ).toThrow('must be an exact semantic version');
    expect(
      parseArgs([
        '--package-spec',
        '@whitegodkingsley/arena-cli@0.4.3-rc.1',
        '--expected-version',
        '0.4.3-rc.1',
      ])
    ).toMatchObject({
      packageSpec: '@whitegodkingsley/arena-cli@0.4.3-rc.1',
      expectedVersion: '0.4.3-rc.1',
    });
  });
});
