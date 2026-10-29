---
name: publish-finding
description: Publish a phase's findings from a study into the hub. Use at the end of a study phase, or when the user asks to publish a finding.
---

# Publish a finding

Run from the study, at the end of a phase, with the hub (`../<hub>`, the folder holding `workspace.yaml`) clean and up to date (`git status`, `git pull`): its one commit must hold only this phase's findings. The format is `../<hub>/docs/findings/finding-format.md`.

1. **Claims.** From the phase note, list the claims the phase supports. A result is not a claim: publish only what the phase's runs, derivations, reproductions, sources or measurements establish. Only counted runs are evidence, and every number of a claim has its unit, its uncertainty and its source (core rules 3, 5, 10). Negative results are claims too (core rule 7).
2. **Status.** An explore phase, too few seeds or samples, or legacy evidence alone gives `hint`. Only a confirm phase, under its decision rules and the protocol frozen for it, can give `confirmed`. A claim the phase refutes makes an existing finding `retracted`; a sharper one makes it `superseded`, with `superseded_by`.
3. **Evidence.** Commit and push the study first, then write each item with its kind and the fields the format gives it, permalinks at that commit (`<study GitLab URL>/-/blob/<sha>/<path>`): `run` (phase note and the run's folder), `derivation` (the derivation and the test or sympy script that checks it), `reproduction` (citekey, page or table, published and reproduced values, tolerance), `source` (citekey and page, checked against the PDF), `measurement` (the dataset of `resources.yaml` and its sha256), `legacy` (a commit and the note reporting a result from before the workspace). Give each item the `phase` type it came from. Take the library commit from the runs' stamps.
4. **Existing finding?** Search `../<hub>/docs/findings/` for the claim (grep its terms). If a note already states it, update that note: append the new evidence, raise or lower `status` as step 2 allows, update `library` and the conditions, and remove `recheck` if this phase reran the evidence. Otherwise create `docs/findings/<slug>.md` in the format, and add its line to `docs/findings/index.md` under its theme.
5. **Review.** For every finding whose status would become `confirmed`, follow the `review-finding` skill and record its verdict in the note's `reviewed`. Only `upheld` keeps `confirmed`; on `narrowed`, rewrite the claim as narrowed and review it again; on `rejected`, publish it as `hint` or not at all, and tell the user why.
6. **Check.** Run `uv run ws check --repo <hub>` from the hub (`uv run --directory ../<hub> ws check --repo <hub>`), and fix every `FAILED` line on the findings you wrote.
7. **One hub commit.** In `../<hub>`, stage only the finding notes and the index, and make one commit for the whole phase: `Publish findings of <study> phase NN`. Push it.
8. **Link back.** In the phase note, list each finding as a link into the hub (`../<hub>/docs/findings/<slug>.md`) with its status, and commit that in the study.

Done when every claim of the phase is a finding or explicitly judged not one (tell the user which), every confirmed finding has an `upheld` review, `ws check` passes on the hub, the hub has exactly one new commit, and the phase note links each finding.
