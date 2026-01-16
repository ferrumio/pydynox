# Architecture Decision Records (ADR)

This folder contains Architecture Decision Records - documents that capture important decisions made during the project's development.

## What is an ADR?

An ADR is a short document that describes a decision, why it was made, and what the consequences are. It helps future contributors understand the "why" behind the codebase.

## ADRs in this project

| # | Title | Status |
|---|-------|--------|
| 001 | [Single client.rs file](001-single-client-file.md) | Accepted |
| 002 | [Why Rust](002-why-rust.md) | Accepted |
| 003 | [Rust vs Python](003-rust-vs-python.md) | Accepted |
| 004 | [Model and Client API](004-model-and-client-api.md) | Accepted |
| 005 | [Why pytest](005-why-pytest.md) | Accepted |
| 006 | [Unit vs Integration tests](006-unit-vs-integration-tests.md) | Accepted |
| 007 | [Why Zensical](007-why-zensical.md) | Accepted |
| 008 | [Examples in folder](008-examples-in-folder.md) | Accepted |
| 009 | [Supported platforms](009-supported-platforms.md) | Accepted |
| 010 | [GenAI in development](010-genai-in-development.md) | Accepted |
| 011 | [Prepare/Execute pattern](011-prepare-execute-pattern.md) | Accepted |
| 012 | [Envelope encryption with KMS](012-envelope-encryption-kms.md) | Accepted |
| 013 | [OpenTelemetry tracing](013-opentelemetry-tracing.md) | Accepted |
| 014 | [as_dict parameter](014-as-dict-parameter.md) | Accepted |
| 015 | [Metrics API redesign](015-metrics-api-redesign.md) | Accepted |
| 016 | [Unified AWS client config](016-unified-aws-client-config.md) | Accepted |

## Adding a new ADR

1. Create a new file: `NNN-short-title.md`
2. Use the template below
3. Add to the table above

## Template

```markdown
# ADR NNN: Title

## Status

Proposed | Accepted | Deprecated | Superseded

## Context

What is the issue or question?

## Decision

What did we decide?

## Reasons

Why did we decide this?

## Alternatives considered

What else did we consider?

## Consequences

What are the results of this decision?
```
