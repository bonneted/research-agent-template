# Off-limits material is guarded in every repository and the workspace root

Some workspaces hold material an agent must never read: a consortium's confidential documents, a partner's data, e-mail. Whatever an agent reads goes to the model provider. The rule alone ("never open it") depends on every agent remembering it, and a session can start in any repository or in the workspace root. So the manifest lists the material (`off_limits`: path globs, patterns on tool-call arguments, connectors, an off-limits repository) and `ws sync` writes the guards everywhere a session can start: deny rules and a PreToolUse hook in `.claude/settings.json`, merged into the repository's own file, the hook script and its patterns, and `.ignore` for Grep and Glob. The hook, generalised from copv-reliability's `guard_confidential.py`, matches a path as a whole name in any spelling, and fails closed without its patterns. An off-limits repository is cloned (so its owner works from the workspace) but never linked, mounted, listed, fetched or checked.

The files are written out of git, like every other link and file `ws sync` makes, so a public repository never carries a workspace's list of confidential names, and a change of the list does not need a commit in every repository.

## Considered options

- **Commit the guard files in each repository.** The guards would hold in a fresh clone before `ws sync`; but every repository, the library included, would carry the list of names, and every change of it would be a commit everywhere. A repository that tracks its own `.claude/settings.json` gets the merge in place, reported to be committed.

## Consequences

The guards are a second line behind the rules in `AGENTS.md`, not a wall: a command that reaches the material without naming it is not caught, the deny rules bind Claude Code only, and a session on a machine where `ws sync` has not run is unguarded. The README says so.
