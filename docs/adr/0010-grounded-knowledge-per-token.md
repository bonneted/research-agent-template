# Grounded knowledge per token: consolidation levels, and working efficiently

Rigour is affordable, not free. Each phase declares a consolidation level and a rough budget in `PLAN.md`: `scout` (the default for explore: the fastest grounded answer, one known-case check, findings as `hint` without review), `build` (the default for confirm: the frozen protocol, verification tests, counted runs, findings as `hint`), `publish` (only to promote the hints the user names: one reviewer for the phase's findings together, two rounds at most). The next level is reached by a later phase, never by default; the phase note reports what was spent.

How the agent spends tokens is not a research rule but an operating one, in *Working efficiently* in `AGENTS.md`: name the claim an optional instrument serves and build the cheapest that answers it; delegate well-scoped work (reviews against a checklist, searches, figure reading, `check` fixes, wiki edits from a given diff) to subagents on a smaller model; keep tool output near 50 lines, crop images and read them once, write scripts that print summaries.

Carried from the workspace template's core rule 11, split in two.
