# Security Policy

## Supported versions

| Version | Supported |
|---------|-----------|
| 0.x.x   | ✅ Yes    |

We support the latest minor version. When 1.0 is released, we will support the latest patch of each minor version.

## Reporting a vulnerability

[Open a GitHub issue](https://github.com/ferrumio/pydynox/issues/new?labels=security) with the label `security`. We will prioritize it.

Include:
- Description of the issue
- Steps to reproduce (if possible)
- Potential impact

We will respond as soon as possible and work with you to fix the issue.

## Security practices

This project follows security best practices:

- Dependencies are kept minimal and up to date
- Rust code is memory-safe by default
- We use Dependabot for automated dependency updates
- Encryption features use AWS KMS (no custom crypto)
- No sensitive data is logged

Thank you for helping keep pydynox secure.
