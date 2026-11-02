# Agent skill

The `using-pydynox` skill helps coding assistants build applications with
pydynox. It explains how to choose an operation, handle its results, and test
the application's behavior with async and sync APIs.

| Task | What the skill covers |
|------|-----------------------|
| Pagination | Streaming, "load more", `limit` vs `page_size`, cursor boundaries, empty filtered pages, and exhaustion |
| Queries and indexes | Sort-key ranges, filters, descending order, GSI/LSI, projections, scans, and counts |
| Writes | Create-only conditions, atomic updates, batch operations, transaction rollback, and retry decisions |
| Models | Attributes, aliases, Decimal, key templates, TTL, smart save, hooks, and optimistic locking |
| Integrations | Pydantic, dataclasses, S3, KMS, compression, and feature-specific guide links |
| Operations | Credentials, timeouts, consistency, throttling, concurrency, and metrics |
| Testing | MemoryBackend limits and executable LocalStack recipes |

## Install

From your application project, run:

```bash
npx skills add ferrumio/pydynox --skill using-pydynox
```

The installer lets you choose which coding assistant receives the skill.
It requires Node.js/npm. This installs agent instructions in your project;
install the Python library in your application environment as usual:

```bash
pip install pydynox
```

You can also copy the complete
[`skills/using-pydynox` directory](https://github.com/ferrumio/pydynox/tree/main/skills/using-pydynox)
into the skill directory supported by your coding assistant. Keep its
`references/` and `examples/` directories together.

## Use it

Ask your coding assistant to use `using-pydynox`, for example:

> Use using-pydynox to add an Order model, query orders by customer, and test
> the application without AWS.

Or ask for a specific application behavior:

> Use using-pydynox to implement "load more" for a customer's paid orders.
> Return a continuation cursor, keep descending order, and test that no orders
> are skipped when some DynamoDB pages contain no matches.

The skill checks the application's installed version and routes the assistant
to a focused reference and runnable Python recipes. Pagination is also explained
in the main `SKILL.md`, including the cursor problem when iteration stops with
unread items in a fetched page.

The basic example runs on pydynox 1.8.0 with `MemoryBackend`, or with LocalStack
for pagination and transactions. The additional query recipes use LocalStack
for GSI, projections, and scans. Empty filtered-page recipes require the fix
merged in [PR #565](https://github.com/ferrumio/pydynox/pull/565) after 1.8.0.
The skill's testing reference contains the commands and version notes.

The skill follows the [Agent Skills format](https://agentskills.io/specification).
Its source lives beside the library, and the Python test suites exercise its
examples. Contributors working on pydynox itself should start with the
repository's `AGENTS.md`.
