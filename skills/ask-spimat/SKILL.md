---
name: ask-spimat
description: Ask what to do next anywhere in the spimat workspace. A router over its commands, the study lifecycle, where knowledge goes, and which skill fits each step.
disable-model-invocation: true
---

# Ask spimat

Answer the user's question with the **next action**: the command to run, the file to edit, or the skill to type, from the map below. Read the file a line points to before answering from it; the map names where the answer lives, those files are the truth. Use the glossary's words (`<hub>/docs/CONTEXT.md`).

**Where you are.** The workspace is the siblings of one folder. `<hub>` below is the hub: `.` inside `spimat-hub`, `../spimat-hub` from the library (`spimat`) a study (`spimat-<topic>`) or an app (`spimat-gui`). An app has no study lifecycle: its work in progress is its own `.scratch/`. A study's state is its `PLAN.md` (phases table, deviations) and `git status`; the hub's work in progress is `<hub>/.scratch/`.

## The workspace

Run from the hub; `<hub>/AGENTS.md` says what each prints and when it fails.

- **`uv run ws sync`**: clone what is missing, link the pool, mount the studies, link the hub skills into every repository. After cloning the hub, after `workspace.yaml` or `skills/` changes, or when a link or mount is missing. Read its `FAILED` lines first.
- **`uv run ws fetch`**: pull every `references.bib` from Zotero, then retrieve the resources every manifest lists into the pool. After adding a resource, or on a new machine; paste the `rsync` line it ends with on a machine that has the rest.
- **`uv run ws refs add <doi | arXiv id | URL>`**: add a reference to the Zotero collection of the repository it is run from (or `--repo <name>`; from a study, `uv run --directory ../spimat-hub ws refs add --repo <study> <id>`), and pull. Never write BibTeX; a thesis, report or slides goes into Zotero by hand. Then `ws fetch` for its PDF.
- **`uv run ws refs pull`**: rewrite that repository's `references.bib` from its Zotero collection, after changing the collection in Zotero. Commit the bib; heed its warnings on removed entries still cited.
- **`uv run ws spawn <topic>`**: a new study. Then do what its output says: create the GitLab repository, push, commit the hub's `workspace.yaml` and `docs/studies/index.md`, and create the Zotero collection if `ws` could not.

## The study lifecycle

Rules are the **study rules** of the study's `AGENTS.md` (the default set: `<hub>/overlay/AGENTS.md`); cite them by number.

1. **Spawn** the study (above).
2. **Plan.** Fill `PLAN.md`: the question and the claim type (rule 3). Sharpen them with `/grill-with-docs`, which keeps the study's terms in its `docs/CONTEXT.md`.
3. **Phase.** Start each with the **prior-work check** (`AGENTS.md`, "A phase", step 1). Add the phase to `PLAN.md` as explore or confirm (rule 1); a confirm phase fixes its protocol there before its first run, `/grilling` to stress-test it. Build `phases/NN-slug/` (`run.py`, `report.py`, `config.yaml`) and shared code in `study/` test-first with `/tdd`; `/prototype` for a design question, `/diagnosing-bugs` when a run misbehaves.
4. **Runs.** Every run is stamped by `study/stamp.py` (rule 7); only a **counted run** is evidence. Seeds and tuning follow rules 4 to 6. After a pin bump or a change to `study/`, rerun the **canary runs** of `PLAN.md` (rule 8).
5. **Report.** `report.py` gives the phase's results; write them, negative ones included, into the phase note `docs/wiki/phases/NN-slug.md`, and follow `update-wiki` for the rest of the wiki.
6. **Publish.** At the end of the phase, `/publish-finding` turns the phase's claims into findings in the hub, each a **hint**, **confirmed**, **retracted** or **superseded**, maybe marked **recheck** (`<hub>/docs/findings/finding-format.md`).
7. **Promotion.** Code one study built and a second study needs goes into `spimat.experimental` (`<hub>/docs/adr/0006-study-code-enters-the-library-through-experimental.md`), and so does a recipe that wins the recipe study's leaderboard (`<hub>/docs/adr/0008-the-recipe-study-owns-benchmarks-recipes-and-the-leaderboard.md`): a library merge request that names no study, the reason recorded in `<hub>/docs/library/`, then a **pin bump** in each study that uses it.
8. **Graduation.** Experimental code moves into the core only with tests and a library ADR in `<hub>/docs/library/adr/`, the folder `<hub>/docs/library/CLAUDE.md` names for them (the first library ADR creates it).

A **pin bump**: move `rev` under `[tool.uv.sources]` in the study's `pyproject.toml` to the new library commit, `uv sync`, commit `uv.lock`, log a **deviation** in `PLAN.md`, rerun the canary runs. A study never edits the library.

## Where knowledge goes

| What | Where |
|---|---|
| A claim a phase establishes | a **finding** in `<hub>/docs/findings/`, by `/publish-finding` |
| A result, a negative result | the phase note, `docs/wiki/phases/NN-slug.md` in the study |
| Protocol, canary runs, deviations | the study's `PLAN.md` |
| A term every study shares / a study's own term | `<hub>/docs/CONTEXT.md` / the study's `docs/CONTEXT.md`, by `/domain-modeling` |
| A decision for the workspace / a study / the library | `<hub>/docs/adr/` / the study's `docs/adr/` / `<hub>/docs/library/adr/` |
| A resource serving several studies / one study | a document by `ws refs add` in the hub's / the study's collection; code or data in its `resources.yaml` (`code_of: [<citekey>, ...]` for code implementing documents of the bib); then `ws fetch` and `digest-source` |
| An improvement to try in a recipe / which recipe is best | the ranked list in `<hub>/docs/wiki/spimat-framework.md` / the leaderboard of the recipe study, spimat-framework |
| The library's guidance, status, plans | `<hub>/docs/library/`, never in the library |
| A library bug or feature | a GitLab issue of `r2d/public/spimat` (`<hub>/docs/library/agents/issue-tracker.md`) |
| Planning for the library or the hub's tooling | `<hub>/.scratch/<feature>/` |
| An improvement to the template | **upstreaming**: a branch on the template (`template` in `workspace.yaml`), free of spimat, for the researcher to merge |

## Building code

Library changes (in `../spimat`, checked by its `CONTRIBUTING.md`) and hub tooling (`ws`, the overlay, the hub skills) follow the main flow: `/grill-with-docs` to sharpen the idea, `/to-spec` and `/to-tickets` for a multi-session build, `/implement` for each ticket (it runs `/tdd` and `/code-review`). Raw incoming issues go through `/triage`; a merge conflict through `/resolving-merge-conflicts`. For anything else about those skills, `/ask-matt`.
