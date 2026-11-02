# research-knowledge-tree

This repository is the template of the knowledge tree: the kit an inquiry carries (`kit/`) and the source of the `rkt` tool (`tools/`). It is not itself an inquiry. Terms follow `GLOSSARY.md`; decisions are in `docs/adr/`; the plan of the current rework is `.scratch/knowledge-tree/spec.md`.

## Working on the template

- **`kit/`** is exactly what a new inquiry contains. `rkt init` copies it into an empty folder; `spawn` copies a parent's. Keep it free of any inquiry's names, and minimal: a mechanism an agent can rebuild from a rule does not belong in it. A change to a rule or a skill is a change to every future inquiry: record why in an ADR when it is hard to reverse.
- **`kit/AGENTS.md`** holds the core rules. Their numbers are cited by the rule packs, the skills, the finding format and `PLAN.md`: renumbering one means updating them all (`grep -rn "rule [0-9]" kit/`).
- **`tools/`** is the `rkt` package (`init`, `refs`, `fetch`, `check`, and the rigour pack's `freeze`; the stamp is kit code, `kit/rules/rigour/study/`). Run `uv run python -m pytest` and `uvx ruff check` before a commit.
- The README is for someone who has never seen the template: start from the thesis, keep the five-minute path first.
