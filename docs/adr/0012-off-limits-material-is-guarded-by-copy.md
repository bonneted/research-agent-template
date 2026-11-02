# Off-limits material is guarded in every inquiry, inherited by copy, never committed

Some inquiries hold material an agent must never read; what an agent reads goes to the model provider, and a session can start in any inquiry. So an inquiry lists its off-limits material (path globs, patterns, connectors) in `.off-limits.yaml`, gitignored so that a public inquiry never carries confidential names. Spawn and adopt copy the inherited union into the child and write the guards: deny rules and a PreToolUse hook in `.claude/settings.json`, and `.ignore` for Grep and Glob. It is the one inheritance made by copy, not by link: a missing link would fail open. `check` verifies a child's list is a superset of its parent's when the parent is present.

Carried from the workspace template's ADR 0007. **To confirm with the user**: the grilling placed `off_limits` in `inquiry.yaml`, which is committed.

## Consequences

The guards are a second line behind the rule in `AGENTS.md`, not a wall: a command that reaches the material without naming it is not caught, deny rules bind Claude Code only, and a fresh clone is unguarded until the list is restored. The alignment step and the README say so.
