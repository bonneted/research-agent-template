# 02 Port: copv-reliability into copv-ws

Status: blocked by 01

Read `../spec.md` first, especially "Confidentiality (ECOHYDRO)": it binds every step here.

## Source

`https://gitlab.kuleuven.be/r2d/researchers/damien/copv-reliability.git` (34 commits). Clone it fresh into a scratch folder; never run tools from inside it that would scan `confidential/`. Its layout: `src/copv_reliability/` (vessel, mesh, nastran, burst, materials, reliability, evaluation, boundary), `tests/` (with `tests/data/` oracles), `docs/` (CONTEXT, adr 0001–0009, roadmap, wiki concepts and sources, agents/), `.scratch/m0…m6/`, `.claude/` (hook and deny rules), `confidential/` (do not read), `references.bib`.

## Do

1. **`copv` (library).** From a fresh clone, `git filter-repo` keeping the code history and removing by path: `confidential/`, and every historical path of the confidential notes (find them by **name** with `git log --all --name-only --format=` filtered against the note names listed in the spec; never `git show` or `-p` them). Then restructure in the filtered repo: the package becomes `copv` (rename `copv_reliability` → `copv`, update imports and tests), add `copv.experimental` (empty, documented route for study code, as spimat's ADR 0006), keep library ADRs 0001, 0002, 0003, 0004, 0005, 0007, 0008, 0009 in `docs/adr/` (0006, workstation setup, is rewritten for the workspace), move `.scratch/m1-dome-layup`, `m2-dome-model`, `m5-cure-residual-stress` tickets here. New ADR: the solver-backend seam (Nastran | dolfinx) is deferred, with the triggers that would open it (FEniCS migration decision, a second backend needed in the library). Keep CI (`.gitlab-ci.yml`), solver tests marked `solver`. Tests pass without Nastran. Remote `origin` = `https://gitlab.kuleuven.be/r2d/researchers/Damien/copv/copv.git`.
2. **`copv-hub` content.** Move to the hub (as new commits, no history): the domain concept notes (`modelling-chain`, `why-model-the-dome`, `reference-vessel`, `netting-analysis`, `burst-criterion`, `dome-thickness-models`, `hoop-ply-drops`, `double-double-under-winding`), source digests used by several studies (judge; at least Van Bavel's thesis digest), `reading-list`, `CONTEXT.md` terms, the roadmap (rewritten: which milestone is library work, which is a study), `docs/agents/confidentiality.md` (generalised to the workspace). Wikilinks to confidential notes stay as dead links (the user's vault resolves them in `copv-confidential`). References: import `references.bib` into Zotero `copv/copv-hub` via `ws refs add` per DOI if a Zotero key with write access is configured; otherwise keep the bib as committed and report what the user must import.
3. **`copv-ring-validation` (study).** `ws spawn ring-validation`. M0 becomes phase 01 (`phases/01-m0-ring/`, note `docs/wiki/phases/01-m0-ring.md` from `docs/wiki/concepts/m0-ring-validation.md` and the M0 `.scratch` issues). Rule packs: `fe-simulation`, `uq-reliability`. Declare canary runs for the workstation (low and high fidelity ring), not run here. Publish M0's results to the hub with `publish-finding` as `hint` with `legacy` evidence (permalinks to the `copv` commits, at their future GitLab URL; note they resolve only after the push). The open strength-side gap (burst mean 1.6 % below, M0 issue 08) is recorded as an open question, not a finding.
4. **`copv-confidential`.** `git init` a new repo at `~/damien/copv-ws/copv-confidential`; copy the `confidential/` folder of the source clone into it **as a unit** (`cp -r`), without listing, reading or grepping its files; commit with a message that names no content. Register it in the manifest as the off-limits repo; `ws sync` must not mount or link it. If the off-limits hook blocks these commands, that is expected: ask the user to run the two commands themselves (`! cp -r … && git -C … add -A && git -C … commit -m "Consortium notes"`).
5. **Manifest and sync.** Add `copv` (library), `copv-ring-validation` (study), `copv-confidential` to `workspace.yaml`; `ws sync`, `ws check` clean.

## Done when

- `copv` tests pass (`uv run python -m pytest`, solver tests deselected); `git log --all --name-only` in `copv` lists no path under `confidential/` and none of the confidential note names.
- The hub holds the domain wiki and the M0 hint findings; `ws check --all` clean.
- Report: what moved where, what the user must do (GitLab repos, push, Zotero import, archive the old repo read-only, clone the Nastran study on the workstation into a new clean pool).
