import { beforeEach, describe, expect, it, vi } from 'vitest';

const mockSpinner = {
  text: '',
  isSpinning: false,
  start: vi.fn(function (this: typeof mockSpinner) {
    this.isSpinning = true;
    return this;
  }),
  succeed: vi.fn(),
  fail: vi.fn(),
  stop: vi.fn(),
  info: vi.fn(),
  warn: vi.fn(),
};

vi.mock('ora', () => ({
  default: () => mockSpinner,
}));

vi.mock('chalk', () => {
  const identity = (value: string) => value;
  return {
    default: {
      blue: identity,
      bold: identity,
      cyan: identity,
      gray: identity,
      green: identity,
      red: identity,
      white: identity,
      yellow: identity,
    },
  };
});
import { ProgressTracker } from '../../src/ui/progress.js';

describe('ProgressTracker stage updates', () => {
  beforeEach(() => {
    mockSpinner.text = '';
    mockSpinner.isSpinning = false;
    vi.clearAllMocks();
  });

  it('renders the first stage progress value instead of dropping it', () => {
    const tracker = new ProgressTracker();
    tracker.initializeStages([{ id: 'transcription', name: 'Transcription' }]);

    tracker.updateStage('transcription', 5, 'Preparing audio');

    expect(mockSpinner.text).toContain('5%');
    expect(mockSpinner.text).toContain('Preparing audio');
  });

  it('does not move a stage backwards when delayed events arrive', () => {
    const tracker = new ProgressTracker();
    tracker.initializeStages([{ id: 'transcription', name: 'Transcription' }]);

    tracker.updateStage('transcription', 40, 'Transcribing audio');
    tracker.updateStage('transcription', 20, 'Delayed preparation event');

    expect(mockSpinner.text).toContain('40%');
    expect(mockSpinner.text).not.toContain('20%');
  });

  it('ignores delayed events for a stage that is already complete', () => {
    const tracker = new ProgressTracker();
    tracker.initializeStages([{ id: 'transcription', name: 'Transcription' }]);

    tracker.updateStage('transcription', 100, 'Transcription complete');
    tracker.updateStage('transcription', 40, 'Delayed chunk event');

    expect(mockSpinner.text).toContain('Transcription complete');
    expect(mockSpinner.text).not.toContain('Delayed chunk event');
  });

  it('shows elapsed time instead of a percentage for indeterminate work', () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date('2026-08-14T12:00:00Z'));

    try {
      const tracker = new ProgressTracker();
      tracker.initializeStages([{ id: 'transcription', name: 'Transcription' }]);

      tracker.updateStage('transcription', 30, 'Audio prepared');
      tracker.updateStage('transcription', null, 'Transcribing audio');

      expect(mockSpinner.text).toContain('◐ Transcribing audio · 0s elapsed');
      expect(tracker.getOverallProgress()).toBe(30);

      vi.advanceTimersByTime(2000);
      expect(mockSpinner.text).toContain('◐ Transcribing audio · 2s elapsed');

      tracker.stop();
      expect(vi.getTimerCount()).toBe(0);
    } finally {
      vi.useRealTimers();
    }
  });

  it('computes overall progress from verified stage checkpoints', () => {
    const tracker = new ProgressTracker();
    tracker.initializeStages([
      { id: 'transcription', name: 'Transcription' },
      { id: 'analysis', name: 'Analysis' },
    ]);

    tracker.updateStage('transcription', 40, 'Transcribing audio');

    expect(tracker.getOverallProgress()).toBe(20);
    expect(mockSpinner.text).toContain('Overall');
    expect(mockSpinner.text).toContain('20%');
  });

  it('adds elapsed time to simple indeterminate commands', () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date('2026-08-14T12:00:00Z'));

    try {
      const tracker = new ProgressTracker();
      tracker.showIndeterminate('Encoding video');

      expect(mockSpinner.text).toContain('Encoding video · 0s elapsed');
      vi.advanceTimersByTime(3000);
      expect(mockSpinner.text).toContain('Encoding video · 3s elapsed');

      tracker.showDeterminate(75, 'Finalizing');
      expect(vi.getTimerCount()).toBe(0);
      expect(mockSpinner.text).toContain('75%');
    } finally {
      vi.useRealTimers();
    }
  });
});
