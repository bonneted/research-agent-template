# Finding format

One note per finding in `docs/findings/<slug>.md`, the slug naming the claim (`adam-then-lbfgs-beats-adam-alone`). A finding is recorded once: a second study that bears on it adds evidence to the same note, it never writes another.

```markdown
---
status: hint            # hint | confirmed | retracted | superseded
evidence:
  - https://gitlab.kuleuven.be/<group>/<study>/-/blob/<sha>/docs/wiki/phases/NN-slug.md
spimat: <sha>           # the library commit the evidence ran on
superseded_by: "[[other-finding]]"   # only when status is superseded
recheck: <why>          # optional: a canary run showed the code drifted since
---

# The claim, as one sentence

**Claim.** What holds, with the numbers that show it.

**Conditions.** Where it was shown: problem, arms, seeds, phase type.

**Rules out.** What it makes not worth trying again.
```

- **Status.** `hint` from an explore phase or too few seeds; `confirmed` only from a confirm phase under its decision rules; `retracted` and `superseded` notes are kept, never deleted.
- **Evidence.** Permalinks at a commit (`<study>/-/blob/<sha>/<path>`) to the phase note and the counted runs, so the note reads correctly without the study checked out ([[0003-hub-cites-studies-by-permalink-mounts-are-local]]). Evidence accumulates: new permalinks are appended, never replace old ones.
- **`spimat`.** The library commit the runs stamped; with evidence from several pins, the newest.
- **Recheck.** Set when the evidence's code drifted; the status stands until the evidence is rerun, then the mark is removed.

Each finding has one line in [[findings/index|the findings index]] under its theme.
