import { defineConfig } from 'vitest/config';

export default defineConfig({
  test: {
    globals: true,
    environment: 'node',
    pool: 'forks', // Use forks instead of threads to allow process.chdir()
    coverage: {
      provider: 'v8',
      reporter: ['text', 'json', 'html', 'lcov'],
      exclude: [
        'node_modules/',
        'dist/',
        '**/*.d.ts',
        '**/*.config.*',
        '**/tests/**',
        '**/test/**',
      ],
      thresholds: {
        lines: 28, // Baseline - improve over time
        functions: 50,
        branches: 70,
        statements: 28, // Baseline - improve over time
      },
    },
    include: ['src/**/*.{test,spec}.ts', 'tests/**/*.{test,spec}.ts'],
    exclude: ['node_modules', 'dist'],
    testTimeout: 30000,
  },
});
