import { describe, expect, it } from 'vitest';
import { requiredProviders, resolveProviderSelectors } from '../../src/core/providers.js';

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

describe('resolveProviderSelectors', () => {
  it('does not carry OpenAI models into an explicit local provider', () => {
    const resolved = resolveProviderSelectors(
      { provider: 'local' },
      {
        provider: 'openai',
        chat_model: 'gpt-4o-mini',
        embedding_model: 'text-embedding-3-small',
        transcription_model: 'whisper-1',
      }
    );

    expect(resolved.provider).toBe('local');
    expect(resolved.chatModel).toBeUndefined();
    expect(resolved.embeddingModel).toBeUndefined();
    expect(resolved.transcriptionModel).toBeUndefined();
  });

  it('keeps a stored model when its provider is unchanged', () => {
    const resolved = resolveProviderSelectors({}, { provider: 'local', chat_model: 'custom.gguf' });

    expect(resolved.provider).toBe('local');
    expect(resolved.chatModel).toBe('custom.gguf');
  });

  it('drops only the model for an overridden capability provider', () => {
    const resolved = resolveProviderSelectors(
      { transcriptionProvider: 'local' },
      { provider: 'openai', transcription_model: 'whisper-1' }
    );

    expect(resolved.chatProvider).toBeUndefined();
    expect(resolved.transcriptionProvider).toBe('local');
    expect(resolved.transcriptionModel).toBeUndefined();
  });
});
