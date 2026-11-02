# Findings have a status, and their evidence has kinds

A finding is one note with a status, `hint | confirmed | retracted | superseded`, and evidence items of a kind — `run`, `derivation`, `reproduction`, `source`, `measurement`, `legacy`, `sub-inquiry` — each with the fields that make it checkable (`docs/findings/finding-format.md`). Only a confirm phase gives `confirmed`; legacy or source evidence alone never does. `sub-inquiry` evidence is a child's finding at a permalink; its status bounds the parent's (ADR 0003).

Carried from the workspace template's ADR 0006, which took it from the spimat workspace.

## Consequences

Never edit a status by hand: `publish-finding` and `review-finding` change it, and `check` reads the kinds and their fields.
