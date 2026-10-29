# The workspace template is a hub template that wraps the research agent template

A workspace is built by a hub, and the template of a workspace is a hub at birth: `ws`, the study overlay, the rule packs and the hub skills, with a skeleton of the hub's own text. `ws init <name>` makes `<name>-hub` from it and keeps it as the `ws-template` remote, so fixes reach every hub by merge. The research agent template stays a single-project template, unchanged: studies are still spawned from it (`template` in the manifest), with the workspace's overlay applied.

It was built by extracting the spimat workspace's `ws`, its end-to-end tests, its overlay and its skills, then parameterising every workspace-specific name from the manifest's `workspace` block (the prefix of repositories, skills and environment variables, the Zotero root, the library, the stamp's extra fields, the off-limits material). Rewriting from scratch would have lost what spimat's tests already pinned down.

## Considered options

- **Put the workspace layer into the research agent template.** Rejected: a single project needs none of it, and the template's users would carry a hub's tooling.
- **A cookiecutter that generates hubs.** Rejected: a generated hub has no remote to merge fixes from.

## Consequences

The template's README is the manual every hub carries; only its opening is the hub's own (`skeleton/`). spimat-hub could adopt the template as one configuration of it; that back-port is a follow-up. A hub's own changes to `ws` go back to the template as a branch free of the workspace's names.
