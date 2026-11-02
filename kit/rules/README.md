# Rule packs

Rules an inquiry takes on besides the core rules of its `AGENTS.md`, one pack per kind of work. An inquiry selects its packs in `inquiry.yaml` (`rule_packs`) and in the Rule packs section of its `PLAN.md`; `spawn` copies this folder into a sub-inquiry, and `rkt check` fails an inquiry that selects a pack it does not have. A child keeps every pack its parent selected (it may add, never drop one). Cite a rule by pack and number: `fe-simulation` 2.

The kit's packs are `rigour` (the mechanisms behind confirm phases: run stamp, protocol freeze, conda pins, canary reruns, units in code), `ml-training`, `fe-simulation`, `uq-reliability` and `literature-check`. Add your own here, one Markdown file each, in the same form: a title, one paragraph on when the pack applies, numbered rules.
