# Resources

Everything here except this file is ignored by git: papers are copyrighted and heavy, code resources have their own repositories, and legacy material is not yours to version. The agent reads these files and never edits them.

```
papers/    <citekey>.pdf, one per entry in references.bib
code/      <name>/, a clone of each code resource in resources.yaml, at its commit
data/      <name>, each dataset in resources.yaml
legacy/    anything else: legacy code, reports, data
```

What belongs here is listed by two committed files at the repo root, the **resource manifest**, so that `uv run fetch` can rebuild this folder on any machine.

## references.bib: the documents

Every document (paper, thesis, report, slides) has an entry in `references.bib` and its PDF here at `papers/<citekey>.pdf`. The file is never edited by hand or by the agent: it is written by `uv run refs`.

### With Zotero (recommended)

The bibliography is a Zotero collection, and `references.bib` is pulled from it.

1. Create a collection for the project in Zotero, and name it in `resources.yaml`: `zotero_collection: Projects/my-project` (its path of names from the library's top, or its 8-character key).
2. Create a key at [zotero.org/settings/keys](https://www.zotero.org/settings/keys) with **write** access to the library (a read-only key pulls, but cannot add), and put it in your retrieval configuration (below) with your user ID.
3. `uv run refs pull` rewrites `references.bib` from the collection, entries sorted by citekey. An item without a citekey gets one (`raissi2019physics`), written back to Zotero. An entry gone from the collection is removed, with a warning if a note in `docs/` still cites it.
4. `uv run refs add <DOI | arXiv id | doi.org or arxiv.org URL>` adds a reference: the metadata comes from Crossref, DataCite or arXiv, the item goes in the collection (or joins it, if the library already has it), and `references.bib` is pulled. A thesis, report or slides has no such identifier: add it in Zotero, then `uv run refs pull`.

`refs` only ever adds to Zotero (items, collection memberships, a citekey where there was none, PDF attachments); it never changes or deletes a value already set. The committed `references.bib` stays the source for anyone without a key.

### Without Zotero

`uv run refs add <identifier>` writes the looked-up entry into `references.bib` itself. Anything else (a thesis, a report) you add by hand in BibTeX. If you configure Zotero later, the first `refs pull` replaces the file with the collection: put the references in it first.

## resources.yaml: code and data

```yaml
zotero_collection: Projects/my-project
code:
  - name: solver
    url: https://github.com/someone/solver.git
    commit: "<full commit hash>"
  - name: thesis-tex
    url: https://gitlab.example.org/me/thesis.git
    commit: "<full commit hash>"
    source_of: <citekey>   # optional: this repository is the source form of that document
data:
  - name: measurements.h5
    source: where a good copy is kept
    sha256: "<sha256 of the file>"
```

Quote commits and checksums: YAML reads a hash made only of digits as a number. A code resource is pinned at a commit, so its digest cites code by permalink. With `source_of`, the agent reads that document from its source (a thesis's LaTeX, say) rather than from the PDF, and gets the equations as written. Data is copied here by hand and checked against its sha256 (`sha256sum`).

## uv run fetch

`uv run fetch` brings in what the manifest lists:

- **Bibliography.** It first pulls `references.bib` from Zotero, as `refs pull` does. Without a Zotero configuration, a named collection or a network, it says so in one line and reads the committed file.
- **Documents.** For each citekey without a PDF in `papers/`, it tries the Zotero Web API (when configured), then arXiv (by `eprint` with `archivePrefix = {arXiv}`, an arXiv DOI or URL), then Unpaywall by DOI, and saves the PDF as `papers/<citekey>.pdf`. With `upload_pdfs: true`, a PDF found on arXiv or Unpaywall is also attached to its Zotero item.
- **Code.** It clones each code resource into `code/<name>/` at its commit, and moves the clone when the pin changes. A clone with uncommitted changes is never moved.
- **Data.** It checks each dataset's sha256.

It ends with what is still missing, to copy in by hand. A wrong checksum, a clone it cannot make, or a `source_of` citekey missing from `references.bib` is a `FAILED` line and a non-zero exit; something only missing is not.

Retrieval is configured per user in `~/.config/research-agent/retrieval.yaml` (or under `$XDG_CONFIG_HOME`), outside git. Every entry is optional:

```yaml
zotero:                      # off unless set; PDFs must be in Zotero's own storage, not WebDAV
  library: users/1234567     # your user ID (zotero.org/settings/keys), or groups/<id>
  api_key: <a key with write access to the library and its files>
email: you@example.org       # Unpaywall asks for one; without it, it is skipped
upload_pdfs: false           # true: attach the PDFs found on arXiv or Unpaywall to their Zotero item
```

Without any configuration, `fetch` still tries arXiv.
