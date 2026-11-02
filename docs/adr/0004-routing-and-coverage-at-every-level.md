# Every index routes to its sub-inquiries and maps their coverage

An agent asked a broad question must descend to the right branch without searching the whole tree. So every `docs/wiki/index.md` has a `## Sub-inquiries` section: one entry per child (a link to its index, its question, its status `active | closed | dormant`, what to dive there for — topics, quantities, methods — and its headline findings), then the sub-questions still open, then what is out of scope and why. A child updates its entry when it publishes upward.

The agent reads the index, picks a route, descends, repeats; it searches across the tree only when no route matches. The open and out-of-scope lines make coverage of an area visible: where the next inquiry goes, and what was left out on purpose.

## Considered options

- **One generated tree file at the root**: goes stale, and breaks when a subtree is adopted or detached.

## Consequences

Routing costs one index per level. `check` fails an `inquiry.yaml` child with no entry, and an entry with no child.
