---
name: review-finding
description: Review findings adversarially before they are confirmed, by a blind reviewer that tries to break each claim. Use when publish-finding would confirm a finding, or when the user asks for a review.
---

# Review a finding

A finding becomes `confirmed` only once a reviewer who knows nothing of the inquiry has tried to break it and failed. The reviewer is a fresh subagent, **blind**: it sees the claim and its evidence, and never this conversation, the inquiry's history, your reasoning, or what the user hopes the result is. You record its verdict; you do not argue it.

1. **Gather**, for each finding to review: the finding note, and for each evidence item the file it points to at its commit (the phase note, the run's output and configuration or stamp, the derivation and its check, the source's page, the sub-inquiry's finding). Add the phase's protocol from `PLAN.md`, the rule packs `inquiry.yaml` selects (`rules/<pack>.md`), and the core rules (`AGENTS.md`, "Core rules"). Nothing else.
2. **Brief the reviewer.** Spawn one subagent for all the findings of the phase, on the smaller model (`model: sonnet`), with only those files and this brief:

   > You review research findings before they are recorded as confirmed. Try to break each one. Work through this checklist, citing the passage of the evidence for each problem:
   > - Over-claiming: a claim beyond its evidence or its stated scope; a model-only result stated about the physical world without validation.
   > - The protocol: fixed before the runs, with its analysis, stopping rule and refuting result; any deviation logged.
   > - Selection: settings chosen on the evaluated case; leakage between calibration and evaluation (shared samples, time, groups, preprocessing).
   > - The denominator: `tried` and the phase note's list agree, and the claim survives the number of attempts.
   > - Uncertainty: each headline number an estimate with an interval that covers the claim; significance alone is not a claim.
   > - The baseline: the strongest competing method, tuned with the same budget.
   > - Verification: the method checked on a case with a known answer before the result.
   > - Traceability: every number traced to a run, a derivation or a page, with its unit.
   > - Sub-inquiry evidence: the finding no stronger than the child findings it rests on.
   > - The rule packs given.
   >
   > Then give each finding one verdict: `upheld` (it holds as written), `narrowed` (it holds only in a narrower form: give that form), or `rejected` (the evidence does not support it). Be specific and brief.

3. **Record** each verdict in the finding's front matter, its notes in two or three lines, and keep the full report in the phase note under the finding's link:

   ```yaml
   reviewed:
     date: <today>
     verdict: upheld        # upheld | narrowed | rejected
     notes: <what the reviewer tried, and what held>
   ```

4. **Act on it.** `upheld`: the finding may be confirmed, once the user approves (`publish-finding`). `narrowed`: rewrite the claim and its scope as narrowed, then review it again with a new reviewer. `rejected`: it stays `hint`, or is not published; tell the user what failed. Two rounds at most: a finding not upheld after the second stays `hint`.

Done when each finding's `reviewed` holds the verdict of a blind reviewer, and its status agrees with that verdict.
