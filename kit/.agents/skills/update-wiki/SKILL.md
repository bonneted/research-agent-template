---
name: update-wiki
description: Bring the wiki in line with the code and the tree. Use after code changes that add a method, change a result, or contradict a wiki note; when a source or concept is needed by a second branch of the tree; or when the user asks to update the wiki.
---

# Update the wiki

1. **Diff.** List what changed since the wiki was last touched (`git diff`, `git log`). For each change, note the method, the result, or the assumption it touches.
2. **Match.** Find the notes that cover each item: the indexes of `docs/wiki/` and a search by the terms of `GLOSSARY.md`.
3. **Edit.** For each match, write what the code does now, the key numbers with their units, and a pointer to the code (file and function). A result that contradicts a source gets a **Discrepancy:** line naming both.
4. **Prune.** A sentence the change makes untrue is rewritten or deleted, never contradicted further down; a superseded number is replaced, never kept beside the new one.
5. **New concept.** A method with no note gets one, `docs/wiki/concepts/<name>.md`: what it is, why this inquiry uses it, where it lives in the code, which sources back it. Add its line to `concepts/index.md`.
6. **Terms.** A term the code and notes now share goes in `GLOSSARY.md` (the `domain-modeling` skill).
7. **Move up.** A source digest or concept note that another branch of the tree needs moves to the lowest common ancestor of the two:
   1. In the ancestor, write the note from the original, keeping what both branches share; add it to the ancestor's index for its folder, and the citekey to the ancestor's `references.bib` (`rkt refs add` there).
   2. In each branch, keep a short note stating only what that branch takes, linking up to the ancestor's note (`../../docs/wiki/...`, one `../..` per level).
   3. Rewrite every link to the old note, and commit the ancestor and each branch.
8. **Check.** Run `rkt check` (in each inquiry you touched) and fix what it reports.

Done when every change of step 1 is reflected in a note or judged not wiki-worthy (tell the user which), every note the tree shares lives at its lowest common ancestor, and `rkt check` reports nothing.
