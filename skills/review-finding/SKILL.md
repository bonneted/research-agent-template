---
name: review-finding
description: Review a finding adversarially before it is confirmed, by a reviewer with no study context who tries to break the claim. Use when publish-finding would make a finding confirmed, or when the user asks for a finding to be reviewed.
---

# Review a finding

A finding becomes `confirmed` only once a reviewer who knows nothing of the study has tried to break it and failed. The reviewer is a fresh subagent: it never sees this conversation, the study's history or your reasoning, only the claim and its evidence. You do not argue its verdict; you record it.

1. **Gather.** The finding note (`../<hub>/docs/findings/<slug>.md`, front matter and body), and for each evidence item the file it points to at its commit: the phase note, the run's `stamp.json` and the report it backs, the derivation and its check, the source's page. Add the study's `PLAN.md` protocol for the phase and the rule packs it selects (`rules/<pack>.md`), and the core rules (the study's `AGENTS.md`, "Core rules"). Nothing else: no other notes, no chat.
2. **Brief the reviewer.** Spawn a subagent with only those files (pasted, or as paths it may read and nothing more) and this brief:

   > You review a research finding before it is recorded as confirmed. Try to break it. Report, with the passage of the evidence for each: over-claiming beyond what the evidence shows (scope, conditions, numbers); a missing or weak baseline, not the strongest classical method at its best setting; confounded factors, or settings selected on the reported metric; a headline number without its uncertainty, or an uncertainty that does not cover the claim; a number that does not trace to a run, a derivation or a page; a violation of the protocol or of a rule of the packs given; a verification on a known case missing before the result. Then give one verdict: `upheld` (the claim holds as written), `narrowed` (it holds only in a narrower form: give that form), or `rejected` (the evidence does not support it). Be specific and brief; do not soften.

3. **Record.** Write the verdict into the finding's front matter, its notes in two or three lines (what was tried, what held or failed):

   ```yaml
   reviewed:
     date: <today>
     verdict: upheld        # upheld | narrowed | rejected
     notes: <what the reviewer tried, and what held>
   ```

   Keep the reviewer's full report in the phase note, under the finding's link.
4. **Act on it.** `upheld`: the finding may be `confirmed`. `narrowed`: rewrite the claim and its conditions as the reviewer narrowed them, then review again with a new subagent. `rejected`: the finding stays `hint` (or is not published); tell the user what failed.

For a `hint` the review is optional; when the user asks for one, record it the same way.

Done when the finding's `reviewed` holds the verdict of a reviewer that saw only the claim and its evidence, and its status agrees with that verdict.
