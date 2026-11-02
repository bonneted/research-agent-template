---
name: digest-source
description: Digest a resource into the wiki, a document from references.bib or a code resource from resources.yaml. Use when the resource manifest gains an entry, rkt fetch brings a resource into the pool, or the user asks to read or digest a paper, thesis or repository.
---

# Digest a resource

1. **Scope.** List the resources this inquiry's manifest names: each citekey of `references.bib` and each code resource of `resources.yaml`. Digest only these, though the pool holds more. A code resource with `source_of: <citekey>` is that document's source form: digest it as the document. One with `code_of: <citekey>` (or a list) implements those documents: digest it as code, and link it from each of their notes. Work through each listed resource with no note in `docs/wiki/sources/`; one not in the pool yet goes on the list for the user, with the `rkt fetch` line that reports it.
2. **Already digested above?** Search the ancestors' source indexes for the citekey or its DOI (`../../docs/wiki/sources/index.md`, then up while `inquiry.yaml` names a parent). A source an ancestor digested gets no second digest: link that note from the concept that uses it, and state there only what this inquiry takes from it.
3. **Reference.** A paper the user asks for that `references.bib` lacks: add it with `rkt refs add <DOI | arXiv id | URL>`, which prints the citekey; then `rkt fetch` for its PDF. A thesis, report or slides has no identifier: ask the user to add it in Zotero, then `rkt refs pull`. It joins the list.
4. **Read** the full text, methods and results, not only the abstract.
   - A document with a source form: the LaTeX at `resources/code/<name>/`, from the main `.tex` through its `\input` and `\include`. Quote equations and values as written.
   - Any other document: `resources/papers/<citekey>.pdf`, extracted with `pdftotext`, or `pypdf` through uv.
   - A code resource: `resources/code/<name>/`, at this inquiry's pin: when `git -C resources/code/<name> rev-parse HEAD` is another commit, read with `git show <commit>:<path>` there.
5. **Write the note** in `docs/wiki/sources/`. "What we take" is judged against this inquiry's question (`inquiry.yaml`) and `GLOSSARY.md`, and answers the resource's "why" in `docs/wiki/reading-list.md` when it has a line there; with the question still empty, ask the user what the resource is for first. Every value carries its page (`[@key, p. 7]`), checked against the passage (rule 8).
   - A document, as `<citekey>.md`:

     ```markdown
     # Author et al. (year): what it does, in a few words

     [@citekey]. One paragraph: problem, method, data, main result with numbers and pages.

     ## What we take
     - **Idea.** What we reuse and why, with the equation or value and its page. → [concept](../concepts/concept.md)

     ## What we don't take
     What we set aside, and why.
     ```

     A document a code resource's `code_of` names gets, under its paragraph, `Code: [name](name.md), where it implements <method>.`
   - A thesis, one note per chapter: `<citekey>-ch<N>.md` in the document shape, and `<citekey>.md` holding the paragraph and a list of the chapter notes.
   - A code resource, as `<name>.md`, citing code by permalink at the pinned commit (GitLab `<url>/-/blob/<commit>/<path>#L<a>-<b>`, GitHub `<url>/blob/<commit>/<path>#L<a>-L<b>`), with what it implements, how it is run, and, with `code_of`, where it departs from its documents.
6. **Concepts.** For each idea this inquiry reuses, add a line to the matching note of `docs/wiki/concepts/`, or create one (and its line in `concepts/index.md`) when two sources or the code need it.
7. **Reading list.** References a document cites that the inquiry needs go in `docs/wiki/reading-list.md`, with why and where they are cited; remove the lines of the resources you digested.
8. **Index.** Add each note to `docs/wiki/sources/index.md`, one line: `- [citekey](citekey.md): author, what it is for us`. A thesis's chapter notes are reached from its `<citekey>.md`.
9. **Check.** Run `rkt check` and fix what it reports on the notes you wrote.

Done when every resource of step 1 has a note reachable from the index, is linked from an ancestor's digest, or is on the list for the user, and `rkt check` reports nothing on your notes.
