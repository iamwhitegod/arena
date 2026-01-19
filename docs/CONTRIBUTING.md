# Contributing to Arena CLI

Thank you for your interest in contributing to Arena CLI! This document provides guidelines and instructions for contributing.

## Code of Conduct

Be respectful, inclusive, and constructive in all interactions with the community.

## Getting Started

### Prerequisites

- Node.js 18 or higher
- Python 3.9 or higher
- FFmpeg
- Git

### Development Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/YOUR_USERNAME/arena.git
   cd arena/cli
   ```

2. Install dependencies:
   ```bash
   npm install
   ```

3. Run tests:
   ```bash
   npm test
   ```

4. Build the CLI:
   ```bash
   npm run build
   ```

5. Run in development mode:
   ```bash
   npm run dev -- process video.mp4
   ```

## Development Workflow

### Project Structure

```
cli/
├── src/
│   ├── commands/         # CLI command implementations
│   ├── core/             # Core modules (config, preflight, workspace)
│   ├── bridge/           # Python bridge for video processing
│   ├── ui/               # UI components (progress, summary, formatters)
│   ├── errors/           # Error handling framework
│   ├── validation/       # Input validation
│   └── index.ts          # CLI entry point
├── tests/
│   ├── unit/             # Unit tests
│   ├── integration/      # Integration tests (future)
│   └── e2e/              # End-to-end tests (future)
├── dist/                 # Compiled output
└── docs/                 # Additional documentation
```

### Making Changes

1. Create a feature branch:
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. Make your changes following our coding standards:
   - Use TypeScript
   - Follow ESLint rules (`npm run lint`)
   - Format with Prettier (`npm run format`)
   - Add tests for new functionality
   - Update documentation if needed

3. Run tests locally:
   ```bash
   npm test
   npm run build
   npm run lint
   ```

4. Commit your changes:
   ```bash
   git add .
   git commit -m "feat: add your feature description"
   ```

   Follow [Conventional Commits](https://www.conventionalcommits.org/):
   - `feat:` - New feature
   - `fix:` - Bug fix
   - `docs:` - Documentation changes
   - `test:` - Adding or updating tests
   - `refactor:` - Code refactoring
   - `chore:` - Build process or tooling changes

5. Push to your fork and create a pull request:
   ```bash
   git push origin feature/your-feature-name
   ```

## Testing

### Running Tests

```bash
# Run all tests
npm test

# Run tests in watch mode
npm run test:watch

# Run tests with coverage
npm run test:coverage

# Run tests with UI
npm run test:ui
```

### Writing Tests

- Place unit tests in `tests/unit/`
- Test files should end with `.test.ts`
- Use descriptive test names
- Follow the AAA pattern: Arrange, Act, Assert

Example:
```typescript
import { describe, it, expect } from 'vitest';
import { formatDuration } from '../../src/ui/formatters.js';

describe('formatDuration', () => {
  it('should format seconds only', () => {
    expect(formatDuration(45)).toBe('45s');
  });
});
```

## Coding Standards

### TypeScript

- Use explicit types where helpful, rely on inference where obvious
- Avoid `any` types (use `unknown` if needed)
- Use interfaces for object shapes
- Export types that are part of the public API

### Error Handling

- Use custom error classes (PreflightError, ProcessingError, SystemError)
- Provide actionable error messages with suggestions
- Include documentation links where helpful

### User Experience

- Provide clear, concise CLI messages
- Use progress indicators for long operations
- Format output for readability
- Include helpful examples in error messages

## Pull Request Process

1. Update the README.md if you add/change functionality
2. Update CHANGELOG.md with your changes
3. Add tests for new features
4. Ensure all tests pass
5. Ensure code passes linting
6. Request review from maintainers

### Pull Request Checklist

- [ ] Tests pass (`npm test`)
- [ ] Build succeeds (`npm run build`)
- [ ] Linter passes (`npm run lint`)
- [ ] Documentation updated (if needed)
- [ ] CHANGELOG.md updated
- [ ] Commit messages follow Conventional Commits
- [ ] PR has descriptive title and description

## Reporting Bugs

Before creating bug reports, please check existing issues to avoid duplicates.

When creating a bug report, include:

- **Description**: Clear description of the issue
- **Steps to Reproduce**: Detailed steps to reproduce the behavior
- **Expected Behavior**: What you expected to happen
- **Actual Behavior**: What actually happened
- **Environment**:
  - OS and version
  - Node.js version
  - Python version
  - Arena CLI version
- **Logs**: Include relevant error messages or logs
- **Screenshots**: If applicable

## Suggesting Features

Feature suggestions are welcome! When suggesting a feature:

1. Check existing issues/PRs to avoid duplicates
2. Describe the problem you're trying to solve
3. Describe your proposed solution
4. Consider alternative solutions
5. Explain why this feature would be useful to most users

## Documentation

Documentation improvements are always welcome:

- Fix typos or unclear explanations
- Add examples
- Improve command descriptions
- Add troubleshooting guides

## Release Process

Releases are managed by maintainers:

1. Update version in `package.json`
2. Update CHANGELOG.md
3. Create git tag: `git tag v1.2.3`
4. Push tag: `git push origin v1.2.3`
5. Create GitHub release
6. GitHub Actions will automatically publish to npm

## Questions?

Feel free to open an issue for questions or discussions.

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
