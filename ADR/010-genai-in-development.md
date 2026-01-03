# ADR 010: GenAI in development

## Status

Accepted

## Context

GenAI tools (Claude, GPT, Copilot, Kiro) are transforming software development. This project embraces them as accelerators while maintaining code quality.

## Decision

Use GenAI as a development accelerator, not a replacement for understanding.

## How we use GenAI

### Code generation

- Boilerplate code (test fixtures, repetitive patterns)
- Initial implementations that we then refine
- Docstrings and documentation
- Error messages

### Documentation

- First drafts of guides and ADRs
- Code examples
- API documentation

### NOT used for

- Architecture decisions without human review
- Security-critical code without careful review
- Blindly accepting generated code

## Guidelines for contributors

### Do

- Use GenAI to accelerate your work
- Review and understand what it generates
- Test the generated code
- Adapt it to match project patterns

### Don't

- Submit code you don't understand
- Let GenAI drive without you steering
- Skip testing because "the AI wrote it"
- Ignore project patterns and style

## Project support for GenAI

We created two resources:

### `.ai/` folder - For AI agents

Guidelines that agentic IDEs (Cursor, Windsurf, Kiro) can read:

- `README.md` - Quick start
- `project-context.md` - What is pydynox
- `coding-guidelines.md` - Code style
- `testing-guidelines.md` - How to test
- `common-mistakes.md` - Things that break

### `ADR/` folder - For humans

Architecture Decision Records that explain the "why":

- Why Rust?
- When Python vs Rust?
- Why this testing strategy?

## Quality control

We reserve the right to reject PRs where:

- Project patterns are not followed
- Code is clearly unreviewed AI output
- Tests are missing or inadequate
- The contributor can't explain the code

## Philosophy

GenAI is a powerful tool. Like any tool, it's only as good as the person using it.

Be the developer, not the spectator.

## Consequences

- Faster development with AI assistance
- Clear guidelines for AI-assisted contributions
- Quality maintained through review process
- Both humans and AI agents have resources to work effectively
