---
name: digest-source
description: Digest a paper into the wiki. Use when a PDF is added to resources/papers, or the user asks to read, digest or add a paper.
---

# Digest a source

For each PDF in `resources/papers/` that has no note in `docs/wiki/sources/`:

1. **Reference.** Make sure `references.bib` has its entry under the PDF's citekey. If missing, build it from the DOI (Crossref) and tell the user to add the paper to Zotero so the next export keeps it.
2. **Read** the full text (`pdftotext`, else `pypdf`). Read methods and results, not only the abstract.
3. **Write `docs/wiki/sources/<citekey>.md`** with this shape:

   ```markdown
   # Author et al. (year): what it does, in a few words

   [@citekey]. One paragraph: problem, method, data, main result with numbers.

   ## What we take
   - **Idea.** What we reuse and why, with the equation or value. → [[concept-note]]

   ## What we don't take
   What we set aside, and why.
   ```

   "What we take" is judged against `docs/CONTEXT.md` and the project line in `AGENTS.md`. If the project scope is still empty, ask the user what the paper is for before writing it.
4. **Concepts.** For each idea the project reuses, add a line to the matching `docs/wiki/concepts/` note, or create one when two sources or the code need it.
5. **Reading list.** References the paper cites that the project needs go in `docs/wiki/reading-list.md`, with why and where they are cited.
6. **Index.** Add the note to `docs/wiki/index.md` under Sources, one line: `[[citekey]]: author, what it is for us`.

Done when every PDF in `resources/papers/` has a source note linked from the index, and every `[[link]]` you wrote resolves to a file.
