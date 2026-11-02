# `references.bib` and one pool outside git are the contract; Zotero is the recommended adapter

Each inquiry commits the manifest that rebuilds its resources — `references.bib` for documents, `resources.yaml` for code and data — and the files live in one pool outside git, read-only for agents, linked as `resources/`. An agent adds a reference by its identifier through `refs add`, never by writing BibTeX.

**With Zotero** (recommended): collections mirror the tree (`<root>/<child>/…`); `refs add` files the item in the inquiry's collection and regenerates its `.bib`. ZotMoov moves attachments into one folder of linked files, which never reach the web API; `fetch` resolves a citekey to its attachment, through the Zotero app's local API where Zotero is installed, or else through the Web API, whose attachment records do sync, reading the file from the ZotMoov folder synced over a drive (`zotero_base`); it copies the file into the pool as `papers/<citekey>.pdf`. A machine needs no Zotero app: the Web API and the synced folder suffice. Setting Zotero's linked attachment base folder to the ZotMoov folder records portable paths; an absolute path recorded on another machine is found by its file name under `zotero_base`. The ZotMoov folder is a source, not the pool: every instruction and check reads a document at the same path whatever the reference manager, at the cost of a second copy of each PDF. **Without Zotero**: `refs add` writes the entry from Crossref, DataCite or arXiv; `fetch` finds `<citekey>.pdf` in the pool or tries open access; a `.bib` exported from any manager works. The mode is detected from a Zotero key and a collection in `inquiry.yaml`.

Carried from the workspace template's ADR 0005, with Zotero made optional.

## Consequences

A new machine gets its pool by copying it, or by `fetch` from its own Zotero, or by `fetch` listing what is missing with the command that copies it in. From WSL, the Zotero app on Windows is reached at its local API only with WSL's mirrored networking, or at the address set in `zotero_local`.
