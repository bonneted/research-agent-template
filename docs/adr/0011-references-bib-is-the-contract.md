# `references.bib` and one pool outside git are the contract; Zotero is the recommended adapter

Each inquiry commits the manifest that rebuilds its resources — `references.bib` for documents, `resources.yaml` for code and data — and the files live in one pool outside git, read-only for agents, linked as `resources/`. An agent adds a reference by its identifier through `refs add`, never by writing BibTeX.

**With Zotero** (recommended): collections mirror the tree (`<root>/<child>/…`); `refs add` files the item in the inquiry's collection and regenerates its `.bib`. ZotMoov moves attachments into one folder, which is the pool; `fetch` resolves a citekey to its attachment through Zotero 7's local API, since linked files never reach the web API, and keeps ZotMoov's file names. **Without Zotero**: `refs add` writes the entry from Crossref, DataCite or arXiv; `fetch` finds `<citekey>.pdf` in the pool or tries open access; a `.bib` exported from any manager works. The mode is detected from a Zotero key and a collection in `inquiry.yaml`.

Carried from the workspace template's ADR 0005, with Zotero made optional.

## Consequences

A new machine gets its pool by copying it, or by Zotero sync plus ZotMoov, or by `fetch` listing what is missing.
