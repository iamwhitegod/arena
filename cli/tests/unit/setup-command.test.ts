import { describe, expect, it } from 'vitest';
import {
  runtimeImportProbe,
  runtimeRequirementsLock,
  nativeCompilerChecks,
  windowsVswherePaths,
} from '../../src/commands/setup.js';

describe('local runtime setup selection', () => {
  it('keeps the core runtime as the default', () => {
    expect(runtimeRequirementsLock(false)).toBe('requirements.lock');
    expect(runtimeImportProbe(false)).not.toContain('llama_cpp');
    expect(runtimeImportProbe(false)).toContain('requests');
  });

  it('selects the complete hash-locked local dependency graph', () => {
    expect(runtimeRequirementsLock(true)).toBe('requirements-local.lock');
    expect(runtimeImportProbe(true)).toContain('llama_cpp');
    expect(runtimeImportProbe(true)).toContain('faster_whisper');
    expect(runtimeImportProbe(true)).toContain('ctranslate2');
  });

  it('uses platform-native compiler probes without a shell', () => {
    expect(nativeCompilerChecks('darwin')).toEqual([['xcrun', ['--find', 'clang']]]);
    expect(nativeCompilerChecks('linux')[0]).toEqual(['cc', ['--version']]);
    expect(nativeCompilerChecks('win32')[0]).toEqual(['where.exe', ['cl.exe']]);
  });

  it('discovers standard Visual Studio installer locations', () => {
    expect(windowsVswherePaths({ 'ProgramFiles(x86)': 'C:\\PF86' })).toEqual([
      'C:\\PF86/Microsoft Visual Studio/Installer/vswhere.exe',
    ]);
  });
});
