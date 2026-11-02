# Confidential material is kept out of scope, and guarded by the harness, not the kit

The workspace template guarded off-limits material in every repository: a list out of git, a PreToolUse hook, deny rules merged into each settings file, inherited by copy and checked. It was built for a workspace whose confidential documents were cloned beside its studies, where a session at the root could search straight into them.

An inquiry's scope is its folder, so keeping confidential material out of an inquiry costs nothing: it is not put there. What remains — keeping an agent from material elsewhere on the same machine, or behind a connector — is a property of the machine and the harness, not of the research, and the harness already has it (Claude Code's `permissions.deny` in the user's or the project's local settings). So the kit has no off-limits rule, file, hook or check; the README says where to set it up.

## Considered options

- **Keep the machinery** (the workspace template's ADR 0007): a list, a hook, inheritance by copy, a `check` that the child's list covers the parent's. Most of a slice of code for a case most inquiries never have, duplicating the harness.
- **An optional `confidential` rule pack** with the hook and a setup guide. Still harness configuration presented as a research rule.

## Consequences

A tree that needs a guard sets it once per machine, at the folder that holds the tree or in the user's settings, where it covers every inquiry below it. The kit's rules never name confidential material.
