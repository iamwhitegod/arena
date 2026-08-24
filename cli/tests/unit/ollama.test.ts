import { describe, expect, it } from 'vitest';
import { PreflightError } from '../../src/errors/index.js';
import { validateOllamaReadiness } from '../../src/core/ollama.js';

describe('validateOllamaReadiness', () => {
  it('accepts installed models and latest aliases', async () => {
    await expect(
      validateOllamaReadiness(['llama3.2', 'nomic-embed-text'], async () => ({
        models: [{ name: 'llama3.2:latest' }, { model: 'nomic-embed-text:latest' }],
      }))
    ).resolves.toBeUndefined();
  });

  it('reports every missing model with pull commands', async () => {
    try {
      await validateOllamaReadiness(['llama3.2', 'nomic-embed-text'], async () => ({ models: [] }));
      expect.fail('Expected a missing-model error');
    } catch (error) {
      expect(error).toBeInstanceOf(PreflightError);
      expect((error as PreflightError).code).toBe('OLLAMA_MODEL_MISSING');
      expect((error as PreflightError).suggestion).toContain('ollama pull llama3.2');
      expect((error as PreflightError).suggestion).toContain('ollama pull nomic-embed-text');
    }
  });

  it('rejects malformed server responses', async () => {
    await expect(
      validateOllamaReadiness(['llama3.2'], async () => ({ models: 'bad' }))
    ).rejects.toMatchObject({
      code: 'OLLAMA_INVALID_RESPONSE',
    });
  });

  it('rejects terminal control characters in model names', async () => {
    await expect(
      validateOllamaReadiness(['llama3.2\nmalicious'], async () => ({ models: [] }))
    ).rejects.toMatchObject({ code: 'INVALID_MODEL' });
  });
});
