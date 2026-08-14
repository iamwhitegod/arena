import { describe, expect, it } from 'vitest';
import { requiredProviders } from '../../src/core/providers.js';

describe('requiredProviders', () => {
  it('uses the global provider as shorthand', () => {
    expect(
      requiredProviders({ provider: 'openai' }, ['chat', 'embedding', 'transcription'])
    ).toEqual(['openai']);
  });

  it('uses per-capability providers when present', () => {
    expect(
      requiredProviders({ provider: 'openai', transcriptionProvider: 'openai' }, [
        'chat',
        'transcription',
      ])
    ).toEqual(['openai']);
  });

  it('makes overview chat fall back to the chat provider', () => {
    expect(requiredProviders({ chatProvider: 'openai' }, ['overviewChat'])).toEqual(['openai']);
  });
});
