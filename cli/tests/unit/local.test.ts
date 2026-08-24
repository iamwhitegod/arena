import { describe, expect, it, vi } from 'vitest';
import { validateLocalReadiness } from '../../src/core/local.js';

describe('validateLocalReadiness', () => {
  it('skips the probe when no local capability is required', async () => {
    const probe = vi.fn();
    await validateLocalReadiness([{ capability: 'chat', provider: 'openai' }], probe);
    expect(probe).not.toHaveBeenCalled();
  });

  it('probes only local capability bindings', async () => {
    const probe = vi.fn().mockResolvedValue(undefined);
    const local = { capability: 'transcription' as const, provider: 'local' as const };
    await validateLocalReadiness([local, { capability: 'chat', provider: 'openai' }], probe);
    expect(probe).toHaveBeenCalledWith([local]);
  });

  it('normalizes probe failures into an actionable preflight error', async () => {
    await expect(
      validateLocalReadiness([{ capability: 'chat', provider: 'local' }], async () => {
        throw new Error('native details');
      })
    ).rejects.toMatchObject({ code: 'LOCAL_NOT_READY' });
  });
});
