# Rules first, and a small kit: text in each inquiry, tools in one pinned package

The product is the rules: how inquiries relate and what makes their knowledge grounded. Mechanisms an agent can rebuild from a rule do not belong in the template; a beginner's one inquiry has no code of its own.

The **text** — `AGENTS.md`, the skills, the rule packs — is copied into each inquiry, because the agent must read it and the user may tighten it; spawn copies the parent's, and `inquiry.yaml` records the template tag it came from. The **tools** — `refs`, `fetch`, `check` — are one `uv tool`, pinned in `inquiry.yaml` and run with `uvx`, so no Python is copied down the tree to drift.

## Considered options

- **Copy the tools too**: every nested inquiry would carry and test its own copy.
- **Skills as a harness plugin**: a repository would no longer explain itself, and other harnesses would lose them.

## Consequences

Upgrading an inquiry is a diff of its text against a newer tag, applied with the user's approval (`ask-tree`), and a version bump of the tool.
