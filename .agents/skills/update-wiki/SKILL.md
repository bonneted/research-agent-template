---
name: update-wiki
description: Bring the wiki in line with the code. Use after code changes that add a method, change a result, or contradict a wiki note, or when the user asks to update the wiki.
---

# Update the wiki after code changes

1. **Diff.** List what changed since the wiki was last touched (`git diff`, `git log`). For each change, note the method, the result, or the assumption it touches.
2. **Match.** Find the notes in `docs/wiki/concepts/` that cover each item (search by term from `docs/CONTEXT.md`).
3. **Edit.** For each match, update the note: what the code does now, the key numbers, and a pointer to the code (`src/<module>.py`, function name). Mark a result that contradicts a source as a **Discrepancy:** line naming both.
4. **New concept.** A method with no note gets one: what it is, why this project uses it, where it lives in the code, which sources back it (`[[citekey]]`). Add it to `docs/wiki/index.md` under Concepts.
5. **Terms.** A new term that the code and notes now share goes in `docs/CONTEXT.md`.

Done when every change from step 1 is reflected in a note or explicitly judged not wiki-worthy (tell the user which), and every `[[link]]` resolves.
