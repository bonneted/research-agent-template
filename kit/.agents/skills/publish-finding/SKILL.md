---
name: publish-finding
description: Publish a phase's findings in this inquiry and up to its parent. Use at the end of a phase, or when the user asks to publish a finding.
---

# Publish a finding

The format is `docs/findings/finding-format.md`. Commit and push this inquiry first: evidence is cited by permalink at that commit.

## Here

1. **Claims.** From the phase note, list the claims the phase supports. A result is not a claim: publish what the phase's runs, derivations, reproductions, sources or measurements establish, every number with its unit, interval and trace (rules 4, 6). Negative results are claims too (rule 10).
2. **Denominator.** For each claim, count what was tried to reach it (variants, analyses, runs) from the phase note's list: that is `tried` (rule 10).
3. **Status.** The phase's consolidation level caps it (rule 2): `scout` and `build` publish `hint`; only `publish`, from a confirm phase under its protocol, may give `confirmed`. A claim the phase refutes makes an existing finding `retracted`; a sharper one makes it `superseded`.
4. **Evidence.** Write each item with its kind and fields, permalinks at the pushed commit, and the `phase` type it came from.
5. **Existing finding?** Search `docs/findings/` for the claim. If a note states it, append the new evidence, raise or lower the status as step 3 allows, and remove `recheck` if this phase reran the evidence. Otherwise create `docs/findings/<slug>.md`, and its line in `docs/findings/index.md` under its theme.
6. **Confirm.** At the `publish` level only, for the findings that would become `confirmed`: follow `review-finding` once for them together; then show the user each claim with its verdict and ask for approval. Only `upheld` and the user's yes give `confirmed`, with `reviewed` and `approved` recorded (rule 12); otherwise the finding stays `hint`.
7. **Link.** In the phase note, link each finding with its status. Run `rkt check`, fix what it reports, and commit.

## Up

When `inquiry.yaml` names a parent and the parent is checked out at `../..`, with a clean tree (`git status`, `git pull`):

8. **What answers the parent's question.** For each finding, decide whether it bears on the parent's question (its `inquiry.yaml`). Detail that matters only here stays here.
9. **The parent's finding.** For each that bears on it, write or update a finding in `../../docs/findings/`, stated in the parent's terms (its `GLOSSARY.md`), with a `sub-inquiry` evidence item: the permalink of this finding at the pushed commit, and its status there. Its status is at most the weakest `sub-inquiry` evidence it rests on (rule 11); `tried` counts what this inquiry tried. Add it to the parent's findings index.
10. **The route.** Update this inquiry's entry under `## Sub-inquiries` in `../../docs/wiki/index.md`: status, what to dive here for, the headline findings with their status.
11. **One commit up.** Run `rkt check` in the parent, fix what it reports on what you wrote, and make one commit there, `Publish findings of <name> phase NN`. Push it if the user works with a remote.

Done when every claim of the phase is a finding here or judged not one (tell the user which), every confirmed finding has an `upheld` review and the user's approval, the parent holds a finding for each that bears on its question with its route updated, and `rkt check` passes in both.
