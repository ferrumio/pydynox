# Agent skill

The `using-pydynox` skill helps coding assistants build applications with
pydynox. It covers models, CRUD, async and sync methods, queries, pagination,
batch operations, transactions, and application tests.

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

The skill checks the application's installed version and points to focused
references for the task. The included examples use APIs available in pydynox
1.8.0 and run with `MemoryBackend`, or with LocalStack for SDK and transaction
tests. Their commands are in the skill's testing reference.

The skill follows the [Agent Skills format](https://agentskills.io/specification).
Its source lives beside the library, and the Python test suites exercise its
examples. Contributors working on pydynox itself should start with the
repository's `AGENTS.md`.
