import { describe, expect, it } from 'vitest';
import {
  providerSupportsCapability,
  requiredProviderBindings,
  requiredProviders,
  resolveProviderSelectors,
} from '../../src/core/providers.js';

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

describe('requiredProviderBindings', () => {
  it('resolves Ollama defaults for chat and embeddings', () => {
    expect(requiredProviderBindings({ provider: 'ollama' }, ['chat', 'embedding'])).toEqual([
      { capability: 'chat', provider: 'ollama', model: 'llama3.2' },
      { capability: 'embedding', provider: 'ollama', model: 'nomic-embed-text' },
    ]);
  });

  it('preserves custom Ollama models', () => {
    expect(
      requiredProviderBindings(
        { provider: 'ollama', chatModel: 'qwen3:8b', embeddingModel: 'mxbai-embed-large' },
        ['chat', 'embedding']
      )
    ).toEqual([
      { capability: 'chat', provider: 'ollama', model: 'qwen3:8b', modelExplicit: true },
      {
        capability: 'embedding',
        provider: 'ollama',
        model: 'mxbai-embed-large',
        modelExplicit: true,
      },
    ]);
  });

  it('declares that Ollama does not support transcription', () => {
    expect(providerSupportsCapability('ollama', 'transcription')).toBe(false);
    expect(providerSupportsCapability('ollama', 'chat')).toBe(true);
  });

  it('does not crash while resolving an untrusted stored provider name', () => {
    expect(requiredProviderBindings({ provider: 'untrusted' as any }, ['chat'])).toEqual([
      { capability: 'chat', provider: 'untrusted', model: undefined },
    ]);
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
