# Evidence has kinds; studies follow core rules and the rule packs they select

spimat's evidence was stamped training runs, and its study rules were about seeds, learning-rate sweeps and GPU budgets. A workspace of FE simulation, reliability analysis, derivations or literature checks needs other evidence and other guards. So a finding keeps spimat's statuses (`hint | confirmed | retracted | superseded`), and each evidence item gets a kind: `run`, `derivation`, `reproduction`, `source`, `measurement` or `legacy`, each with the fields that make it checkable (`docs/findings/finding-format.md`). The explore/confirm distinction stays universal: only a confirm phase gives `confirmed`. Legacy evidence, produced before the workspace and unstamped, never does.

The rules split the same way. Ten **core rules**, in every study's `AGENTS.md`, hold for any kind of work: explore or confirm, verification before results, every number traces, no selection on the reported metric, uncertainty with every headline number, a competent baseline, negative results published, canary reruns after any version change, nothing derived committed and the library never edited from a study, units. **Rule packs** (`rules/`) hold what depends on the kind of work: `ml-training` (spimat's rules, taken as they are), `fe-simulation`, `uq-reliability`, `literature-check`. A study selects its packs in `PLAN.md`; `ws spawn` copies every pack into the study, so a pack edited in the hub changes a running study only by a copy logged as a deviation.

## Consequences

A workspace adds its own packs in its hub's `rules/`. `ws check` reads the kinds and their fields, and fails a study that selects a pack it does not have.
