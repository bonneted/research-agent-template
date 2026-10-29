# Tooling refuses what breaks a rule, and `ws check` checks what a machine can tell

A rule an agent can forget is weaker than a tool that refuses. So the run stamp refuses a confirm run from a dirty tree, and from a `PLAN.md` whose protocol is not the one frozen for the phase: freezing records the hash of the phase's protocol (the shared text of the Protocol section and the phase's own subsection, comments aside) in its `config.yaml`, and refreezing a changed protocol needs a deviation logged first. The stamp also records each conda environment a run used, by the hash of its explicit package list, and the workspace's own fields (`stamp_extras`).

What cannot be refused at run time is checked by `ws check`, which a repository's CI can run: finding front matter against its schema, evidence permalinks against the clones, citations against the bibliographies, a number beside a citation with no page (a warning), phases with their notes and types, confirm phases frozen at their current protocol, selected rule packs present, conda environments against their pinned files, and the off-limits files. Everything else is in the agent rules.

The freeze is one module, `ws`'s `protocol.py`, copied into each study at spawn as `study/protocol.py`, so the stamp and `ws check` hash alike.

## Considered options

- **Freeze by a git tag.** Rejected: the tag says when, not what; the hash says exactly which text was fixed, and survives a rebase.

## Consequences

A study whose protocol changes mid-phase must log it before it can run again. `ws check` reads only local clones and conda: a study not cloned is not checked, and the permalinks of its findings are taken on trust there.
