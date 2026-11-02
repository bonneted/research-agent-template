"""`rkt refs`: an inquiry's `references.bib`, written from its Zotero collection."""

import re
from pathlib import Path

from rkt import bibtex, inquiry, lookup, resources, retrieve, zotero
from rkt.inquiry import Inquiry

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
    inquiry: Inquiry, library: zotero.Library
) -> tuple[str | None, str | None]:
    """The key of the inquiry's collection, or None if it has none; and its path, or None
    if `inquiry.yaml` names none.
    """
    if not inquiry.zotero_collection:
        return None, None
    names = [name for name in inquiry.zotero_collection.split("/") if name]
    return library.collection(names), "/".join(names)


def _no_collection(described: str | None) -> str:
    if described is None:
        return f"no zotero_collection in {inquiry.FILENAME}"
    return f"no Zotero collection {described}: create it, or correct zotero_collection"


def pull(
    inquiry: Inquiry,
    library: zotero.Library,
    required: bool = True,
) -> tuple[list[str], bool]:
    """Rewrite the inquiry's `references.bib` from its Zotero collection.

    An inquiry without a collection fails, unless not `required`: its bibliography
    is then left as it is. Raises `zotero.ZoteroError` if Zotero cannot be read.
    Returns the report lines and success.
    """
    name = inquiry.label
    collection, described = _collection(inquiry, library)
    if collection is None and not required:
        return [
            f"{name}: {_no_collection(described)}; {resources.BIBLIOGRAPHY} left as it is"
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
        f"Written by `rkt refs pull` from the Zotero collection {described}.",
        "Add a reference with `rkt refs add`, never here.",
    ]
    folder = inquiry.path
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


def _same(
    library: zotero.Library, identifier: lookup.Identifier, text: str
) -> list[dict]:
    """The items of the library holding `text` that `identifier` names."""
    return [data for data in library.search(text) if lookup.names(identifier, data)]


def add(
    inquiry: Inquiry,
    identifier: lookup.Identifier,
    library: zotero.Library,
) -> tuple[list[str], bool]:
    """Add the reference `identifier` names to the inquiry's Zotero collection, and pull.

    Raises `zotero.ZoteroError` if Zotero cannot be read or written.
    Returns the report lines and success.
    """
    name = inquiry.label
    collection, described = _collection(inquiry, library)
    if collection is None:
        return [f"{name}: FAILED: {_no_collection(described)}"], False
    existing = _same(library, identifier, identifier.value)
    found = None
    if not existing:
        # Zotero's search splits a DOI into words and seldom finds it whole: look the
        # reference up, and search the library again by its title.
        try:
            found = lookup.item(identifier, library.send)
        except lookup.LookupFailed as error:
            return [f"{name}: FAILED: {error}"], False
        if found.get("title"):
            existing = _same(library, identifier, found["title"])
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
        assert found is not None  # looked up above, since nothing was found by it
        data = found
        key = library.unique_citekey(data, set())
        library.create({**data, "collections": [collection], "citationKey": key})
        lines = [f"{name}: added {key}"]
    pulled, ok = pull(inquiry, library)
    return lines + pulled + [f"{name}: run `rkt fetch` to retrieve its PDF"], ok


BIB_ONLY_HEADER = [
    "Written by `rkt refs add` from Crossref, DataCite or arXiv: this inquiry has no",
    "Zotero collection. Add a reference with `rkt refs add`, never here.",
]


def _named(identifier: lookup.Identifier, entry: retrieve.Entry) -> bool:
    """Whether a bibliography entry is the reference `identifier` names."""
    value = identifier.value.lower()
    if identifier.kind == "arxiv":
        return (entry.arxiv or "").lower().split("v")[0] == value.split("v")[0]
    return (entry.doi or "").lower() == value


def add_to_bibliography(
    inquiry: Inquiry, identifier: lookup.Identifier, send: zotero.Send = zotero.send
) -> tuple[list[str], bool]:
    """Add the reference `identifier` names to the inquiry's `references.bib` itself, for
    an inquiry with no Zotero collection.

    Returns the report lines and success.
    """
    name = inquiry.label
    bibliography = inquiry.path / resources.BIBLIOGRAPHY
    text = bibliography.read_text(encoding="utf-8") if bibliography.is_file() else ""
    entries = retrieve.entries(text)
    for key, entry in entries.items():
        if _named(identifier, entry):
            return [f"{name}: {key} is already in {resources.BIBLIOGRAPHY}"], True
    try:
        data = lookup.item(identifier, send)
    except lookup.LookupFailed as error:
        return [f"{name}: FAILED: {error}"], False
    base = zotero.made_citekey(data)
    key = next(
        (
            base + suffix
            for suffix in ["", *"abcdefghijklmnopqrstuvwxyz"]
            if base + suffix not in entries
        ),
        None,
    )
    if key is None:
        return [f"{name}: FAILED: no free citekey from {base}"], False
    if not text.strip():
        text = "".join(f"% {line}\n" for line in BIB_ONLY_HEADER)
    bibliography.write_text(
        text.rstrip("\n") + "\n\n" + bibtex.entry(key, data), encoding="utf-8"
    )
    return [
        f"{name}: added {key}",
        f"{name}: run `rkt fetch` to retrieve its PDF",
    ], True
