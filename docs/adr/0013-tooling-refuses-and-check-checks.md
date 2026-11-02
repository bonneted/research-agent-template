# Tooling refuses what breaks a rule, and `check` checks what a machine can tell

A rule an agent can forget is weaker than a tool that refuses. `refs` refuses to write a reference without an identifier, which is what makes rule 8 hold against fabricated citations: an agent cannot cite a paper it made up; the rigour pack's stamp refuses a confirm run from a dirty tree or an unfrozen protocol. What cannot be refused is checked by `check`: links resolve, every note is reachable from its index, no sideways links, sub-inquiries match their routing entries, findings' statuses and evidence fields, no parent finding stronger than its sub-inquiry evidence, citekeys in `references.bib`, each with a DOI, arXiv id or URL or flagged as hand-entered in Zotero. It prints one line per violation and exits non-zero, so the agent fixes them itself; a pack adds its own checks.

Carried from the workspace template's ADR 0008; the protocol freeze and the stamp move to the rigour pack.
