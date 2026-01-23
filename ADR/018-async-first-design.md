# ADR 018: Async-first design

## Status

Accepted

## Context

pydynox started with sync operations and added async later. This led to problems:

1. **Feature parity gaps** - Some sync features are missing in async
2. **Docs lag behind** - Async examples are incomplete or missing
3. **Tests focus on sync** - Async tests are an afterthought
4. **API inconsistencies** - Some async methods have different signatures or missing properties

Modern Python apps (FastAPI, aiohttp) are async-first. Our users expect async to work as well as sync.

## Decision

pydynox is now async-first. This means:

1. **Design async first** - New features start with async API, sync wraps it
2. **Feature parity** - Every sync feature must have an async equivalent
3. **Same API** - Async methods have identical parameters and return types
4. **Docs highlight async** - Async should be prominent in documentation, not hidden
5. **Test parity** - Every sync test needs an async test

### Checklist for new features

- [ ] Async implementation in Rust
- [ ] Async Python wrapper
- [ ] Sync wrapper (calls async internally or has separate impl)
- [ ] Async tests
- [ ] Sync tests
- [ ] Async docs/examples (shown first or equally)
- [ ] Sync docs/examples

### Documentation guidelines

- Show async examples alongside sync, not as an afterthought
- Use tabs to show both versions when possible
- Async should not be buried at the bottom of pages

## Reasons

1. **FastAPI adoption** - Most popular Python web framework is async
2. **User feedback** - Users report missing features in async API
3. **Maintenance burden** - Easier to maintain one pattern than two divergent ones
4. **Concurrent operations** - Async allows running multiple DynamoDB calls in parallel

## Consequences

- More work upfront for new features
- Better user experience for async users
- Easier to maintain long-term
- Need to audit existing code for gaps
- Docs need review and updates

## Action items

1. Audit all sync features for async parity
2. Review docs for async coverage and prominence
3. Add async examples where missing
4. Fix any API inconsistencies between sync and async
