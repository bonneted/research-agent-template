# 01 Template: build research-ws-template, then `ws init copv`

Status: ready-for-agent

Read `../spec.md` first; decisions D1–D11 are settled.

## Starting point

`~/damien/research-ws-template` is a fresh clone of research-agent-template (commit `9c6822d`), remote `template`. Nothing else is done. The spimat implementation to extract from is `~/damien/spimat-ws/spimat-hub` (read-only): `tools/ws/`, `tests/`, `overlay/`, `skills/`, `docs/findings/finding-format.md`, `docs/adr/` (ADRs 0001–0009 explain why the layout is what it is), `README.md`, `AGENTS.md`, `workspace.yaml`.

## Do

1. **Shape the repo as a hub template.** It is what a hub looks like at birth: `tools/ws/`, `overlay/`, `skills/`, `rules/` (core packs), `docs/` (vault skeleton with `findings/finding-format.md`, `findings/index.md`, `studies/index.md`, `CONTEXT.md` with the workspace terms, `adr/` with the template's own ADRs), `workspace.yaml` skeleton, `README.md`, `AGENTS.md`. Remove what a hub does not need from the research-agent-template copy (`talk/`, `src/`; its `tools/fetch` is replaced by `ws fetch`, as spimat's spawn does). Keep the template's `digest-source` and `update-wiki` skills.
2. **Extract `ws`** from spimat-hub with its tests, then parameterise per D2: no `spimat` string left in code paths (grep for it; leftovers only in docs that cite spimat as the origin). Keep `sync`, `fetch`, `refs pull/add`, `spawn`. Add `init` (D3) and `check` (D7). The tests stay end to end against local bare repositories, as in spimat-hub.
3. **Generalise the overlay** (`overlay/AGENTS.md`, `PLAN.md`, `study/stamp.py`, `study/paths.py`, tests): core rules (D5), rule packs selected in `PLAN.md`, evidence kinds (D4), protocol freeze and its hash in the stamp (D7), conda environments (D8), `stamp_extras` (D2).
4. **Rule packs** in `rules/`: `ml-training` (extracted faithfully from spimat's rules), `fe-simulation`, `uq-reliability`, `literature-check` (D5).
5. **Skills**: `publish-finding` generalised (evidence kinds, calls `review-finding` for `confirmed`), new `review-finding` (D9), `ask-<name>` generated or templated from the manifest (spimat's `ask-spimat` as the model).
6. **Off-limits module** (D6), with tests: settings merge, hook blocking (feed it tool-call JSON on stdin as Claude Code does; exit code 2 blocks), written into every repo and the workspace root, report on drift.
7. **Cross-platform links** (D10), with tests for the junction/copy path.
8. **ADRs** for the template's own decisions (one short ADR each for D1, D4+D5, D6, D7, D9, D10), in the style of spimat-hub's.
9. **README** a newcomer can follow: start a workspace (`ws init`), add a study (`ws spawn`), the evidence model and rules, `ws check`, the off-limits module, Windows. Record the spimat back-port follow-up in `.scratch/workspace-template/`.
10. **Commit** in logical steps (local only).
11. **Instantiate copv-ws**: in `~/damien/copv-ws`, run `ws init copv` non-interactively with the manifest values and off-limits configuration of `../spec.md` ("copv-ws"). Repositories `copv`, `copv-ring-validation`, `copv-analytical` are **not** created here (tickets 02, 03): the manifest lists only the hub at this point (or lists the others as pending if the tool supports it; do not make sync fail on their absence). Hub remote `origin` = `https://gitlab.kuleuven.be/r2d/researchers/Damien/copv/copv-hub.git`, `ws-template` = the template's future URL. Run `ws sync` and `ws check` and show their output. Check that `~/damien/copv-ws/.claude/settings.json` and the hook exist and that the hook blocks a test call naming `confidential/` (run the hook directly with a JSON payload; do not try to read a real confidential file).

## Done when

- `uv run python -m pytest` passes in research-ws-template (show the summary line), and ruff passes.
- `grep -rn spimat tools/ overlay/ skills/` finds nothing but deliberate origin citations.
- `~/damien/copv-ws/copv-hub` exists, committed, `ws sync` and `ws check` clean; the workspace root and the hub carry the off-limits files.
- A final report: what was built, test output, anything deferred, decisions the agent had to make within the spec (listed, so the user can review them).
