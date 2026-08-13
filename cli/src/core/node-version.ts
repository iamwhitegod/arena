export const MIN_NODE_MAJOR = 22;
// Exclusive upper bound: supported Node.js majors are 22, 23, and 24.
export const MAX_NODE_MAJOR_EXCLUSIVE = 25;
export const SUPPORTED_NODE_RANGE = '22–24';

export function parseNodeMajor(version: string): number | null {
  const match = /^v?(\d+)(?:\.|$)/.exec(version.trim());
  if (!match) {
    return null;
  }

  const major = Number.parseInt(match[1], 10);
  return Number.isInteger(major) ? major : null;
}

export function isSupportedNodeVersion(version = process.versions.node): boolean {
  const major = parseNodeMajor(version);
  return major !== null && major >= MIN_NODE_MAJOR && major < MAX_NODE_MAJOR_EXCLUSIVE;
}

export function unsupportedNodeVersionMessage(version = process.versions.node): string | null {
  if (isSupportedNodeVersion(version)) {
    return null;
  }

  return (
    `Arena requires Node.js ${SUPPORTED_NODE_RANGE}; found v${version}. ` +
    'Install a supported LTS release from https://nodejs.org/ and try again.'
  );
}
