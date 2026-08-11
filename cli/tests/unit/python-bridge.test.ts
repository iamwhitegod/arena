import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { EventEmitter } from 'events';

// Mock child_process before importing PythonBridge
const mockSpawn = vi.fn();
vi.mock('child_process', () => ({
  spawn: (...args: any[]) => mockSpawn(...args),
}));

// Mock chalk to avoid color output in tests
vi.mock('chalk', () => ({
  default: {
    gray: (s: string) => s,
    red: (s: string) => s,
    yellow: (s: string) => s,
    cyan: (s: string) => s,
  },
}));

// Mock fs-extra
vi.mock('fs-extra', () => ({
  default: {
    ensureDirSync: vi.fn(),
    existsSync: vi.fn().mockReturnValue(false),
    copySync: vi.fn(),
    chmodSync: vi.fn(),
  },
}));

import { PythonBridge } from '../../src/bridge/python-bridge.js';
import { ProcessingError, SystemError } from '../../src/errors/index.js';

/**
 * Creates a mock ChildProcess with controllable stdout, stderr, and lifecycle events.
 */
function createMockProcess() {
  const stdout = new EventEmitter();
  const stderr = new EventEmitter();
  const proc = new EventEmitter() as EventEmitter & {
    stdout: EventEmitter;
    stderr: EventEmitter;
    killed: boolean;
    kill: ReturnType<typeof vi.fn>;
  };
  proc.stdout = stdout;
  proc.stderr = stderr;
  proc.killed = false;
  proc.kill = vi.fn(() => {
    proc.killed = true;
  });
  return proc;
}

describe('PythonBridge', () => {
  let bridge: PythonBridge;
  let exitListeners: Map<string, (...args: any[]) => void>;

  beforeEach(() => {
    vi.clearAllMocks();
    // Capture process signal handlers to prevent real listeners
    exitListeners = new Map();
    vi.spyOn(process, 'on').mockImplementation((event: string, handler: any) => {
      exitListeners.set(event, handler);
      return process;
    });
    bridge = new PythonBridge();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe('stdout JSON parsing', () => {
    it('should call onProgress for progress updates', async () => {
      const mockProc = createMockProcess();
      mockSpawn.mockReturnValue(mockProc);

      const onProgress = vi.fn();
      const promise = bridge.runProcess({ videoPath: '/test.mp4', outputDir: '/out' }, onProgress);

      // Emit a progress JSON line
      mockProc.stdout.emit(
        'data',
        Buffer.from(
          '{"type":"progress","stage":"transcription","progress":50,"message":"Transcribing..."}\n'
        )
      );
      mockProc.emit('close', 0);

      await promise;

      expect(onProgress).toHaveBeenCalledWith({
        stage: 'transcription',
        progress: 50,
        message: 'Transcribing...',
      });
    });

    it('should resolve with data for result updates', async () => {
      const mockProc = createMockProcess();
      mockSpawn.mockReturnValue(mockProc);

      const promise = bridge.runProcess({ videoPath: '/test.mp4', outputDir: '/out' });

      mockProc.stdout.emit(
        'data',
        Buffer.from('{"type":"result","data":{"clips":[{"title":"Test"}]}}\n')
      );
      // close also fires, but result should have already resolved
      mockProc.emit('close', 0);

      const result = await promise;
      expect(result).toEqual({ clips: [{ title: 'Test' }] });
    });

    it('should buffer incomplete lines until newline arrives', async () => {
      const mockProc = createMockProcess();
      mockSpawn.mockReturnValue(mockProc);

      const onProgress = vi.fn();
      const promise = bridge.runProcess({ videoPath: '/test.mp4', outputDir: '/out' }, onProgress);

      // Send partial JSON
      mockProc.stdout.emit('data', Buffer.from('{"type":"progress","stage":'));
      expect(onProgress).not.toHaveBeenCalled();

      // Complete the line
      mockProc.stdout.emit(
        'data',
        Buffer.from('"analysis","progress":75,"message":"Analyzing..."}\n')
      );
      expect(onProgress).toHaveBeenCalledWith({
        stage: 'analysis',
        progress: 75,
        message: 'Analyzing...',
      });

      mockProc.emit('close', 0);
      await promise;
    });
  });

  describe('stderr handling', () => {
    it('should forward stderr to onError callback', async () => {
      const mockProc = createMockProcess();
      mockSpawn.mockReturnValue(mockProc);

      const onError = vi.fn();
      const promise = bridge.runProcess(
        { videoPath: '/test.mp4', outputDir: '/out' },
        undefined,
        onError
      );

      mockProc.stderr.emit('data', Buffer.from('Python warning: something'));
      mockProc.emit('close', 0);

      await promise;
      expect(onError).toHaveBeenCalledWith('Python warning: something');
    });
  });

  describe('exit codes', () => {
    it('should resolve with success on exit code 0', async () => {
      const mockProc = createMockProcess();
      mockSpawn.mockReturnValue(mockProc);

      const promise = bridge.runProcess({ videoPath: '/test.mp4', outputDir: '/out' });

      mockProc.emit('close', 0);

      const result = await promise;
      expect(result).toEqual({ success: true });
    });

    it('should reject with ProcessingError on non-zero exit code', async () => {
      const mockProc = createMockProcess();
      mockSpawn.mockReturnValue(mockProc);

      const promise = bridge.runProcess({ videoPath: '/test.mp4', outputDir: '/out' });

      mockProc.stderr.emit('data', Buffer.from('RuntimeError: API call failed\n'));
      mockProc.emit('close', 1);

      await expect(promise).rejects.toThrow(ProcessingError);
      await expect(promise).rejects.toThrow(/API call failed/);
    });

    it('should reject with SystemError INTERRUPTED on exit code 130', async () => {
      const mockProc = createMockProcess();
      mockSpawn.mockReturnValue(mockProc);

      const promise = bridge.runProcess({ videoPath: '/test.mp4', outputDir: '/out' });

      mockProc.emit('close', 130);

      await expect(promise).rejects.toThrow(SystemError);
      try {
        await promise;
      } catch (e: any) {
        expect(e.code).toBe('INTERRUPTED');
      }
    });
  });

  describe('spawn errors', () => {
    it('should reject with SystemError PYTHON_START_FAILED on spawn error', async () => {
      const mockProc = createMockProcess();
      mockSpawn.mockReturnValue(mockProc);

      const promise = bridge.runProcess({ videoPath: '/test.mp4', outputDir: '/out' });

      mockProc.emit('error', new Error('ENOENT'));

      await expect(promise).rejects.toThrow(SystemError);
      try {
        await promise;
      } catch (e: any) {
        expect(e.code).toBe('PYTHON_START_FAILED');
        expect(e.message).toContain('ENOENT');
      }
    });
  });

  describe('parseErrorFromOutput', () => {
    it('should extract Error: line from Python traceback', async () => {
      const mockProc = createMockProcess();
      mockSpawn.mockReturnValue(mockProc);

      const promise = bridge.runProcess({ videoPath: '/test.mp4', outputDir: '/out' });

      mockProc.stderr.emit(
        'data',
        Buffer.from(
          'Traceback (most recent call last):\n' +
            '  File "main.py", line 10, in <module>\n' +
            'ValueError: Invalid video format\n'
        )
      );
      mockProc.emit('close', 1);

      try {
        await promise;
      } catch (e: any) {
        expect(e.message).toContain('ValueError: Invalid video format');
      }
    });

    it('should return last meaningful line if no Error: found', async () => {
      const mockProc = createMockProcess();
      mockSpawn.mockReturnValue(mockProc);

      const promise = bridge.runProcess({ videoPath: '/test.mp4', outputDir: '/out' });

      mockProc.stderr.emit('data', Buffer.from('Something went wrong\n'));
      mockProc.emit('close', 1);

      try {
        await promise;
      } catch (e: any) {
        expect(e.message).toContain('Something went wrong');
      }
    });

    it('should use generic message for empty stderr', async () => {
      const mockProc = createMockProcess();
      mockSpawn.mockReturnValue(mockProc);

      const promise = bridge.runProcess({ videoPath: '/test.mp4', outputDir: '/out' });

      mockProc.emit('close', 1);

      try {
        await promise;
      } catch (e: any) {
        expect(e.message).toContain('Processing failed with exit code 1');
      }
    });
  });

  describe('checkPythonEnvironment', () => {
    it('should return available with version on success', async () => {
      const mockProc = createMockProcess();
      mockSpawn.mockReturnValue(mockProc);

      const promise = bridge.checkPythonEnvironment();

      mockProc.stdout.emit('data', Buffer.from('Python 3.11.5'));
      mockProc.emit('close', 0);

      const result = await promise;
      expect(result).toEqual({ available: true, version: 'Python 3.11.5' });
    });

    it('should return unavailable on non-zero exit', async () => {
      const mockProc = createMockProcess();
      mockSpawn.mockReturnValue(mockProc);

      const promise = bridge.checkPythonEnvironment();

      mockProc.emit('close', 1);

      const result = await promise;
      expect(result.available).toBe(false);
      expect(result.error).toBeDefined();
    });

    it('should return unavailable on spawn error', async () => {
      const mockProc = createMockProcess();
      mockSpawn.mockReturnValue(mockProc);

      const promise = bridge.checkPythonEnvironment();

      mockProc.emit('error', new Error('ENOENT'));

      const result = await promise;
      expect(result.available).toBe(false);
    });
  });

  describe('checkDependencies', () => {
    it('should return installed when import succeeds', async () => {
      const mockProc = createMockProcess();
      mockSpawn.mockReturnValue(mockProc);

      const promise = bridge.checkDependencies();

      mockProc.stdout.emit('data', Buffer.from('ok'));
      mockProc.emit('close', 0);

      const result = await promise;
      expect(result).toEqual({ installed: true });
    });

    it('should return not installed when import fails', async () => {
      const mockProc = createMockProcess();
      mockSpawn.mockReturnValue(mockProc);

      const promise = bridge.checkDependencies();

      mockProc.emit('close', 1);

      const result = await promise;
      expect(result.installed).toBe(false);
      expect(result.missing).toContain('arena engine dependencies');
    });

    it('should return not installed on spawn error', async () => {
      const mockProc = createMockProcess();
      mockSpawn.mockReturnValue(mockProc);

      const promise = bridge.checkDependencies();

      mockProc.emit('error', new Error('ENOENT'));

      const result = await promise;
      expect(result.installed).toBe(false);
    });
  });

  describe('command argument building', () => {
    it('should pass all process options as CLI args', async () => {
      const mockProc = createMockProcess();
      mockSpawn.mockReturnValue(mockProc);

      const promise = bridge.runProcess({
        videoPath: '/test.mp4',
        outputDir: '/out',
        clipCount: 5,
        minDuration: 30,
        maxDuration: 120,
        use4Layer: true,
        fast: true,
        padding: 2,
      });

      mockProc.emit('close', 0);
      await promise;

      // Check the args passed to spawn
      const spawnArgs = mockSpawn.mock.calls[0][1];
      expect(spawnArgs).toContain('/test.mp4');
      expect(spawnArgs).toContain('-o');
      expect(spawnArgs).toContain('/out');
      expect(spawnArgs).toContain('-n');
      expect(spawnArgs).toContain('5');
      expect(spawnArgs).toContain('--min');
      expect(spawnArgs).toContain('30');
      expect(spawnArgs).toContain('--max');
      expect(spawnArgs).toContain('120');
      expect(spawnArgs).toContain('--use-4layer');
      expect(spawnArgs).toContain('--fast');
      expect(spawnArgs).toContain('--padding');
      expect(spawnArgs).toContain('2');
    });

    it('should omit undefined optional args', async () => {
      const mockProc = createMockProcess();
      mockSpawn.mockReturnValue(mockProc);

      const promise = bridge.runProcess({
        videoPath: '/test.mp4',
        outputDir: '/out',
      });

      mockProc.emit('close', 0);
      await promise;

      const spawnArgs = mockSpawn.mock.calls[0][1];
      expect(spawnArgs).not.toContain('-n');
      expect(spawnArgs).not.toContain('--min');
      expect(spawnArgs).not.toContain('--use-4layer');
    });
  });

  describe('shutdown handling', () => {
    it('should reject immediately if shutdown is in progress', async () => {
      // Trigger shutdown via captured SIGINT handler
      const sigintHandler = exitListeners.get('SIGINT');
      if (sigintHandler) {
        // Mock process.exit to prevent actual exit
        const exitSpy = vi.spyOn(process, 'exit').mockImplementation(() => {
          throw new Error('exit');
        });
        try {
          await sigintHandler();
        } catch {
          // Expected: process.exit throws
        }
        exitSpy.mockRestore();
      }

      // Now trying to run should reject with INTERRUPTED
      await expect(
        bridge.runProcess({ videoPath: '/test.mp4', outputDir: '/out' })
      ).rejects.toThrow(SystemError);
    });
  });
});
