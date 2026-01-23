# Testing Documentation

## Overview

Arena CLI has a comprehensive testing strategy with unit, integration, and end-to-end tests using Vitest.

## Test Structure

```
cli/tests/
├── unit/                    # Unit tests for individual modules
│   ├── config.test.ts      # ConfigManager tests (100% coverage)
│   ├── errors.test.ts      # Error handling tests (85% coverage)
│   ├── formatters.test.ts  # UI formatters tests (74% coverage)
│   ├── validation.test.ts  # Input validation tests (57% coverage)
│   └── workspace.test.ts   # Workspace tests (100% coverage)
├── integration/             # Integration tests
│   └── process-command.test.ts  # Process command integration (81% coverage)
├── e2e/                     # End-to-end tests
│   └── full-workflow.test.ts    # CLI workflow tests
├── fixtures/                # Test data
│   ├── test-config.json
│   └── test-analysis.json
├── mocks/                   # Mock implementations
│   └── python-bridge.mock.ts
└── setup.ts                 # Global test setup

```

## Running Tests

### Run all tests
```bash
npm test
```

### Run tests in watch mode
```bash
npm run test:watch
```

### Run tests with coverage
```bash
npm run test:coverage
```

### Run tests with UI
```bash
npm run test:ui
```

## Current Coverage

**Overall Coverage:**
- Lines: 28.46% (baseline)
- Functions: 51.06% ✓
- Branches: 73.97% ✓
- Statements: 28.46% (baseline)

**Module Coverage:**

| Module | Coverage | Status |
|--------|----------|--------|
| src/core/config.ts | 100% | ✅ Excellent |
| src/core/workspace.ts | 100% | ✅ Excellent |
| src/errors/formatter.ts | 84% | ✅ Good |
| src/errors/index.ts | 86% | ✅ Good |
| src/commands/process.ts | 82% | ✅ Good |
| src/ui/formatters.ts | 74% | ✅ Good |
| src/validation/index.ts | 57% | ⚠️ Fair |
| src/ui/progress.ts | 45% | ⚠️ Needs improvement |
| src/ui/summary.ts | 47% | ⚠️ Needs improvement |
| Other commands | 0% | ❌ Not tested |

**Not Yet Tested:**
- src/index.ts (CLI entry point)
- src/bridge/python-bridge.ts (mocked in tests)
- src/commands/analyze.ts
- src/commands/config.ts
- src/commands/detect-scenes.ts
- src/commands/extract-audio.ts
- src/commands/format.ts
- src/commands/generate.ts
- src/commands/init.ts
- src/commands/transcribe.ts
- src/core/preflight.ts (mocked in tests)

## Test Types

### Unit Tests

Test individual functions and classes in isolation.

**Example:**
```typescript
describe('ConfigManager', () => {
  it('should create default global config', async () => {
    const manager = new ConfigManager();
    await manager.ensureGlobalConfig();

    const config = await manager.getGlobalConfig();
    expect(config.whisper_mode).toBe('api');
  });
});
```

### Integration Tests

Test how components work together.

**Example:**
```typescript
describe('Process Command Integration', () => {
  it('should process video with 4-layer system', async () => {
    const videoPath = path.join(testDir, 'test.mp4');
    const options = { use4layer: true };

    await expect(processCommand(videoPath, options)).resolves.not.toThrow();
  });
});
```

### End-to-End Tests

Test complete CLI workflows.

**Example:**
```typescript
describe('Full Workflow E2E', () => {
  it('should display help', async () => {
    const { stdout } = await execAsync(`node "${CLI_PATH}" --help`);
    expect(stdout).toContain('AI-powered video clip generation');
  });
});
```

## Coverage Thresholds

Current thresholds are set to baseline levels to prevent regressions:

```typescript
thresholds: {
  lines: 28,      // Baseline - will increase to 70%
  functions: 50,  // Target: 70%
  branches: 70,   // ✓ Already meeting target
  statements: 28, // Baseline - will increase to 70%
}
```

## Roadmap to 70% Coverage

### Phase 1 (Current - 28% coverage) ✓
- ✅ Core modules tested (config, workspace, validation, errors)
- ✅ Main workflow tested (process command)
- ✅ Integration and E2E tests passing

### Phase 2 (Target: 40% coverage)
- Add tests for analyze command
- Add tests for generate command
- Add tests for format command
- Improve validation test coverage to 70%

### Phase 3 (Target: 55% coverage)
- Add tests for init command
- Add tests for transcribe command
- Add tests for config command
- Add tests for extract-audio command

### Phase 4 (Target: 70% coverage)
- Add tests for detect-scenes command
- Improve progress tracker test coverage
- Improve summary test coverage
- Add tests for preflight checks

## Writing Tests

### Guidelines

1. **Use descriptive test names** - Test names should clearly describe what is being tested
2. **Follow AAA pattern** - Arrange, Act, Assert
3. **Test one thing per test** - Each test should verify one specific behavior
4. **Use beforeEach/afterEach** - Clean up test state between tests
5. **Mock external dependencies** - Mock Python bridge, file system when appropriate

### Example Test

```typescript
describe('validateVideoFile', () => {
  let testDir: string;

  beforeEach(async () => {
    testDir = await createTestDir('validation-test');
  });

  afterEach(async () => {
    await cleanTestDir(testDir);
  });

  it('should validate existing video file', async () => {
    // Arrange
    const videoPath = path.join(testDir, 'test.mp4');
    await fs.writeFile(videoPath, 'fake video content');

    // Act & Assert
    await expect(validateVideoFile(videoPath)).resolves.not.toThrow();
  });

  it('should reject non-existent file', async () => {
    // Act & Assert
    try {
      await validateVideoFile('/non/existent/video.mp4');
      expect.fail('Should have thrown PreflightError');
    } catch (error) {
      expect(error).toBeInstanceOf(PreflightError);
      expect((error as PreflightError).code).toBe('VIDEO_NOT_FOUND');
    }
  });
});
```

## Continuous Improvement

### Coverage Goals

- **Short term** (v0.2.0): 40% coverage
- **Medium term** (v0.3.0): 55% coverage
- **Long term** (v1.0.0): 70% coverage

### Next Steps

1. Add unit tests for remaining commands
2. Add more integration tests for command combinations
3. Improve test coverage for UI modules (progress, summary)
4. Add performance tests for large video processing
5. Add tests for error recovery scenarios

## CI/CD Integration

Tests run automatically on:
- Every push to any branch
- Every pull request
- Before npm publish

Coverage reports are generated and can be viewed in:
- Terminal output
- HTML report: `coverage/index.html`
- LCOV report: `coverage/lcov.info` (for CI tools)

## Troubleshooting

### Tests failing with "process.chdir not supported"

The tests use `pool: 'forks'` in vitest.config.ts to allow process.chdir(). If you change this, config tests may fail.

### Tests failing with "process.exit unexpectedly called"

Integration tests mock process.exit to prevent test runner from exiting. Ensure the mock is properly set up in beforeEach.

### Coverage thresholds failing

If adding new files causes coverage to drop below thresholds:
1. Add tests for the new files
2. Or temporarily adjust thresholds (with plan to increase coverage)

## Contributing

When adding new features:
1. Write tests FIRST (TDD approach recommended)
2. Ensure all tests pass: `npm test`
3. Check coverage doesn't drop: `npm run test:coverage`
4. Update this document if adding new test patterns
