"""Zotero items as a BibTeX bibliography, in one fixed form.

Entries are sorted by citekey and their fields come in a fixed order, each on a line
of its own, so that a pull changes only the lines whose item changed in Zotero.
"""

import re

_TYPES = {
    "journalArticle": "article",
    "magazineArticle": "article",
    "newspaperArticle": "article",
    "conferencePaper": "inproceedings",
    "bookSection": "incollection",
    "book": "book",
    "thesis": "phdthesis",
    "report": "techreport",
}
_MONTHS = (
    "jan",
    "feb",
    "mar",
    "apr",
    "may",
    "jun",
    "jul",
    "aug",
    "sep",
    "oct",
    "nov",
    "dec",
)
_SPECIAL = re.compile(r"(?<!\\)([&%$#_])")


def _people(data: dict, role: str) -> str | None:
    names = []
    for creator in data.get("creators", []):
        if creator.get("creatorType") != role:
            continue
        if creator.get("name"):
            names.append(f"{{{creator['name']}}}")
        else:
            first, last = creator.get("firstName", ""), creator.get("lastName", "")
            names.append(f"{last}, {first}" if first else last)
    return " and ".join(names) or None


def _date(text: str) -> tuple[str | None, str | None]:
    """The year and month of a Zotero date, as its user typed it."""
    year = re.search(r"\b(\d{4})\b", text)
    month = re.search(r"\b\d{4}-(\d{2})\b", text)
    if month and 1 <= int(month.group(1)) <= 12:
        return year.group(1), _MONTHS[int(month.group(1)) - 1]
    for index, name in enumerate(_MONTHS):
        if re.search(rf"\b{name}", text, re.IGNORECASE):
            return year and year.group(1), name
    return year and year.group(1), None


def fields(data: dict) -> list[tuple[str, str]]:
    """The fields of an item's entry, in their fixed order."""
    kind = data.get("itemType")
    year, month = _date(data.get("date", ""))
    pages = data.get("pages", "")
    archive, _, eprint = data.get("archiveID", "").partition(":")
    found = [
        # Software credits its programmers, which BibTeX has no field for but author.
        ("author", _people(data, "author") or _people(data, "programmer")),
        ("editor", _people(data, "editor")),
        ("title", data.get("title")),
        (
            "journal",
            data.get("publicationTitle") if kind != "conferencePaper" else None,
        ),
        ("booktitle", data.get("proceedingsTitle") or data.get("bookTitle")),
        ("school", data.get("university")),
        ("institution", data.get("institution")),
        (
            "publisher",
            data.get("publisher")
            or data.get("company")
            or (data.get("repository") if kind == "dataset" else None),
        ),
        ("year", year),
        ("month", month),
        ("volume", data.get("volume")),
        ("number", data.get("issue") or data.get("reportNumber")),
        ("pages", re.sub(r"\s*-+\s*", "--", pages) if pages else None),
        ("doi", data.get("DOI")),
        ("eprint", eprint if archive.lower() == "arxiv" else None),
        ("archiveprefix", "arXiv" if archive.lower() == "arxiv" and eprint else None),
        ("isbn", data.get("ISBN")),
        ("issn", data.get("ISSN")),
        ("url", data.get("url")),
        ("abstract", data.get("abstractNote")),
    ]
    return [(name, value) for name, value in found if value]


def _value(name: str, value: str) -> str:
    value = " ".join(value.split())
    return value if name in ("url", "doi") else _SPECIAL.sub(r"\\\1", value)


def entry(key: str, data: dict) -> str:
    """One item's entry under `key`."""
    kind = _TYPES.get(data.get("itemType", ""), "misc")
    lines = [f"@{kind}{{{key},"]
    lines += [f"  {name} = {{{_value(name, value)}}}," for name, value in fields(data)]
    return "\n".join(lines + ["}"]) + "\n"


def bibliography(header: list[str], items: dict[str, dict]) -> str:
    """The bibliography of `items` (data by citekey), under comment lines `header`."""
    text = "".join(f"% {line}\n" for line in header)
    return text + "".join("\n" + entry(key, items[key]) for key in sorted(items))
