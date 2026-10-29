---
name: publish-finding
description: Publish a phase's findings from a study into the hub. Use at the end of a study phase, or when the user asks to publish a finding.
---

# Publish a finding

Run from the study, at the end of a phase, with `../spimat-hub` clean and up to date (`git status`, `git pull`): its one commit must hold only this phase's findings. The hub is `../spimat-hub`; the format is `../spimat-hub/docs/findings/finding-format.md`.

1. **Claims.** From the phase note, list the claims the phase supports. A result is not a claim: publish only what the phase's runs establish. Only counted runs are evidence.
2. **Status.** An explore phase, or too few seeds, gives `hint`. Only a confirm phase, under its decision rules, gives `confirmed`. A claim the phase refutes makes an existing finding `retracted`; a sharper one makes it `superseded`, with `superseded_by`.
3. **Evidence.** Commit and push the study first, then build permalinks at that commit: `<study GitLab URL>/-/blob/<sha>/<path>` for the phase note and the runs. Take the library commit from the runs' stamp.
4. **Existing finding?** Search `../spimat-hub/docs/findings/` for the claim (grep its terms). If a note already states it, update that note: append the new permalinks to `evidence`, raise or lower `status` as step 2 allows, update `spimat` and the conditions, and remove `recheck` if this phase reran the evidence. Otherwise create `docs/findings/<slug>.md` in the format, and add its line to `docs/findings/index.md` under its theme.
5. **One hub commit.** In `../spimat-hub`, stage only the finding notes and the index, and make one commit for the whole phase: `Publish findings of <study> phase NN`. Push it.
6. **Link back.** In the phase note, list each finding as a link into the hub (`../spimat-hub/docs/findings/<slug>.md`) with its status, and commit that in the study.

Done when every claim of the phase is a finding or explicitly judged not one (tell the user which), the hub has exactly one new commit, and the phase note links each finding.
