---
name: digest-source
description: Digest a resource into the wiki, a document from references.bib or a code resource from resources.yaml. Use when the resource manifest gains an entry, a PDF or clone appears in resources/, or the user asks to read or digest a paper, thesis or repository.
---

# Digest a resource

1. **Scope.** List the resources the manifest names: each citekey of `references.bib` and each code resource of `resources.yaml`. A code resource with `source_of: <citekey>` is that document's source form: it is digested as the document, never as code. Work through each listed resource with no note in `docs/wiki/sources/`. One not in `resources/` yet: run `uv run fetch`, and put what it still reports missing on a list for the user.
2. **Reference.** A paper the user asks for that `references.bib` lacks: add it with `uv run refs add <DOI | arXiv id | URL>`, never by writing BibTeX; it prints the citekey. Then `uv run fetch` for its PDF. A thesis, report or slides has no identifier `refs` takes: ask the user to add it in Zotero, then `uv run refs pull`. It joins the list of step 1.
3. **Read** the full text, methods and results, not only the abstract.
   - A document with a source form: the source at `resources/code/<name>/`, for LaTeX from the main `.tex` through its `\input` and `\include`. Quote equations and values from it as written.
   - Any other document: `resources/papers/<citekey>.pdf` (`pdftotext`, else `pypdf`).
   - A code resource: `resources/code/<name>/`, at its pinned commit. When `git -C resources/code/<name> rev-parse HEAD` is another commit, read files with `git show <commit>:<path>` there.
4. **Write the note** in `docs/wiki/sources/`. "What we take" is judged against `docs/CONTEXT.md` and the project line in `AGENTS.md`. If the project scope is still empty, ask the user what the resource is for before writing it.
   - A document, as `<citekey>.md`:

     ```markdown
     # Author et al. (year): what it does, in a few words

     [@citekey]. One paragraph: problem, method, data, main result with numbers.

     ## What we take
     - **Idea.** What we reuse and why, with the equation or value. → [[concept-note]]

     ## What we don't take
     What we set aside, and why.
     ```

   - A code resource, as `<name>.md`, citing code by permalink at the pinned commit (on GitLab `<url without .git>/-/blob/<commit>/<path>#L<first>-<last>`, on GitHub `<url without .git>/blob/<commit>/<path>#L<first>-L<last>`):

     ```markdown
     # name: what it does, in a few words

     [name @ <commit, 12 characters>](<url of the tree at the commit>). One paragraph: what it implements, its language and main dependencies, how it is run, and the work it backs ([@citekey]).

     ## What we take
     - **Idea.** What we reuse and why, at [`path/to/file.py` L10–42](<permalink>). → [[concept-note]]

     ## What we don't take
     What we set aside, and why.
     ```

5. **Concepts.** For each idea the project reuses, add a line to the matching `docs/wiki/concepts/` note, or create one when two sources or the code need it.
6. **Reading list.** References a document cites that the project needs go in `docs/wiki/reading-list.md`, with why and where they are cited. Remove the rows of the resources you digested.
7. **Index.** Add each note to `docs/wiki/index.md` under Sources, one line: `[[citekey]]: author, what it is for us`, or `[[name]]: code, what it is for us`.

Done when every resource of step 1 has a note linked from the index or is on the list for the user, and every `[[link]]` you wrote resolves to a file.
