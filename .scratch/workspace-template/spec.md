# Workspace template, and copv-ws built on it

Status: ready-for-agent (ticket 01); tickets 02 and 03 wait for 01.

Decided with the user in a grilling session on 2026-10-29. Every decision below is settled; an agent that finds one unworkable stops and reports, it does not re-decide.

## Why

`~/damien/spimat-ws` works: independent study repositories, a private hub that only receives what the studies establish (findings, through `publish-finding`), a resource pool outside git, Zotero-driven bibliographies, and the `ws` tool that builds it all (`spimat-hub/tools/ws/`, `spimat-hub/overlay/`, `spimat-hub/skills/`). But it is spimat-specific in two ways:

- **Names** are hard-coded: `SPIMAT_RESOURCES`, `~/.config/spimat/retrieval.yaml`, Zotero collections `spimat/<repo>`, the library `spimat`, `spimat.installed_from()` in the stamp, `ask-spimat`.
- **The evidence model is ML-shaped**: evidence = stamped training runs; the study rules (`spimat-hub/overlay/AGENTS.md`, "Study rules") are about seeds, learning-rate sweeps, GPU budgets, SPINN vs PINN vs FEM.

The goal is a general **workspace template** for expanding research knowledge in a field, with best-practice guards against research flaws built in (rules, mechanical checks, review), then a first workspace from it: **copv-ws** (composite overwrapped pressure vessels).

## Decisions

### D1. The template is a new hub-template repository wrapping the research agent template

- `~/damien/research-ws-template` (later `r2d/collaboration/research-ws-template` on KU Leuven GitLab). It was created from `research-agent-template` and keeps it as its `template` remote, so upstream improvements merge in.
- research-agent-template stays a single-project template, unchanged. Studies are still spawned from it (`template` key of the manifest), with the workspace overlay applied.
- A hub instantiated from research-ws-template keeps it as a remote too (name it `ws-template`), so template fixes reach hubs by merge.
- Build by **extracting** spimat-hub's `ws` and its end-to-end tests (`spimat-hub/tools/ws/`, `spimat-hub/tests/`), then parameterising. Do not rewrite from scratch. spimat-hub is read-only for this work.
- **spimat is not migrated** in this effort. Design so spimat-hub could adopt the template (spimat = one configuration of it); record the back-port as a follow-up in this folder.

### D2. Everything workspace-specific comes from the manifest

`workspace.yaml` of the hub gains a `workspace:` block (names illustrative, the agent may refine them, documented in the README):

```yaml
workspace:
  name: copv                          # prefix of repos, skills (ask-copv), env vars (COPV_RESOURCES, COPV_RUNS)
  gitlab: https://gitlab.kuleuven.be/r2d/researchers/Damien/copv
  zotero_root: copv                   # collections <zotero_root>/<repo>
  library: copv                       # the role: library repo, pinned by studies; optional (a workspace may have none)
  stamp_extras: hub_tools.stamp_extras:collect   # optional entry point adding fields to every run stamp
  rule_packs_dir: rules               # workspace-specific packs, beside the template's
  off_limits: {...}                   # D6
template: https://gitlab.kuleuven.be/r2d/collaboration/research-agent-template.git
repositories: [...]
```

Config outside git moves to `~/.config/research-ws/retrieval.yaml` with a per-workspace section (fall back to reading `~/.config/spimat/retrieval.yaml` is not needed).

### D3. `ws init <name>`

Creates `<name>-hub` in the current folder (the workspace root) from research-ws-template: asks for (or takes as flags) the manifest keys of D2 and the off-limits configuration (D6), writes `workspace.yaml`, fills the hub's `AGENTS.md`/`README.md`/`docs/CONTEXT.md` skeletons, commits, and runs `ws sync`. Interactive prompts must have flag equivalents so agents can run it non-interactively.

### D4. Evidence model

A finding keeps spimat's statuses: `hint | confirmed | retracted | superseded` (format: `spimat-hub/docs/findings/finding-format.md`, generalised). Each evidence item gets a **kind**:

| kind | what it is | must carry |
|---|---|---|
| `run` | a stamped computation | permalink to phase note + run stamp reference |
| `derivation` | an analytical result | permalink to the derivation and to the test or CAS script (sympy) that checks it |
| `reproduction` | a published number reproduced | citekey, page/table/figure, published value, reproduced value, tolerance |
| `source` | a cited passage | citekey and page, checked against the PDF |
| `measurement` | experimental data | dataset name in `resources.yaml` with sha256 |
| `legacy` | a result produced before the workspace existed (unstamped) | commit permalink and the note that reports it |

`legacy` evidence can never support `confirmed`. Explore/confirm stays the universal phase distinction (exploratory vs preregistered); only confirm phases can give `confirmed`.

### D5. Rules: core rules + rule packs

`overlay/AGENTS.md` carries the **core rules**, always on:

1. Each phase is **explore** or **confirm**. Confirm: protocol fixed in `PLAN.md` before the first run, deviations logged. Only confirm gives `confirmed`.
2. **Verification before results**: a method is checked on a known case (analytical solution, published number, manufactured solution) before it produces a new result.
3. **Every number traces**: each number in a note comes from a stamped run, a derivation test, or a page of a source.
4. **No selection on the reported metric**: settings chosen on a calibration case separate from evaluation.
5. **Uncertainty with every headline number**: whichever applies (seeds, noise draws, discretisation/mesh, sampling error of an estimator), stated.
6. **Competent baseline**: every comparison is against the strongest classical method at its best setting.
7. **Negative results are published.**
8. **Canary reruns** after any library, solver or environment version change; drift beyond the stated uncertainty is a deviation and flags the hub findings it touches.
9. **Nothing derived committed; a study never edits the library** (library change = library merge request, then a logged pin bump).
10. **Units**: quantities carry units explicitly in code (unit tests on dimensions, or pint), and every number in a note has its unit.

**Rule packs** (opt-in per study in `PLAN.md`, one Markdown file each in the template's `rules/`; a workspace adds its own in the hub's `rules/`):

- `ml-training`: today's spimat rules 2, 4–6, 9–10 (factors, final iterate, tuning policy, matched budget, seeds 3/5 with effect rule, scoring grids). Extract them faithfully.
- `fe-simulation`: mesh convergence of every reported quantity (≥3 meshes, observed order, Richardson or GCI where applicable); solver verification (patch test / analytical case); same constitutive law on both sides of a comparison; boundary conditions and load stated and checked (reaction balance); solver version and input deck kept.
- `uq-reliability`: estimator convergence shown (CoV of P_f or of the quantity, confidence interval); sample size justified; distributions and their sources stated; surrogate validated on held-out points with the error stated; FORM/SORM checked against sampling at least once; sensitivity indices with their estimator error.
- `literature-check`: claim register (quotation, page, metric, published number, verdict `holds | tie | fails | untestable as published`); reproduce the paper's own baseline before testing it; the study does not win by changing the problem (variants go beside the paper's case, never in its place); code/data availability checked and recorded. Model it on `spimat-ws/spimat-pinn-claims/PLAN.md` ("How a paper is checked").

### D6. Off-limits module (confidential material)

Optional, configured at `ws init` (and editable in the manifest):

```yaml
off_limits:
  paths: [...]          # globs, absolute or ~-relative, per machine as needed
  patterns: [...]       # regexes on tool-call arguments (file names, extensions)
  deny_connectors: [mcp__claude_ai_Gmail, mcp__claude_ai_Google_Drive]
  repo: copv-confidential   # optional: a repo ws clones but never mounts, links, or lists in study indexes
```

`ws sync` writes into **every repository and into the workspace root** (sessions start there): `.claude/settings.json` deny rules (merged with an existing file, never clobbering other keys; if it cannot merge safely it reports), the PreToolUse hook script (generalised from `copv-reliability/.claude/hooks/guard_confidential.py`, reading its patterns from the manifest), and `.ignore`. The hook blocks Read/Grep/Glob/Bash/PowerShell calls whose arguments match. The module's README states its limits honestly (a recursive grep that does not name the path is not caught; the rule covers it).

### D7. Enforcement: tooling that refuses, `ws check`, agent rules

- **Stamp** (`overlay/study/stamp.py`, generalised): library report via the manifest's library (not `spimat.installed_from()`; fall back to `importlib.metadata` + editable git checkout), `stamp_extras` hook output, the hash of each declared conda environment (D8). Refuses a confirm run from a dirty tree, and from a `PLAN.md` whose protocol section hash differs from the one frozen for the phase (freezing = `ws freeze <phase>` or equivalent, recording the hash in the phase's `config.yaml`).
- **`ws check`** (run from any repo, `--repo`, or `--all`; non-zero exit on FAILED; used in each repo's CI):
  - finding front-matter against a schema (status, evidence kinds and their required fields, `confirmed` only with confirm-phase non-legacy evidence, `reviewed` present for `confirmed`);
  - evidence permalinks: the commit exists in the study (local clone check; network check optional);
  - every `[@citekey]` in `docs/` exists in the repo's `references.bib` (or the hub's for hub-scope digests);
  - numbers quoted from a source carry a page (heuristic, warning level);
  - every `phases/NN-slug/` has its `docs/wiki/phases/NN-slug.md` and a `type`;
  - confirm phases have a frozen protocol hash; deviations after a freeze are logged;
  - declared conda environments match their pinned files (if the env exists on the machine);
  - off-limits files present and current in every repo.
- **Agent rules** in `AGENTS.md` cover the rest.

### D8. Environments uv cannot install

The spimat pattern (`spimat-plasticity/fem/README.md`): a conda environment never sharing a process with the uv one, called with `conda run -n <env>`. Standardised: a study declares `environments/<name>.yml` with exact pins; the stamp records the hash of `conda list --explicit` for each environment a run used; `ws check` reports drift. pixi is a possible later change, not now.

### D9. Review before `confirmed`

New hub skill `review-finding`: an adversarial reviewer with **no study context** (a fresh subagent given only the finding note and its evidence permalinks/files) that tries to break the claim: over-claiming beyond the evidence, missing or weak baseline, confounded factors, missing uncertainty, rule-pack violations. Its verdict is recorded in the finding front-matter (`reviewed: {date, verdict, notes}`). Required for `confirmed`; optional for `hint`. `publish-finding` calls it when the status would be `confirmed`.

### D10. Cross-platform, no admin

The workspace must run on the Windows workstation `set-s-me-xad02` **without admin rights or Developer Mode**. On Windows, `ws` uses **directory junctions** (`mklink /J`, or `_winapi.CreateJunction`) wherever it uses directory symlinks on Linux; where a *file* link is needed it copies, records the copy's hash, and reports drift (never overwrites an edited copy silently). Linux behaviour unchanged. Tests cover the link abstraction on both paths (the Windows path can be tested by monkeypatching the platform and the link primitive).

### D11. What the hub holds

Findings (only through `publish-finding`), digests of sources used by ≥2 studies, domain concept notes, the workspace glossary and ADRs, the roadmap, `workspace.yaml`, `ws`, hub skills (`publish-finding`, `review-finding`, `ask-<name>`, and the template skills). Everything else stays in its study. If the library is private, its design context stays in the library repo (spimat's split of private context into the hub exists only because spimat is public).

## copv-ws

Workspace root `~/damien/copv-ws` on r2d2 (WSL). GitLab group `r2d/researchers/Damien/copv/`, all private. Nastran studies are later also cloned on the workstation (Windows) by `ws sync`, into a **new, clean pool**; the old `...\ECOHYDRO\resources` folder (which contains the consortium PDFs in `ecohydro/`) is never the pool.

| repo | role | from |
|---|---|---|
| `copv-hub` | hub | `ws init copv` |
| `copv` | library | copv-reliability's code, history kept after path filtering (ticket 02) |
| `copv-ring-validation` | study | M0 of copv-reliability as phase 01 (ticket 02) |
| `copv-analytical` | study | new (ticket 03) |
| `copv-confidential` | off-limits repo | copv-reliability's `confidential/`, moved by git operations only (ticket 02) |

M3 (fidelity link), M4 (uncertainty propagation), M6 (design optimisation) become studies only when they start. M1 (dome layup), M2 (dome mesher), M5 (cure residual stress) are library engineering: their `.scratch/` tickets go to the library.

### Confidentiality (ECOHYDRO), binding on every agent

Source of truth: `copv-reliability/docs/agents/confidentiality.md` (readable; it describes the rules, not the material). In short: **never open, search, list, convert or `git show`/`git log -p`** `confidential/`, `$COPVREL_RESOURCES/ecohydro/`, `~/VISIATIV/`, the WP working folders, the confidential note names (`ecohydro-project`, `ecohydro-wp5`, `ecohydro-d5.5`, `ecohydro-wp4-data`, `ecohydro-materials`, `demonstrators`, `d3-vessel`, `partner-inputs`), or Office/e-mail files. Moving them is done by path (`git filter-repo --path`, `git mv`, `cp -r` of the folder as a unit) without reading content. Project values (pressures, liner dimensions, material properties, layups, deadlines) are never constants: code takes them as inputs, tests use literature or made-up values. If a task needs one, stop and ask the user.

### Off-limits configuration for copv

Paths: `confidential/`, `copv-confidential/`, `~/VISIATIV/`, `~/Documents/ECOHYDRO/WP*/`, `D:/u0150568.LUNA/Documents/ECOHYDRO/WP*/`, `D:/u0150568.LUNA/Documents/ECOHYDRO/resources/ecohydro/`, any `resources/ecohydro/`. Patterns: those of `copv-reliability/.claude/hooks/guard_confidential.py` (Office/e-mail extensions, the note names, the data tracker). Connectors denied: Gmail, Google Drive. `repo: copv-confidential`.

## Tickets

- [01 Template](issues/01-template.md): build research-ws-template, then `ws init copv`. Ready.
- [02 Port](issues/02-port.md): copv-reliability → `copv`, `copv-hub` content, `copv-ring-validation`, `copv-confidential`. After 01.
- [03 Analytical](issues/03-analytical.md): `copv-analytical`, phase 01 then stop. After 01; parallel with 02 once the library exists (it pins `copv`), so in practice after 02's library step.

## Across all tickets

- **Commit locally, never push.** The user creates the GitLab subgroup and repositories and pushes at the end (`glab` is not authenticated for gitlab.kuleuven.be). Remotes are set to their future URLs so a push just works.
- Read-only: `~/damien/spimat-ws/**`, `~/damien/research-agent-template`, the copv-reliability clone's `confidential/` (not even read).
- `uv` for everything Python; tests `uv run python -m pytest`. Follow the house style of spimat-hub's code and docs (plain sentences, no marketing, Markdown that reads like the existing notes).
- Each ticket ends with a short report to the user: what was built, what was verified (test output), what was skipped and why, what the user must do.

## Follow-ups (not in this effort)

- Back-port spimat-hub onto research-ws-template (spimat as one configuration).
- pixi in place of the conda pattern.
- Library solver-backend seam (Nastran | dolfinx) when its trigger fires (ADR in `copv`).
- Nastran validation of copv-analytical on the workstation.
