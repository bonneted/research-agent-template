# Project

<!-- One or two lines: the research question and its scope. Written during project init (see README). -->

Start from `docs/wiki/index.md`; vocabulary is in `docs/CONTEXT.md`, decisions in `docs/adr/`.

## Layout

- **`resources/`** is outside git and read-only: `papers/<citekey>.pdf`, `code/<name>/`, `data/<name>`, `legacy/` (anything else). Extract PDF text with `pdftotext` if available, otherwise `pypdf`.
- **`references.bib`** and **`resources.yaml`** are the resource manifest: every document (cite in docs as `[@citekey]`), and every code resource at a pinned commit and dataset with its sha256. `uv run fetch` brings what they list into `resources/` and prints what is still missing.
- **`references.bib` is written by `uv run refs`, never by hand or by you.** Add a reference with `uv run refs add <DOI | arXiv id | URL>`: it takes the metadata from Crossref, DataCite or arXiv and prints the citekey. A thesis, report or slides: ask the user to add it in Zotero, then `uv run refs pull`.
- **`docs/`** is an Obsidian vault: `wiki/`, `CONTEXT.md`, `adr/`. Link notes with `[[note-name]]`.
- **`src/`, `tests/`** hold the code; `tools/fetch/` holds the `fetch` and `refs` commands. Use `uv` for everything: `uv run python -m pytest`.

## The wiki

The wiki is the project memory, read by the user in Obsidian and by you. Before answering a question about the project, read `docs/wiki/index.md` and the notes it links, and cite the notes you used. When a claim comes from a document, check it against the passage in its source form or PDF.

Keep the wiki current as part of the work, in the same turn:

- **New resource** in `references.bib` or `resources.yaml`, or newly in `resources/` → follow `.agents/skills/digest-source/SKILL.md`.
- **Code change** that adds a method, changes a result, or contradicts a note → follow `.agents/skills/update-wiki/SKILL.md`.

**Parsimony rule:** one note per source or concept. A note states what this project uses or rejects from its subject, with a pointer to where it is used. A digest is a selection, never a full summary.
