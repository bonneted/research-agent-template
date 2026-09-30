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

Every document (paper, thesis, report, slides) is a Zotero item, its PDF here at `papers/<citekey>.pdf`.

1. Install the [Better BibTeX](https://retorque.re/zotero-better-bibtex/) plugin for Zotero.
2. Put the project's documents in one Zotero collection.
3. Right-click the collection → **Export Collection…** → format *Better BibTeX*, tick **Keep updated**, and save it as `references.bib` at the repo root. Zotero now rewrites the file whenever the collection changes.
4. Copy each PDF to `papers/` named `<citekey>.pdf`, using the citekey shown in Zotero's Info pane. The [ZotMoov](https://github.com/wileyyugioh/zotmoov) plugin can do this automatically with a `{citekey}` file-name pattern.

A paper the agent finds first (from a DOI) can go the other way: the agent adds the BibTeX entry, and you import it into Zotero so the next export keeps it.

## resources.yaml: code and data

```yaml
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

- **Documents.** For each citekey without a PDF in `papers/`, it tries the Zotero Web API (when configured), then arXiv (by `eprint` with `archivePrefix = {arXiv}`, an arXiv DOI or URL), then Unpaywall by DOI, and saves the PDF as `papers/<citekey>.pdf`.
- **Code.** It clones each code resource into `code/<name>/` at its commit, and moves the clone when the pin changes. A clone with uncommitted changes is never moved.
- **Data.** It checks each dataset's sha256.

It ends with what is still missing, to copy in by hand. A wrong checksum, a clone it cannot make, or a `source_of` citekey missing from `references.bib` is a `FAILED` line and a non-zero exit; something only missing is not.

Retrieval is configured per user in `~/.config/research-agent/retrieval.yaml` (or under `$XDG_CONFIG_HOME`), outside git. Both entries are optional:

```yaml
zotero:                      # off unless set; the PDFs must be in Zotero's own storage, not WebDAV
  library: users/1234567     # your user ID (zotero.org/settings/keys), or groups/<id>
  api_key: <a key with read access to the library and its files>
email: you@example.org       # Unpaywall asks for one; without it, it is skipped
```

Without any configuration, `fetch` still tries arXiv.
