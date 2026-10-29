---
name: ask-{{name}}
description: Ask what to do next anywhere in the {{name}} workspace. A router over its commands, the study lifecycle, where knowledge goes, and which skill fits each step.
disable-model-invocation: true
---

# Ask {{name}}

Answer the user's question with the **next action**: the command to run, the file to edit, or the skill to type, from the map below. Read the file a line points to before answering from it; the map names where the answer lives, those files are the truth. Use the glossary's words (`<hub>/docs/CONTEXT.md`).

**Where you are.** The workspace is the siblings of one folder. `<hub>` below is the hub: `.` inside `{{hub}}`, `../{{hub}}` from the library, a study (`{{name}}-<topic>`) or an app. An app has no study lifecycle: its work in progress is its own `.scratch/`. A study's state is its `PLAN.md` (phases table, deviations) and `git status`; the hub's work in progress is `<hub>/.scratch/`. Off-limits material (`off_limits` in `<hub>/workspace.yaml`) is never read: ask the user for what you need from it.

## The workspace

Run from the hub; `<hub>/README.md` says what each prints and when it fails.

- **`uv run ws sync`**: clone what is missing, link the pool, mount the studies, link the hub skills, write the off-limits files. After cloning the hub, after `workspace.yaml` or `skills/` changes, or when a link or mount is missing. Read its `FAILED` lines first.
- **`uv run ws fetch`**: pull every `references.bib` from Zotero, then retrieve the resources every manifest lists into the pool. After adding a resource, or on a new machine; paste the `rsync` line it ends with on a machine that has the rest.
- **`uv run ws refs add <doi | arXiv id | URL>`**: add a reference to the Zotero collection of the repository it is run from (or `--repo <name>`; from a study, `uv run --directory ../{{hub}} ws refs add --repo <study> <id>`), and pull. Never write BibTeX; a thesis, report or slides goes into Zotero by hand. Then `ws fetch` for its PDF.
- **`uv run ws refs pull`**: rewrite that repository's `references.bib` from its Zotero collection, after changing the collection in Zotero. Commit the bib; heed its warnings on removed entries still cited.
- **`uv run ws spawn <topic>`**: a new study. Then do what its output says: create the GitLab project, push, commit the hub's `workspace.yaml` and `docs/studies/index.md`, and create the Zotero collection if `ws` could not.
- **`uv run ws check`** (`--repo <name>`, `--all`): the repository against the workspace's rules. Before committing a finding, and at the end of a phase.

## The study lifecycle

Rules are the **core rules** of the study's `AGENTS.md` (`<hub>/overlay/AGENTS.md`) and the **rule packs** its `PLAN.md` selects (`rules/<pack>.md`); cite them by number.

1. **Spawn** the study (above).
2. **Plan.** Fill `PLAN.md`: the question, the claim type, the rule packs. Sharpen them with `/grill-with-docs`, which keeps the study's terms in its `docs/CONTEXT.md`.
3. **Phase.** Start each with the **prior-work check** (`AGENTS.md`, "A phase", step 1). Add the phase to `PLAN.md` as explore or confirm (core rule 1); a confirm phase writes its protocol there and **freezes** it before its first run (`uv run python -m study.protocol freeze phases/NN-slug`), `/grilling` to stress-test it. Build `phases/NN-slug/` (`run.py`, `report.py`, `config.yaml`) and shared code in `study/` test-first with `/tdd`; verify the method on a known case first (core rule 2); `/prototype` for a design question, `/diagnosing-bugs` when a run misbehaves.
4. **Runs.** Every run is stamped by `study/stamp.py` (core rule 3). A solver uv cannot install is a conda environment in `environments/<name>.yml`, listed in the phase's `config.yaml`. After a pin bump or an environment change, rerun the **canary runs** of `PLAN.md` (core rule 8).
5. **Report.** `report.py` gives the phase's results; write them, negative ones included, into the phase note `docs/wiki/phases/NN-slug.md`, every number with its unit, its uncertainty and its source, and follow `update-wiki` for the rest of the wiki.
6. **Publish.** At the end of the phase, `/publish-finding` turns the phase's claims into findings in the hub, each a **hint**, **confirmed**, **retracted** or **superseded** with evidence of a kind (`<hub>/docs/findings/finding-format.md`); one that would be confirmed goes through `/review-finding` first.
7. **Promotion.** Code one study built and a second study needs goes into the library: a library merge request that names no study, then a **pin bump** in each study that uses it.

A **pin bump**: move `rev` under `[tool.uv.sources]` in the study's `pyproject.toml` to the new library commit, `uv sync`, commit `uv.lock`, log a **deviation** in `PLAN.md`, rerun the canary runs. A study never edits the library.

## Where knowledge goes

| What | Where |
|---|---|
| A claim a phase establishes | a **finding** in `<hub>/docs/findings/`, by `/publish-finding` |
| A result, a negative result | the phase note, `docs/wiki/phases/NN-slug.md` in the study |
| Protocol, rule packs, canary runs, deviations | the study's `PLAN.md` |
| A term every study shares / a study's own term | `<hub>/docs/CONTEXT.md` / the study's `docs/CONTEXT.md`, by `/domain-modeling` |
| A decision for the workspace / a study / the library | `<hub>/docs/adr/` / the study's `docs/adr/` / the library's own |
| A resource serving several studies / one study | a document by `ws refs add` in the hub's / the study's collection; code or data in its `resources.yaml`; then `ws fetch` and `digest-source` |
| A rule for a kind of work the template's packs miss | a pack in `<hub>/rules/` |
| The next questions | the roadmap in `<hub>/docs/wiki/index.md` |
| Planning for the library or the hub's tooling | `.scratch/<feature>/` of that repository |
| An improvement to `ws`, the overlay or the packs | a branch on the workspace template (`ws-template` remote of the hub), free of {{name}}'s names |

## Building code

Library changes and hub tooling (`ws`, the overlay, the hub skills) follow the main flow: `/grill-with-docs` to sharpen the idea, `/to-spec` and `/to-tickets` for a multi-session build, `/implement` for each ticket (it runs `/tdd` and `/code-review`). Raw incoming issues go through `/triage`; a merge conflict through `/resolving-merge-conflicts`.
