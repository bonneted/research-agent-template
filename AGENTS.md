# Project

<!-- One or two lines: the research question and its scope. Written during project init (see README). -->

Start from `docs/wiki/index.md`; vocabulary is in `docs/CONTEXT.md`, decisions in `docs/adr/`.

## Layout

- **`resources/`** is outside git and read-only: `papers/<citekey>.pdf`, `legacy/` (legacy code, reports, data). Extract PDF text with `pdftotext` if available, otherwise `pypdf`.
- **`references.bib`** is the reference list, exported from Zotero. Cite in docs as `[@citekey]`.
- **`docs/`** is an Obsidian vault: `wiki/`, `CONTEXT.md`, `adr/`. Link notes with `[[note-name]]`.
- **`src/`, `tests/`** hold the code. Use `uv` for everything: `uv run python -m pytest`.

## The wiki

The wiki is the project memory, read by the user in Obsidian and by you. Before answering a question about the project, read `docs/wiki/index.md` and the notes it links, and cite the notes you used. When a claim comes from a paper, check it against the PDF passage.

Keep the wiki current as part of the work, in the same turn:

- **New PDF in `resources/papers/`** → follow `.agents/skills/digest-source/SKILL.md`.
- **Code change** that adds a method, changes a result, or contradicts a note → follow `.agents/skills/update-wiki/SKILL.md`.

**Parsimony rule:** one note per source or concept. A note states what this project uses or rejects from its subject, with a pointer to where it is used. A digest is a selection, never a full summary.
