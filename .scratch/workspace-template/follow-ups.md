# Follow-ups of the workspace template

Not in this effort (see `spec.md`, "Follow-ups"); recorded here so they are not lost.

## Back-port spimat-hub onto the template

spimat-hub could become one configuration of the workspace template, as copv-hub is. What it takes:

1. Add `ws-template` as a remote of spimat-hub and merge it. Conflicts are expected in `tools/ws/`, `tests/`, `overlay/`, `skills/`, `README.md`, `AGENTS.md` and `docs/CONTEXT.md`: take the template's code and tests, keep spimat's own text and findings.
2. Write the `workspace` block of its manifest: `name: spimat`, `gitlab: https://gitlab.kuleuven.be/r2d/researchers/Damien/spimat`, `zotero_root: spimat`, `library: spimat` (its URL stays on `r2d/public/`, listed as now). No off-limits material.
3. Environment and configuration names stay as they were (`SPIMAT_RESOURCES`, `SPIMAT_SSH_HOST`): they now derive from the name. The retrieval configuration moves from `~/.config/spimat/retrieval.yaml` to `~/.config/research-ws/retrieval.yaml`, its Zotero keys under `workspaces: {spimat: ...}`.
4. Its library is public and its private context stays in `docs/library/`: `ws sync` keeps writing the library's local agent files, since the hub has that folder.
5. Its study rules become the core rules plus the `ml-training` pack; its rule 3 (claim type) is the Claim type section of `PLAN.md`, and its rule 11's "hard metered compute budget" goes into each study's protocol. Existing studies keep their `AGENTS.md` until they choose to take the new one (a deviation each).
6. Its findings carry plain permalink lists as evidence and a `spimat:` key: rewrite them to evidence items with kinds (`run`, with `phase` from each phase's config at the cited commit) and `library:`, then run `ws check --repo spimat-hub`. Its confirmed findings need a `review-finding` verdict, or go back to `hint` until reviewed.
7. `ask-spimat` becomes `skills/ask-spimat` filled from `skeleton/skills/ask-{{name}}`, keeping its spimat-specific rows (the recipe study's leaderboard, `spimat.experimental`).
8. `spawn` now also removes the template's `tests/test_refs.py`, `tests/fakes.py`, `tests/zotero-fields.json`, `talk/` and `uv.lock`, which spimat's spawn left in studies spawned from the template's latest commits.

## Other follow-ups

- pixi in place of the conda pattern (D8).
- `ws check` does not check a study's findings links against GitLab (network check left optional, not built).
- Removing `off_limits` from a manifest leaves the module's files where `ws sync` wrote them: delete them by hand.
