# Resources

Everything here except this file is ignored by git: papers are copyrighted and heavy, and legacy material is not yours to version. The agent reads these files and never edits them.

```
papers/    <citekey>.pdf, one per entry in references.bib
legacy/    legacy code, reports, data
```

## Zotero → references.bib + papers/

1. Install the [Better BibTeX](https://retorque.re/zotero-better-bibtex/) plugin for Zotero.
2. Put the project's papers in one Zotero collection.
3. Right-click the collection → **Export Collection…** → format *Better BibTeX*, tick **Keep updated**, and save it as `references.bib` at the repo root. Zotero now rewrites the file whenever the collection changes.
4. Copy each PDF to `papers/` named `<citekey>.pdf`, using the citekey shown in Zotero's Info pane. The [ZotMoov](https://github.com/wileyyugioh/zotmoov) plugin can do this automatically with a `{citekey}` file-name pattern.

A paper the agent finds first (from a DOI) can go the other way: the agent adds the BibTeX entry, and you import it into Zotero so the next export keeps it.
