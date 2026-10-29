# Study

<!-- One or two lines: the research question and its scope. Written when the study starts (see PLAN.md). -->

**{{study}}** is a study of the spimat workspace: it answers one research question with the spimat library. Start from `docs/wiki/index.md`; the question, claim type, protocol and phases are in `PLAN.md`. This study's physics and method terms are in `docs/CONTEXT.md`, the terms every study shares in `../{{hub}}/docs/CONTEXT.md`; decisions are in `docs/adr/`.

## The workspace

- **The hub**, `../{{hub}}`, holds what outlives a study: findings with their status and evidence, the library's private context, hub-scope resources and their digests. If it is missing, clone it beside this study and build the workspace from it: `git clone {{hub_url}} ../{{hub}}`, then `uv run ws sync` in it.
- **The library**, spimat, is pinned in `pyproject.toml` at one commit (`[tool.uv.sources]`). It is never edited from here: a library change is a library merge request, then a pin bump here, logged as a deviation in `PLAN.md` and followed by the canary runs declared in `PLAN.md`.
- **Hub skills** such as `publish-finding` and `ask-spimat` are linked into `.agents/skills/` by `ws sync`, out of git. `.claude/skills` is a link to `.agents/skills`: edit a skill in `.agents/skills/`, or in the hub for a hub skill.

## Layout

- **`PLAN.md`**: the question, the claim type, the protocol, the phases and the deviations.
- **`study/`** is the shared study code, imported by every phase. `study/paths.py` says where runs go; `study/stamp.py` stamps each run (rule 7; usage in its docstring): it writes `stamp.json` (and `diff.patch` from a dirty tree) into the run's folder, with the run's resolved configuration when its runner passes one, and refuses a confirm run from a dirty tree.
- **`phases/NN-slug/`**: one folder per phase, `NN` two digits and a short slug (`03-mixed-formulation`), holding `run.py`, `report.py` and `config.yaml`. The configuration declares the phase `type: explore` or `type: confirm`.
- **Runs** are outside git, one folder per run in `runs/NN-slug/<run>/`. To keep them elsewhere (another drive), set `{{runs_env}}` to that folder.
- **`resources/`** is the link to the workspace's pool, outside git and read-only: `papers/<citekey>.pdf`, `code/<name>/`, `data/<name>`. This study's resources are those listed in `references.bib` (written by `ws` from the Zotero collection `spimat/{{study}}`; cite as `[@citekey]`) and `resources.yaml`; `uv run ws fetch` in the hub retrieves them. A reference is added with `uv run --directory ../{{hub}} ws refs add --repo {{study}} <doi | arXiv id | URL>`, which prints its citekey, never by writing BibTeX; a thesis, report or slides is added by hand in Zotero, then `ws refs pull --repo {{study}}` in the hub. Extract PDF text with `pypdf` through uv.
- **`docs/`** is an Obsidian vault: `wiki/` (with `wiki/phases/NN-slug.md`, one note per phase), `CONTEXT.md`, `adr/`. Link notes with `[[note-name]]`.
- **`tests/`** holds the tests. Use `uv` for everything: `uv run python -m pytest`.

## A phase

1. **Prior-work check.** Before planning a phase, search the hub for what is already known, in its findings, the library's context and every mounted study: `grep -Rli "<terms>" ../{{hub}}/docs/findings ../{{hub}}/docs/library ../{{hub}}/docs/studies`. A retracted finding is a dead end, a hint is a lead to confirm, a confirmed finding is a starting point, one marked recheck may have drifted. Cite what you used in the phase note.
2. **Plan.** Add the phase to `PLAN.md` with its question and its type. A confirm phase fixes its protocol there before its first run.
3. **Run and report.** Write the phase note `docs/wiki/phases/NN-slug.md` as the phase goes: what was asked, what happened, negative results included.
4. **Publish.** At the end of the phase, follow the `publish-finding` skill: it writes the phase's findings into the hub in one commit and links them from the phase note.

## The wiki

The wiki is the study memory, read by the user in Obsidian and by you. Before answering a question about the study, read `docs/wiki/index.md` and the notes it links, and cite the notes you used. When a claim comes from a paper, check it against the PDF passage.

Keep the wiki current as part of the work, in the same turn:

- **New PDF in `resources/papers/`** of a citekey in this study's `references.bib` → follow `.agents/skills/digest-source/SKILL.md`. A document the hub has already digested gets no second digest: link the hub note and state only what this study takes from it.
- **Code change** that adds a method, changes a result, or contradicts a note → follow `.agents/skills/update-wiki/SKILL.md`.

**Parsimony rule:** one note per source or concept. A note states what this study uses or rejects from its subject, with a pointer to where it is used. A digest is a selection, never a full summary.

## Study rules

The default rules of a spimat study (scientific ML for mechanics); rule 11 keeps those of the first study, spimat-framework. `PLAN.md` records any rule this study sets aside, and why.

1. Each phase declares **explore** or **confirm**. Confirm: protocol fixed before the first run, deviations logged. Only confirm can produce `confirmed` findings.
2. Each comparison is attributable to its declared factors: one factor by default, a small factorial (2×2) when an interaction is the hypothesis.
3. Each study declares its **claim type** in `PLAN.md`: comparative (matched axis, equal tuning, effect rule); feasibility/tractability
   (accuracy vs reference + scaling curves of cost and memory vs dimension or resolution, SPINN vs PINN vs FEM, where they cross); scientific
   (verification on a known case first, uncertainty over seeds and noise, engineering quantities). Most studies here are application/feasibility.
4. No selection on the reported error: settings chosen on a calibration case separate from evaluation; always report the final iterate.
   A stabilised estimator (e.g. median over the last 10% of logged steps) may be the headline if declared beforehand and computed only
   from quantities available in practice; the final iterate is reported beside it.
5. Tuning: the phase states its policy; default is an equal learning-rate sweep per arm. Budget: state the matched axis
   (params / steps / wall-clock), report all three plus GPU type.
6. Seeds: one seed controls init and collocation; arms paired by seed; report median and full range; 3 to screen, 5 to claim;
   effect rule = beyond both the reference floor and the seed spread.
7. A run counts only if it stamps study commit (clean tree, or diff saved in the run), resolved spimat sha, config, seed, hardware, wall-clock.
   The runner refuses a confirm run from a dirty tree.
8. Canary runs, declared in `PLAN.md`: one or two reference runs rerun after any spimat pin bump or shared-code change; drift beyond seed spread is a deviation
   and flags the hub findings it touches.
9. Reporting: primary metric declared per study; always report equilibrium/traction residuals on an independent grid, engineering
   quantities (Kt, peak stress, reaction, identified parameters), energy-norm error where a reference exists; area-weighted scoring grids.
10. Against FEM: same constitutive implementation (shared material library); compare at matched accuracy; competent solver, hardware
    on both sides stated; count the whole cost (training is the solve); inverse problems compare against FEMU.
11. Kept from the current study: hard metered compute budget, verification before runs, negative results reported, nothing derived
    committed, a study never edits spimat (library change = spimat MR, then a logged pin bump).
