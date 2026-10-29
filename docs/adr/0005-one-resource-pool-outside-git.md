# One resource pool outside git, rebuilt from committed manifests

Every document, code resource and dataset of the workspace lives in one uncommitted folder, the pool, and each repository commits only the manifest that can rebuild its part: a bibliography written from Zotero, and a list of code and data with their commits and checksums. PDFs are copyrighted and heavy, and resources shared by several studies would otherwise be stored several times. Scope is kept by the manifests rather than by folders: a study digests only what its own manifest lists, even though the pool holds everything.

Taken from the spimat workspace (its ADRs 0005 and 0007). Zotero is the source of every bibliography: `ws refs` writes `references.bib` from a repository's collection, `<zotero_root>/<repository>`, and an agent adds a reference by its identifier, never by writing BibTeX. The user's configuration (`~/.config/research-ws/retrieval.yaml`) has a section per workspace, so one machine serves several workspaces with different Zotero libraries.

## Consequences

A new machine gets its pool by copying the old one or by `ws fetch`, which tries open-access retrieval and otherwise lists what is missing. Material that must not be read is never put in the pool: a workspace's old document folders are not its pool.
