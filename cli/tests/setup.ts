/**
 * Global test setup
 * Runs before all tests
 */

import { beforeAll, afterAll, vi } from 'vitest';
import path from 'path';
import fs from 'fs-extra';

// Test directories
export const TEST_DIR = path.join(__dirname, `tmp-${Math.random().toString(36).substring(2, 9)}`);
export const FIXTURES_DIR = path.join(__dirname, 'fixtures');
export const MOCKS_DIR = path.join(__dirname, 'mocks');

// Setup before all tests
beforeAll(async () => {
  // Create temporary test directory
  await fs.ensureDir(TEST_DIR);

  // Set test environment variables
  process.env.NODE_ENV = 'test';
  process.env.ARENA_TEST_MODE = 'true';

  // Mock console methods to reduce noise in tests
  vi.spyOn(console, 'log').mockImplementation(() => {});
  vi.spyOn(console, 'error').mockImplementation(() => {});

  console.log('🧪 Test environment initialized');
});

// Cleanup after all tests
afterAll(async () => {
  // Clean up temporary test directory
  try {
    // Check if directory exists before trying to remove
    if (await fs.pathExists(TEST_DIR)) {
      // First empty the directory to remove all contents
      await fs.emptyDir(TEST_DIR);
      // Then remove the directory itself
      await fs.remove(TEST_DIR);
    }
  } catch (error) {
    // Ignore cleanup errors - they're not critical
    // Most common errors are ENOENT (already removed) or ENOTEMPTY (race condition)
  }

  // Restore console
  vi.restoreAllMocks();

  console.log('✓ Test cleanup complete');
});

// Helper to create isolated test directory
export async function createTestDir(name: string): Promise<string> {
  const dir = path.join(TEST_DIR, name);
  await fs.ensureDir(dir);
  return dir;
}

// Helper to clean up test directory
export async function cleanTestDir(dir: string): Promise<void> {
  try {
    // Check if directory exists before trying to remove
    if (await fs.pathExists(dir)) {
      // Use stronger removal method
      await fs.emptyDir(dir);
      await fs.remove(dir);
    }
  } catch (error) {
    // Ignore cleanup errors - they're not critical for test functionality
    // Most common errors are ENOENT (already removed) or ENOTEMPTY (race condition)
  }
}
