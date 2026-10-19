"""`refs`: the project's `references.bib`, written from its Zotero collection.

`refs pull` rewrites `references.bib` from the collection that `resources.yaml` names as
`zotero_collection`. `refs add <DOI | arXiv identifier | URL>` adds a reference to that
collection, with metadata looked up by its identifier (never written by hand or by an
agent), and pulls. Without a Zotero configuration, `add` writes the entry into
`references.bib` itself, from the same lookup.
"""

import argparse
import re
from pathlib import Path

from fetch import bibtex, lookup, manifest, zotero

# A Pandoc citation group, such as `[@a; @b, p. 3]`.
_CITATIONS = re.compile(r"\[[^\[\]]*@[^\[\]]*\]")
# A Zotero object key; any other `zotero_collection` is a path of names.
_KEY = re.compile(r"[A-Z0-9]{8}")
HEADER = [
    "Written by `uv run refs pull` from the Zotero collection {collection}.",
    "Add a reference with `uv run refs add`, or in Zotero, never here.",
]


class NoCollection(Exception):
    """The project names no Zotero collection, or the library does not have it."""


def _citing(project: Path, key: str) -> list[str]:
    """The notes in the project's `docs/` that cite `key`."""
    cite = re.compile(rf"@{re.escape(key)}(?![\w-])")
    docs = project / "docs"
    return [
        note.relative_to(project).as_posix()
        for note in sorted(docs.rglob("*.md"))
        if note.is_file()
        and any(
            cite.search(group)
            for group in _CITATIONS.findall(note.read_text(encoding="utf-8"))
        )
    ]


def _collection(project: Path, library: zotero.Library) -> tuple[str, str]:
    """The key of the project's collection, and its description.

    Raises `NoCollection` if the project names none or the library does not have it,
    and `manifest.ManifestError` if `resources.yaml` is malformed.
    """
    named = manifest.load(project).zotero_collection
    if named is None:
        raise NoCollection(
            f"name the project's Zotero collection as zotero_collection in "
            f"{manifest.FILENAME}"
        )
    if _KEY.fullmatch(named):
        return named, named
    key = library.collection([name.strip() for name in named.split("/")])
    if key is None:
        raise NoCollection(
            f"no Zotero collection {named}: create it, or correct zotero_collection "
            f"in {manifest.FILENAME}"
        )
    return key, named


def pull(project: Path, library: zotero.Library) -> tuple[list[str], bool]:
    """Rewrite the project's `references.bib` from its Zotero collection.

    Raises `NoCollection` and `manifest.ManifestError` as `_collection` does, and
    `zotero.ZoteroError` if Zotero cannot be read. Returns the report lines and success.
    """
    collection, described = _collection(project, library)
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
    header = [line.format(collection=described) for line in HEADER]
    bibliography = project / manifest.BIBLIOGRAPHY
    before = manifest.bibliography(project)
    bibliography.write_text(bibtex.bibliography(header, items), encoding="utf-8")
    count = f"{len(items)} entr{'y' if len(items) == 1 else 'ies'}"
    lines = [f"{manifest.BIBLIOGRAPHY}: {count} from Zotero"]
    removed = sorted(set(before) - set(items))
    if removed:
        lines.append(f"{manifest.BIBLIOGRAPHY}: removed {', '.join(removed)}")
    for key in removed:
        if notes := _citing(project, key):
            lines.append(
                f"WARNING: {key} is no longer in the collection, "
                f"but {', '.join(notes)} cites it"
            )
    lines += [f"FAILED: {failure}" for failure in failures]
    return lines, not failures


def add(
    project: Path, identifier: lookup.Identifier, library: zotero.Library
) -> tuple[list[str], bool]:
    """Add the reference `identifier` names to the project's Zotero collection, and pull.

    Raises as `pull` does, and `zotero.ZoteroError` if Zotero cannot be written.
    Returns the report lines and success.
    """
    collection, _ = _collection(project, library)
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
        lines = [f"added {key}, already in Zotero"]
    else:
        try:
            data = lookup.item(identifier, library.send)
        except lookup.LookupFailed as error:
            return [f"FAILED: {error}"], False
        key = library.unique_citekey(data, set())
        library.create({**data, "collections": [collection], "citationKey": key})
        lines = [f"added {key}"]
    pulled, ok = pull(project, library)
    return lines + pulled + ["run `uv run fetch` to retrieve its PDF"], ok


def add_without_zotero(
    project: Path, identifier: lookup.Identifier, send: zotero.Send = zotero.send
) -> tuple[list[str], bool]:
    """Add the reference `identifier` names to `references.bib` itself, for a project
    without Zotero. Returns the report lines and success.
    """
    documents = manifest.bibliography(project)
    for key, entry in documents.items():
        if (
            identifier.kind == "doi" and (entry.doi or "").lower() == identifier.value
        ) or (identifier.kind == "arxiv" and entry.arxiv == identifier.value):
            return [f"{key} is already in {manifest.BIBLIOGRAPHY}"], True
    try:
        data = lookup.item(identifier, send)
    except lookup.LookupFailed as error:
        return [f"FAILED: {error}"], False
    base = zotero.made_citekey(data)
    key = next(
        base + suffix
        for suffix in ["", *"abcdefghijklmnopqrstuvwxyz"]
        if base + suffix not in documents
    )
    bibliography = project / manifest.BIBLIOGRAPHY
    text = bibliography.read_text(encoding="utf-8") if bibliography.is_file() else ""
    if text and not text.endswith("\n"):
        text += "\n"
    bibliography.write_text(text + "\n" + bibtex.entry(key, data), encoding="utf-8")
    return [
        f"added {key} to {manifest.BIBLIOGRAPHY} (no Zotero configuration)",
        "run `uv run fetch` to retrieve its PDF",
    ], True


def main(argv: list[str] | None = None) -> int:
    """Run `refs` on the project holding the current folder; returns the exit code."""
    parser = argparse.ArgumentParser(
        prog="refs",
        description="The project's references.bib, written from its Zotero collection.",
    )
    actions = parser.add_subparsers(dest="action", required=True)
    actions.add_parser(
        "pull", help="rewrite references.bib from the project's Zotero collection"
    )
    adder = actions.add_parser(
        "add",
        help="add a reference from its DOI, arXiv identifier, or doi.org or arxiv.org "
        "URL to the Zotero collection, and pull",
    )
    adder.add_argument("identifier", help="a DOI, an arXiv identifier, or a URL to one")
    arguments = parser.parse_args(argv)
    project = manifest.project(Path.cwd())
    lines, ok = _run(project, arguments)
    print("\n".join(lines))
    return 0 if ok else 1


def _run(project: Path, arguments: argparse.Namespace) -> tuple[list[str], bool]:
    if arguments.action == "add":
        try:
            identifier = lookup.identify(arguments.identifier)
        except lookup.Refused as error:
            return [f"FAILED: {error}"], False
    library, reason = zotero.configured()
    try:
        if library is None:
            if arguments.action == "add" and reason.startswith(
                "no Zotero configuration"
            ):
                return add_without_zotero(project, identifier)
            return [f"FAILED: {reason}"], False
        if arguments.action == "add":
            return add(project, identifier, library)
        return pull(project, library)
    except (NoCollection, manifest.ManifestError, zotero.ZoteroError) as error:
        return [f"FAILED: {error}"], False
