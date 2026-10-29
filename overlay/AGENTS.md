# Study

<!-- One or two lines: the research question and its scope. Written when the study starts (see PLAN.md). -->

**{{study}}** is a study of the {{workspace}} workspace: it answers one research question. Start from `docs/wiki/index.md`; the question, claim type, rule packs, protocol and phases are in `PLAN.md`. This study's own terms are in `docs/CONTEXT.md`, the terms every study shares in `../{{hub}}/docs/CONTEXT.md`; decisions are in `docs/adr/`.

## The workspace

- **The hub**, `../{{hub}}`, holds what outlives a study: findings with their status and evidence, hub-scope resources and their digests, the workspace glossary and ADRs. If it is missing, clone it beside this study and build the workspace from it: `git clone {{hub_url}} ../{{hub}}`, then `uv run ws sync` in it.
- **The library**, when the workspace has one, is pinned in `pyproject.toml` at one commit (`[tool.uv.sources]`). It is never edited from here: a library change is a library merge request, then a pin bump here, logged as a deviation in `PLAN.md` and followed by the canary runs declared in `PLAN.md`.
- **Hub skills** such as `publish-finding`, `review-finding` and `ask-{{workspace}}` are linked into `.agents/skills/` by `ws sync`, out of git. `.claude/skills` is a link to `.agents/skills`: edit a skill in `.agents/skills/`, or in the hub for a hub skill.
- **Off-limits material**, when the workspace has some, is listed in the hub's `workspace.yaml` (`off_limits`). Never open, search, list, convert or `git show` it, and never ask the user to paste it. A hook blocks the calls that name it; when it blocks one, do not look for another way in. When a task needs a value from that material, stop and ask the user for it, naming the quantity, its unit and what it is for; code takes such values as inputs, never as constants, and tests use literature or made-up values.

## Layout

- **`PLAN.md`**: the question, the claim type, the rule packs, the protocol, the phases, the canary runs and the deviations.
- **`rules/`**: the rule packs this study may select, copied from the hub when it was spawned. A pack changed in the hub reaches the study only by copying it here, logged as a deviation.
- **`study/`** is the shared study code, imported by every phase. `study/paths.py` says where runs go; `study/stamp.py` stamps each run (core rule 3; usage in its docstring); `study/protocol.py` freezes a confirm phase's protocol.
- **`phases/NN-slug/`**: one folder per phase, `NN` two digits and a short slug (`03-mesh-convergence`), holding `run.py`, `report.py` and `config.yaml`. The configuration declares the phase `type: explore` or `type: confirm`, and lists under `environments` the conda environments its runs call.
- **`environments/<name>.yml`**: a conda environment for a solver uv cannot install, with exact pins (`name=version=build`). It never shares a process with the uv environment: a run calls it with `conda run -n <name>`, and the stamp records the hash of its `conda list --explicit`. `ws check` reports an environment on this machine that drifted from its file.
- **Runs** are outside git, one folder per run in `runs/NN-slug/<run>/`. To keep them elsewhere (another drive), set `{{runs_env}}` to that folder.
- **`resources/`** is the link to the workspace's pool, outside git and read-only: `papers/<citekey>.pdf`, `code/<name>/`, `data/<name>`. This study's resources are those listed in `references.bib` (written by `ws` from the Zotero collection `{{zotero_root}}/{{study}}`; cite as `[@citekey]`, with the page for a number: `[@key, p. 7]`) and `resources.yaml`; `uv run ws fetch` in the hub retrieves them. A reference is added with `uv run --directory ../{{hub}} ws refs add --repo {{study}} <doi | arXiv id | URL>`, which prints its citekey, never by writing BibTeX; a thesis, report or slides is added by hand in Zotero, then `ws refs pull --repo {{study}}` in the hub. Extract PDF text with `pypdf` through uv.
- **`docs/`** is an Obsidian vault: `wiki/` (with `wiki/phases/NN-slug.md`, one note per phase), `CONTEXT.md`, `adr/`. Link notes with `[[note-name]]`.
- **`tests/`** holds the tests. Use `uv` for everything: `uv run python -m pytest`. `uv run --directory ../{{hub}} ws check --repo {{study}}` checks the study against the workspace's rules; run it before a commit that ends a phase.

## A phase

1. **Prior-work check.** Before planning a phase, search the hub for what is already known, in its findings and every mounted study: `grep -Rli "<terms>" ../{{hub}}/docs/findings ../{{hub}}/docs/studies`. A retracted finding is a dead end, a hint is a lead to confirm, a confirmed finding is a starting point, one marked recheck may have drifted. Cite what you used in the phase note.
2. **Plan.** Add the phase to `PLAN.md` with its question, its type, its consolidation level and its budget (core rule 11). A confirm phase fixes its protocol there (its own `### NN-slug` under Protocol), then freezes it before its first run: `uv run python -m study.protocol freeze phases/NN-slug`. The stamp refuses a confirm run whose protocol changed since; a change is a deviation, logged, then frozen again.
3. **Verify, then run.** Check the method on a known case first (core rule 2), then run. Write the phase note `docs/wiki/phases/NN-slug.md` as the phase goes: what was asked, what happened, negative results included.
4. **Publish.** At the end of the phase, follow the `publish-finding` skill: it writes the phase's findings into the hub in one commit, as `hint` unless the phase's level is `publish` (then after a `review-finding` for those that would be confirmed), and links them from the phase note.

## The wiki

The wiki is the study memory, read by the user in Obsidian and by you. Before answering a question about the study, read `docs/wiki/index.md` and the notes it links, and cite the notes you used. When a claim comes from a paper, check it against the PDF passage.

Keep the wiki current as part of the work, in the same turn:

- **New PDF in `resources/papers/`** of a citekey in this study's `references.bib` → follow `.agents/skills/digest-source/SKILL.md`. A document the hub has already digested gets no second digest: link the hub note and state only what this study takes from it.
- **Code change** that adds a method, changes a result, or contradicts a note → follow `.agents/skills/update-wiki/SKILL.md`.

**Parsimony rule:** one note per source or concept. A note states what this study uses or rejects from its subject, with a pointer to where it is used. A digest is a selection, never a full summary.

## Core rules

Every study of the workspace follows these; `PLAN.md` records any rule this study sets aside, and why. The rule packs `PLAN.md` selects (`rules/<pack>.md`) add to them, numbered by pack (`fe-simulation` 2).

1. Each phase is **explore** or **confirm**. Confirm: protocol fixed in `PLAN.md` before the first run (frozen, its hash in the phase's `config.yaml`), deviations logged. Only confirm gives `confirmed`.
2. **Verification before results**: a method is checked on a known case (analytical solution, published number, manufactured solution) before it produces a new result.
3. **Every number traces**: each number in a note comes from a stamped run (`study/stamp.py`: study commit, clean tree or saved diff, library, configuration, seed, environments, hardware, wall-clock), a derivation test, or a page of a source.
4. **No selection on the reported metric**: settings chosen on a calibration case separate from evaluation.
5. **Uncertainty with every headline number**: whichever applies (seeds, noise draws, discretisation or mesh, sampling error of an estimator), stated.
6. **Competent baseline**: every comparison is against the strongest classical method at its best setting.
7. **Negative results are published.**
8. **Canary reruns** after any library, solver or environment version change; drift beyond the stated uncertainty is a deviation and flags the hub findings it touches.
9. **Nothing derived committed; a study never edits the library** (library change = library merge request, then a logged pin bump).
10. **Units**: quantities carry units explicitly in code (unit tests on dimensions, or pint), and every number in a note has its unit.
11. **Grounded knowledge per token.** Each phase declares a consolidation level in `PLAN.md` and in its `config.yaml` (`consolidation:`); it sets how much the phase spends to ground its answer, and the next level is reached by a later phase, never by default.
    - `scout` (the default for explore): the fastest grounded answer. One known-case check; targets spot-checked (a figure value read by eye, with its reading error); findings published as `hint`, without review; no stamped diagnostics.
    - `build` (the default for confirm): the frozen protocol, verification tests, stamped counted runs; findings published as `hint`, without adversarial review.
    - `publish`: only to promote hints the user names to `confirmed`: one `review-finding` reviewer for the phase's findings together, two rounds at most; what is not then upheld stays `hint`.

    Before building an optional instrument (a figure digitiser, a diagnostics run, a sweep), name the claim it serves and use the cheapest one that answers it. Delegate well-scoped work (reviews against the checklist, searches, figure reading, `ws check` fixes, wiki edits from a given diff) to subagents on the smaller model (`model: sonnet`); keep derivations, method and protocol design, and the reading of results in the main session. Keep the context small: tool output near 50 lines at most (longer output goes to a file, then is searched), images cropped and read once, scripts that print summaries. Each phase states a rough budget in `PLAN.md` (tokens, counted runs), and its note reports what it spent.
