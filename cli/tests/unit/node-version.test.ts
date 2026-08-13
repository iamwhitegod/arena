import { describe, expect, it } from 'vitest';
import {
  isSupportedNodeVersion,
  parseNodeMajor,
  unsupportedNodeVersionMessage,
} from '../../src/core/node-version.js';

describe('Node.js version support', () => {
  it.each([
    ['v22.0.0', 22],
    ['24.9.1', 24],
    ['25', 25],
  ])('parses %s', (version, expected) => {
    expect(parseNodeMajor(version)).toBe(expected);
  });

  it('rejects malformed versions', () => {
    expect(parseNodeMajor('current')).toBeNull();
  });

  it.each([
    ['21.7.0', false],
    ['22.0.0', true],
    ['23.4.1', true],
    ['24.9.0', true],
    ['25.0.0', false],
  ])('evaluates %s as supported=%s', (version, expected) => {
    expect(isSupportedNodeVersion(version)).toBe(expected);
  });

  it('returns an actionable unsupported-version message', () => {
    expect(unsupportedNodeVersionMessage('20.15.0')).toBe(
      'Arena requires Node.js 22–24; found v20.15.0. ' +
        'Install a supported LTS release from https://nodejs.org/ and try again.'
    );
    expect(unsupportedNodeVersionMessage('22.23.2')).toBeNull();
  });
});
