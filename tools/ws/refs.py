"""`ws refs`: each repository's `references.bib`, written from its Zotero collection."""

import re
from pathlib import Path

from ws import bibtex, lookup, manifest, resources, retrieve, zotero
from ws.manifest import Workspace

# A repository's collection is `<zotero_root>/<repository>`, under the workspace's
# `zotero_root` at the library's top, unless its line in the workspace manifest names
# another by `zotero_collection`.
# A Pandoc citation group, such as `[@a; @b, p. 3]`.
_CITATIONS = re.compile(r"\[[^\[\]]*@[^\[\]]*\]")


def _citing(repository: Path, key: str) -> list[str]:
    """The notes in the repository's `docs/` that cite `key`."""
    cite = re.compile(rf"@{re.escape(key)}(?![\w-])")
    docs = repository / "docs"
    return [
        note.relative_to(repository).as_posix()
        for note in sorted(docs.rglob("*.md"))
        if note.is_file()
        and any(
            cite.search(group)
            for group in _CITATIONS.findall(note.read_text(encoding="utf-8"))
        )
    ]


def _collection(
    workspace: Workspace, name: str, library: zotero.Library
) -> tuple[str | None, str]:
    """The key of the repository's collection, or None if it has none; and its description."""
    repository = workspace.repository(name)
    if repository.zotero_collection:
        return repository.zotero_collection, repository.zotero_collection
    parent = workspace.zotero_root
    return library.collection([parent, name]), f"{parent}/{name}"


def _no_collection(described: str) -> str:
    return (
        f"no Zotero collection {described}: create it, or name another by its key "
        f"as zotero_collection in {manifest.FILENAME}"
    )


def pull(
    root: Path,
    workspace: Workspace,
    name: str,
    library: zotero.Library,
    required: bool = True,
) -> tuple[list[str], bool]:
    """Rewrite the `references.bib` of the repository `name` from its Zotero collection.

    A repository without a collection fails, unless not `required`: its bibliography
    is then left as it is. Raises `zotero.ZoteroError` if Zotero cannot be read.
    Returns the report lines and success.
    """
    collection, described = _collection(workspace, name, library)
    if collection is None and not required:
        return [
            (
                f"{name}: no Zotero collection {described}, "
                f"{resources.BIBLIOGRAPHY} left as it is"
            )
        ], True
    if collection is None:
        return [f"{name}: FAILED: {_no_collection(described)}"], False
    items = {}
    keyless = []
    for data in library.items(collection):
        if key := zotero.citekey(data):
            items[key] = data
        else:
            keyless.append(data)
    failures = []
    for data in keyless:
        key = library.unique_citekey(data, set(items))
        try:
            library.add(data, citationKey=key)
        except zotero.ReadOnly as error:
            # The entry is written all the same; the next pull makes the key again.
            if str(error) not in failures:
                failures.append(str(error))
        items[key] = data
    header = [
        f"Written by `ws refs pull` from the Zotero collection {described}.",
        "Add a reference with `ws refs add`, never here.",
    ]
    folder = root / name
    bibliography = folder / resources.BIBLIOGRAPHY
    before = (
        retrieve.entries(bibliography.read_text(encoding="utf-8"))
        if bibliography.is_file()
        else {}
    )
    bibliography.write_text(bibtex.bibliography(header, items), encoding="utf-8")
    count = f"{len(items)} entr{'y' if len(items) == 1 else 'ies'}"
    lines = [f"{name}: {resources.BIBLIOGRAPHY}: {count}"]
    removed = sorted(set(before) - set(items))
    if removed:
        lines.append(f"{name}: {resources.BIBLIOGRAPHY}: removed {', '.join(removed)}")
    for key in removed:
        if notes := _citing(folder, key):
            lines.append(
                f"{name}: WARNING: {key} is no longer in the collection, "
                f"but {', '.join(notes)} cites it"
            )
    lines += [f"{name}: FAILED: {failure}" for failure in failures]
    return lines, not failures


def add(
    root: Path,
    workspace: Workspace,
    name: str,
    identifier: lookup.Identifier,
    library: zotero.Library,
) -> tuple[list[str], bool]:
    """Add the reference `identifier` names to the Zotero collection of the repository
    `name`, and pull that repository.

    Raises `zotero.ZoteroError` if Zotero cannot be read or written.
    Returns the report lines and success.
    """
    collection, described = _collection(workspace, name, library)
    if collection is None:
        return [f"{name}: FAILED: {_no_collection(described)}"], False
    existing = [
        data
        for data in library.search(identifier.value)
        if lookup.names(identifier, data)
    ]
    if existing:
        # One item per reference in the library: it joins this collection as it is.
        data = existing[0]
        if collection not in data["collections"]:
            library.add(data, collections=[*data["collections"], collection])
        key = zotero.citekey(data) or library.unique_citekey(data, set())
        if not zotero.citekey(data):
            library.add(data, citationKey=key)
        lines = [f"{name}: added {key}, already in Zotero"]
    else:
        try:
            data = lookup.item(identifier, library.send)
        except lookup.LookupFailed as error:
            return [f"{name}: FAILED: {error}"], False
        key = library.unique_citekey(data, set())
        library.create({**data, "collections": [collection], "citationKey": key})
        lines = [f"{name}: added {key}"]
    pulled, ok = pull(root, workspace, name, library)
    return lines + pulled + [
        f"{name}: run `uv run ws fetch` in the hub to retrieve its PDF"
    ], ok
