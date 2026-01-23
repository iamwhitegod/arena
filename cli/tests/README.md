# Arena CLI Testing Guide

## 🎯 Testing Strategy

Arena uses a comprehensive 3-tier testing approach:

1. **Unit Tests** - Test individual functions and modules in isolation
2. **Integration Tests** - Test how components work together
3. **E2E Tests** - Test complete workflows from CLI to output

## 📁 Test Structure

```
tests/
├── setup.ts                 # Global test configuration
├── unit/                    # Unit tests
│   ├── validation.test.ts
│   ├── config.test.ts
│   └── ...
├── integration/             # Integration tests
│   ├── process-command.test.ts
│   ├── analyze-command.test.ts
│   └── ...
├── e2e/                     # End-to-end tests
│   └── full-workflow.test.ts
├── fixtures/                # Test data
│   ├── test-config.json
│   ├── test-analysis.json
│   └── test-video.mp4
└── mocks/                   # Mock implementations
    └── python-bridge.mock.ts
```

## 🚀 Running Tests

### Run all tests
```bash
npm test
```

### Run tests in watch mode
```bash
npm run test:watch
```

### Run with coverage
```bash
npm run test:coverage
```

### Run specific test file
```bash
npm test validation.test.ts
```

### Run tests with UI
```bash
npm run test:ui
```

## 📊 Coverage Goals

We aim for **70%+ coverage** across all metrics:
- Lines: 70%
- Functions: 70%
- Branches: 70%
- Statements: 70%

## ✍️ Writing Tests

### Unit Test Example

```typescript
import { describe, it, expect } from 'vitest';
import { myFunction } from '../src/module.js';

describe('MyModule', () => {
  it('should do something', () => {
    const result = myFunction('input');
    expect(result).toBe('expected output');
  });
});
```

### Integration Test Example

```typescript
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { MyCommand } from '../src/commands/my-command.js';
import { MockPythonBridge } from './mocks/python-bridge.mock.js';

vi.mock('../src/bridge/python-bridge.js', () => ({
  PythonBridge: MockPythonBridge,
}));

describe('MyCommand Integration', () => {
  it('should execute command', async () => {
    await expect(MyCommand('arg')).resolves.not.toThrow();
  });
});
```

## 🧪 Test Fixtures

Test fixtures are located in `tests/fixtures/`:
- `test-config.json` - Sample configuration
- `test-analysis.json` - Sample analysis output
- `test-video.mp4` - Small test video (not committed)

## 🎭 Mocking

We mock the Python bridge in tests to:
- Speed up tests (no actual Python execution)
- Make tests deterministic
- Avoid requiring OpenAI API key
- Test error scenarios

## ⏭️ Skipping Tests

Use `.skip` for tests that require external resources:

```typescript
it.skip('should process real video', async () => {
  // This test requires a real video file and API key
});
```

## 🐛 Debugging Tests

```bash
# Run tests with verbose output
npm test -- --reporter=verbose

# Run single test file
npm test validation.test.ts

# Debug in VS Code
# Add breakpoint and use "JavaScript Debug Terminal"
```

## 📈 CI/CD Integration

Tests run automatically on:
- Every commit (via pre-commit hook)
- Every push (via GitHub Actions)
- Before publishing (via prepublishOnly)

## 🔧 Troubleshooting

### Tests failing locally but passing in CI
- Check Node.js version (requires 18+)
- Clear node_modules and reinstall
- Check for environment-specific issues

### Coverage below threshold
- Add tests for uncovered files
- Check coverage report: `open coverage/index.html`

### Mock not working
- Ensure mock is imported before the module being tested
- Use `vi.mock()` at the top of test file

## 📚 Resources

- [Vitest Documentation](https://vitest.dev)
- [Testing Best Practices](https://github.com/goldbergyoni/javascript-testing-best-practices)
- [Mocking Guide](https://vitest.dev/guide/mocking.html)
