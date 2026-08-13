import { describe, expect, it } from 'vitest';
import { redactSensitiveData } from '../../src/utils/logger.js';

describe('logger redaction', () => {
  it('redacts sensitive fields recursively', () => {
    expect(
      redactSensitiveData({
        apiKey: 'sk-super-secret-value',
        nested: { authorization: 'Bearer hidden', safe: 'visible' },
      })
    ).toEqual({
      apiKey: '[REDACTED]',
      nested: { authorization: '[REDACTED]', safe: 'visible' },
    });
  });

  it('redacts secrets embedded in messages and arrays', () => {
    expect(
      redactSensitiveData([
        'request used sk-abcdefghijklmnopqrstuvwxyz',
        'Authorization=top-secret',
        'Bearer abc123',
      ])
    ).toEqual(['request used [REDACTED]', 'Authorization=[REDACTED]', 'Bearer [REDACTED]']);
  });
});
