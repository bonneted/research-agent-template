# Finding format

One note per finding in `docs/findings/<slug>.md`, the slug naming the claim (`a-mesh-of-three-elements-per-ply-converges-the-burst-pressure`). A finding is recorded once: a second study that bears on it adds evidence to the same note, it never writes another. `ws check` checks the front matter against this format.

```markdown
---
status: hint            # hint | confirmed | retracted | superseded
evidence:
  - kind: run
    phase: confirm      # the type of the phase that produced it
    note: https://<gitlab>/<group>/<study>/-/blob/<sha>/docs/wiki/phases/NN-slug.md
    stamp: NN-slug/<run>          # the run's folder, as the phase note reports it
  - kind: source
    citekey: smith2020
    page: 7
library: <sha>          # optional: the library commit the runs stamped
superseded_by: "[[other-finding]]"   # only when status is superseded
recheck: <why>          # optional: a canary run showed the code drifted since
reviewed:               # required for confirmed: the review-finding skill's verdict
  date: 2026-10-29
  verdict: upheld       # upheld | narrowed | rejected
  notes: what the reviewer tried, and what held
---

# The claim, as one sentence

**Claim.** What holds, with the numbers that show it, each with its unit and uncertainty.

**Conditions.** Where it was shown: problem, arms, seeds or samples, meshes, phase type.

**Rules out.** What it makes not worth trying again.
```

## Evidence kinds

| kind | what it is | must carry |
|---|---|---|
| `run` | a stamped computation | `phase`, `note` (permalink to the phase note), `stamp` (the run, `NN-slug/<run>`) |
| `derivation` | an analytical result | `phase`, `derivation` (permalink to it), `check` (permalink to the test or CAS script, such as sympy, that checks it) |
| `reproduction` | a published number reproduced | `phase`, `citekey`, `where` (page, table or figure), `published`, `reproduced`, `tolerance` |
| `source` | a cited passage | `citekey`, `page`; checked against the PDF |
| `measurement` | experimental data | `phase`, `dataset` (its name in a `resources.yaml`), `sha256` |
| `legacy` | a result from before the workspace, unstamped | `commit` (permalink to the commit), `note` (permalink to the note that reports it) |

`phase` is `explore` or `confirm`. A permalink is at a commit (`<repository>/-/blob/<sha>/<path>`), so the note reads correctly without the study checked out ([[0004-the-hub-cites-studies-by-permalink]]); `ws check` finds the commit in the local clone, and for a run checks the type its phase declares at that commit. Evidence accumulates: new items are appended, never replace old ones.

## Status

- **`hint`**: from an explore phase, too few seeds or samples, or legacy evidence only.
- **`confirmed`**: only from a confirm phase under its decision rules, with at least one `run`, `derivation`, `reproduction` or `measurement` item of `phase: confirm`, and a `reviewed` verdict of `upheld` from the `review-finding` skill. `legacy` and `source` items may stand beside them but never make a finding confirmed.
- **`retracted`** and **`superseded`** notes are kept, never deleted; a superseded one names its `superseded_by`.
- **Recheck.** Set when a canary run shows the evidence's code drifted; the status stands until the evidence is rerun, then the mark is removed.
- **`library`.** The library commit the runs stamped; with evidence from several pins, the newest.

Each finding has one line in [[findings/index|the findings index]] under its theme.
