# A finding is confirmed after a blind review, and by the user

The agent that ran a phase is the worst judge of its claim. So a finding becomes `confirmed` only after `review-finding`: a fresh subagent, given only the finding, its evidence, the phase's protocol and the rules — never the conversation or what the user hopes, since models tell users what they want to hear — tries to break the claim against a checklist built on established ones (the NeurIPS reproducibility checklist, the leakage taxonomy of Kapoor & Narayanan, the V&V framework of Roy & Oberkampf), and gives `upheld`, `narrowed` or `rejected`, recorded in the finding's front matter. Then the user approves the promotion: the agent never certifies its own work. The user also approves a confirm protocol before it is frozen.

Carried from the workspace template's ADR 0009, with the user's approval added.

## Consequences

Confirming costs a review and a question to the user; a narrowed claim is rewritten and reviewed by a new reviewer, two rounds at most (ADR 0010).
