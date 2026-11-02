---
name: digest-source
description: Digest a resource into the wiki, a document from references.bib or a code resource from resources.yaml. Use when the resource manifest gains an entry, ws fetch brings a resource into the pool, or the user asks to read or digest a paper, thesis or repository.
---

# Digest a resource

1. **Scope.** List the resources this repository's resource manifest names: each citekey of `references.bib` and each code resource of `resources.yaml`. Digest only these, though the pool holds more. A code resource with `source_of: <citekey>` is that document's source form: it is digested as the document, never as code. A code resource with `code_of: <citekey>` (or a list) implements those documents: it is digested as code, and each of those documents' notes links it. Work through each listed resource with no note in `docs/wiki/sources/`; one that is not in the pool yet goes on the list for the user, with the `ws fetch` line that reports it.
2. **Reference.** A paper the user asks for that `references.bib` lacks: add it with `uv run ws refs add <doi | arXiv id | URL>` in the hub (`--repo <name>` for a study, or `uv run --directory ../<hub> ws refs add --repo <study> <id>` from it), never by writing BibTeX; it prints the citekey and pulls. Then `uv run ws fetch` in the hub for its PDF. A thesis, report or slides has no identifier `ws` takes: ask the user to add it in Zotero, then `ws refs pull`. It joins the list.
3. **Read** the full text, methods and results, not only the abstract. Read a clone of `resources/code/` at this repository's pin: when `git -C resources/code/<name> rev-parse HEAD` is another commit, read files with `git show <commit>:<path>` there.
   - A document with a source form: the LaTeX at `resources/code/<name>/`, from the main `.tex` through its `\input` and `\include`. Quote equations and values from it as written.
   - Any other document: `resources/papers/<citekey>.pdf`, extracted with `pypdf` through uv.
   - A code resource: `resources/code/<name>/`.
4. **Write the note** in `docs/wiki/sources/`. "What we take" is judged against `docs/CONTEXT.md` and the project line in `AGENTS.md`, and answers the resource's "Why" in `docs/wiki/reading-list.md` when it has a row there; if the project scope is still empty, ask the user what the resource is for before writing it.
   - A document, as `<citekey>.md`:

     ```markdown
     # Author et al. (year): what it does, in a few words

     [@citekey]. One paragraph: problem, method, data, main result with numbers.

     ## What we take
     - **Idea.** What we reuse and why, with the equation or value. → [[concept-note]]

     ## What we don't take
     What we set aside, and why.
     ```

     A document that a code resource's `code_of` names has, under its paragraph, the line `Code: [[name]], where it implements <method>.`, and its "What we take" cites the code where the code settles a value the text leaves open.

   - A thesis, one note per chapter: `<citekey>-ch<N>.md` per chapter in the document shape, titled by the chapter, and `<citekey>.md` holding the paragraph and a list of the chapter notes.
   - A code resource, as `<name>.md`, citing code by permalink at the pinned commit (on GitLab, `<url without .git>/-/blob/<commit>/<path>#L<first>-<last>`; on GitHub, `<url without .git>/blob/<commit>/<path>#L<first>-L<last>`). With `code_of`, it says which of its documents each method comes from, and where the code departs from the document:

     ```markdown
     # name: what it does, in a few words

     [name @ <commit, 12 characters>](<url without .git>/-/tree/<commit>). One paragraph: what it implements, its language and main dependencies, how it is run, and the work it backs ([@citekey]).

     ## What we take
     - **Idea.** What we reuse and why, at [`path/to/file.py` L10–42](<permalink>). → [[concept-note]]

     ## What we don't take
     What we set aside, and why.
     ```

5. **Concepts.** For each idea the project reuses, add a line to the matching `docs/wiki/concepts/` note, or create one when two sources or the code need it.
6. **Reading list.** References a document cites that the project needs go in `docs/wiki/reading-list.md`, with why and where they are cited. A row stays there, with its citekey once `ws refs add` gives one, until its digest is written; remove the rows of the resources you digested.
7. **Follow-ups.** What the reading shows needs doing outside the note goes as a row in `docs/wiki/follow-ups.md`: a defect or a mismatch with the library code, a check to run, a correction to another note. Give what was found, the note that raised it, and the action. Fix it in the same turn instead when it is a wiki note you can correct.
8. **Index.** Add each note to `docs/wiki/index.md` under Sources, one line: `[[citekey]]: author, what it is for us`, or `[[name]]: code, what it is for us`. A thesis's chapter notes are reached from its `<citekey>.md`.

Done when every resource of step 1 has a note linked from the index or is on the list for the user, every follow-up it raised is a row or done, and every `[[link]]` you wrote resolves to a file.
