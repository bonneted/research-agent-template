# Finding format

One note per finding in `docs/findings/<slug>.md`, the slug naming the claim (`a-mesh-of-three-elements-per-ply-converges-the-burst-pressure`). A finding is recorded once: a later phase that bears on it adds evidence to the same note, never writes another. `rkt check` checks the front matter against this format. Back to the [findings](index.md).

```markdown
---
status: hint            # hint | confirmed | retracted | superseded
tried: 6                # rule 10: variants, analyses or runs tried to reach this claim
evidence:
  - kind: run
    phase: confirm      # the type of the phase that produced it
    note: https://<forge>/<group>/<inquiry>/-/blob/<sha>/docs/wiki/phases/NN-slug.md
    run: NN-slug/<run>  # the run's folder, as the phase note reports it
  - kind: source
    citekey: smith2020
    page: 7
  - kind: sub-inquiry
    finding: https://<forge>/<group>/<child>/-/blob/<sha>/docs/findings/<slug>.md
    status: hint        # the child's status at that commit; bounds this one (rule 11)
superseded_by: other-finding.md   # only when status is superseded
recheck: <why>          # optional: a canary run showed the code drifted since
reviewed:               # required for confirmed: the review-finding verdict
  date: 2026-11-02
  verdict: upheld       # upheld | narrowed | rejected
  notes: what the reviewer tried, and what held
approved: 2026-11-02    # required for confirmed: the date the user approved the promotion (rule 12)
---

# The claim, as one sentence

**Claim.** What holds, with the numbers that show it, each with its unit and interval.

**Scope.** Where it was shown (problem, cases, seeds or samples, meshes, phase type), and whether it holds for the model only or was validated against a measurement (rule 9).

**Tried.** What else was tried on the way, in one line each or by a link to the phase note's list (rule 10).

**Rules out.** What it makes not worth trying again.
```

## Evidence kinds

| kind | what it is | must carry |
|---|---|---|
| `run` | a computation, traced by its commit and configuration (stamped with the rigour pack) | `phase`, `note` (permalink to the phase note), `run` (`NN-slug/<run>`) |
| `derivation` | an analytical result | `phase`, `derivation` (permalink to it), `check` (permalink to the test or CAS script that checks it) |
| `reproduction` | a published number reproduced | `phase`, `citekey`, `where` (page, table or figure), `published`, `reproduced`, `tolerance` |
| `source` | a cited passage | `citekey`, `page`; checked against the passage |
| `measurement` | experimental data | `phase`, `dataset` (its name in a `resources.yaml`), `sha256` |
| `legacy` | a result from before the inquiry, untraced | `commit` (permalink), `note` (permalink to the note that reports it) |
| `sub-inquiry` | a child's finding | `finding` (permalink at a commit), `status` (the child's, at that commit) |

`phase` is `explore` or `confirm`. A permalink is at a commit, so the note reads correctly without the other inquiry checked out; `rkt check` finds the commit where a clone is present. Evidence accumulates: new items are appended, never replace old ones.

## Status

- **`hint`**: from an explore phase, from too few seeds or samples, from legacy evidence only, or resting on any `sub-inquiry` evidence that is a hint (rule 11).
- **`confirmed`**: only from a confirm phase under its protocol, with at least one `run`, `derivation`, `reproduction` or `measurement` item of `phase: confirm`, or `sub-inquiry` items that are all confirmed; a `reviewed` verdict of `upheld`; and the user's `approved` date. `legacy` and `source` items may stand beside them but never make a finding confirmed.
- **`retracted`** and **`superseded`** notes are kept, never deleted; a superseded one names its `superseded_by`.
- **Recheck**: set when a canary run shows the evidence's code drifted; the status stands until the evidence is rerun. A child's recheck marks the parent findings that cite it.

Each finding has one line in the [findings index](index.md) under its theme.
