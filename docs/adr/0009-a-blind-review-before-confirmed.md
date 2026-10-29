# A finding is confirmed only after a review with no study context

The agent that ran a phase is the worst judge of its claim: it knows what it meant, and reads that into the evidence. So a finding becomes `confirmed` only after the `review-finding` skill: a fresh subagent, given only the finding note, its evidence, the phase's protocol and the rules, tries to break the claim (over-claiming, a weak baseline, confounded factors, missing uncertainty, untraced numbers, rule-pack violations) and gives a verdict, `upheld`, `narrowed` or `rejected`. The verdict is recorded in the finding's front matter (`reviewed`); `publish-finding` calls the review when the status would be `confirmed`, and `ws check` fails a confirmed finding without an `upheld` verdict.

## Consequences

Confirming costs a review; a hint may have one when the user asks. A narrowed claim is rewritten and reviewed again by a new reviewer. The reviewer's full report stays in the phase note.
