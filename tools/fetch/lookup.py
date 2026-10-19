"""A reference's metadata, looked up by its identifier, as a Zotero item.

A DOI is asked of Crossref, and of DataCite when Crossref does not know it; an arXiv
identifier, of the arXiv API. The metadata always comes from them, never from whoever
asks `refs` to add the reference.
"""

import html
import json
import re
import urllib.parse
from dataclasses import dataclass
from xml.etree import ElementTree

from fetch import zotero

_DOI = re.compile(r"(?:doi:\s*)?(10\.\d{4,9}/\S+)", re.IGNORECASE)
_DOI_URL = re.compile(r"https?://(?:dx\.)?doi\.org/(10\.\d{4,9}/\S+)", re.IGNORECASE)
_ARXIV_ID = r"(\d{4}\.\d{4,5}|[a-z-]+(?:\.[A-Z]{2})?/\d{7})(?:v\d+)?"
_ARXIV = re.compile(rf"(?:arxiv:\s*)?{_ARXIV_ID}", re.IGNORECASE)
_ARXIV_URL = re.compile(
    rf"https?://(?:www\.|export\.)?arxiv\.org/(?:abs|pdf)/{_ARXIV_ID}(?:\.pdf)?/?",
    re.IGNORECASE,
)
_ARXIV_DOI = re.compile(r"10\.48550/arxiv\.(.+)", re.IGNORECASE)

# Crossref's work types, as Zotero item types, with the field their container goes in.
_CROSSREF_TYPES = {
    "journal-article": ("journalArticle", "publicationTitle"),
    "proceedings-article": ("conferencePaper", "proceedingsTitle"),
    "book-chapter": ("bookSection", "bookTitle"),
    "book-part": ("bookSection", "bookTitle"),
    "book": ("book", None),
    "monograph": ("book", None),
    "edited-book": ("book", None),
    "posted-content": ("preprint", "repository"),
    "report": ("report", None),
    "dissertation": ("thesis", None),
}

# DataCite's resource types, as Zotero item types.
_DATACITE_TYPES = {
    "JournalArticle": "journalArticle",
    "ConferencePaper": "conferencePaper",
    "BookChapter": "bookSection",
    "Book": "book",
    "Dissertation": "thesis",
    "Report": "report",
    "Preprint": "preprint",
    "Dataset": "dataset",
    "Software": "computerProgram",
}

# Where each item type keeps its publisher, when it has one (Zotero's base field mapping).
_PUBLISHER = {
    "book": "publisher",
    "bookSection": "publisher",
    "conferencePaper": "publisher",
    "thesis": "university",
    "report": "institution",
    "dataset": "repository",
    "computerProgram": "company",
    "document": "publisher",
}


class Refused(Exception):
    """The text is no identifier `refs` can look up."""


class LookupFailed(Exception):
    """The identifier could not be looked up."""


@dataclass(frozen=True)
class Identifier:
    """A DOI (lowercased) or an arXiv identifier (without its version)."""

    kind: str
    value: str

    def __str__(self) -> str:
        return f"arXiv:{self.value}" if self.kind == "arxiv" else self.value


def identify(text: str) -> Identifier:
    """The identifier `text` is or links to; raises `Refused` for anything else."""
    text = text.strip()
    for pattern, kind in (
        (_DOI_URL, "doi"),
        (_ARXIV_URL, "arxiv"),
        (_DOI, "doi"),
        (_ARXIV, "arxiv"),
    ):
        if match := pattern.fullmatch(text):
            value = urllib.parse.unquote(match.group(1))
            if kind == "doi" and (arxiv := _ARXIV_DOI.fullmatch(value)):
                return identify(arxiv.group(1))
            return Identifier(kind, value.lower() if kind == "doi" else value)
    raise Refused(
        f"{text!r} is not a DOI, an arXiv identifier, or a doi.org or arxiv.org URL: "
        "add a thesis, report or slides by hand in Zotero"
    )


def names(identifier: Identifier, data: dict) -> bool:
    """Whether the Zotero item `data` is the one `identifier` names, by that exact identifier."""
    doi = (data.get("DOI") or "").strip().lower()
    if identifier.kind == "doi":
        return doi == identifier.value
    arxiv = re.escape(identifier.value.lower())
    version = r"(?:v\d+)?"
    extra = [line.strip().lower() for line in (data.get("extra") or "").splitlines()]
    return bool(
        doi == f"10.48550/arxiv.{identifier.value.lower()}"
        or re.fullmatch(
            rf"arxiv:\s*{arxiv}{version}", (data.get("archiveID") or "").lower()
        )
        or re.search(
            rf"arxiv\.org/(?:abs|pdf)/{arxiv}{version}(?:\.pdf)?/?$",
            (data.get("url") or "").lower(),
        )
        or any(re.fullmatch(rf"arxiv:\s*{arxiv}{version}", line) for line in extra)
    )


def _get(send: zotero.Send, url: str) -> bytes | None:
    """The body at `url`, or None if there is nothing there."""
    try:
        response = send("GET", url, {"Accept": "application/json"}, None)
    except OSError as error:
        raise LookupFailed(f"{url}: {error}") from error
    if response.status == 404:
        return None
    if response.status >= 400:
        raise LookupFailed(f"{url} answered {response.status}")
    return response.body


def _text(markup: str) -> str:
    """Plain text from an abstract's JATS or HTML markup."""
    return " ".join(html.unescape(re.sub(r"<[^>]+>", " ", markup)).split())


def _crossref(doi: str, send: zotero.Send) -> dict | None:
    body = _get(
        send, f"https://api.crossref.org/works/{urllib.parse.quote(doi, safe='/')}"
    )
    if body is None:
        return None
    work = json.loads(body)["message"]
    kind, container = _CROSSREF_TYPES.get(
        work.get("type", ""), ("journalArticle", "publicationTitle")
    )
    parts = (work.get("published") or work.get("issued") or {}).get("date-parts") or [
        []
    ]
    data = {
        "itemType": kind,
        "title": " ".join((work.get("title") or [""])[0].split()),
        "creators": [
            {
                "creatorType": role,
                "firstName": person.get("given", ""),
                "lastName": person["family"],
            }
            if person.get("family")
            else {"creatorType": role, "name": person.get("name", "")}
            for role, field in (("author", "author"), ("editor", "editor"))
            for person in work.get(field, [])
        ],
        "date": "-".join(f"{part:02d}" for part in parts[0] if part),
        "DOI": work.get("DOI", doi),
        "url": work.get("URL", f"https://doi.org/{doi}"),
        "abstractNote": _text(work.get("abstract", "")),
    }
    if container and work.get("container-title"):
        data[container] = work["container-title"][0]
    for name, field in (("volume", "volume"), ("issue", "issue"), ("pages", "page")):
        if work.get(field) and kind in (
            "journalArticle",
            "conferencePaper",
            "bookSection",
        ):
            data[name] = work[field]
    if work.get("ISSN") and kind == "journalArticle":
        data["ISSN"] = work["ISSN"][0]
    if work.get("ISBN") and kind in ("book", "bookSection"):
        data["ISBN"] = work["ISBN"][0]
    if work.get("publisher") and kind in _PUBLISHER:
        data[_PUBLISHER[kind]] = work["publisher"]
    return {name: value for name, value in data.items() if value}


def _datacite(doi: str, send: zotero.Send) -> dict | None:
    body = _get(
        send, f"https://api.datacite.org/dois/{urllib.parse.quote(doi, safe='/')}"
    )
    if body is None:
        return None
    record = json.loads(body)["data"]["attributes"]
    kind = _DATACITE_TYPES.get(
        (record.get("types") or {}).get("resourceTypeGeneral", ""), "document"
    )
    abstracts = [
        description["description"]
        for description in record.get("descriptions") or []
        if description.get("descriptionType") == "Abstract"
    ]
    data = {
        "itemType": kind,
        "title": " ".join(
            ((record.get("titles") or [{}])[0].get("title") or "").split()
        ),
        "creators": [
            {
                "creatorType": "author",
                "firstName": person.get("givenName", ""),
                "lastName": person["familyName"],
            }
            if person.get("familyName")
            else {"creatorType": "author", "name": person.get("name", "")}
            for person in record.get("creators") or []
        ],
        "date": str(record.get("publicationYear") or ""),
        "DOI": record.get("doi", doi),
        "url": record.get("url") or f"https://doi.org/{doi}",
        "abstractNote": _text(abstracts[0]) if abstracts else "",
    }
    # DataCite gives the publisher as a name, or as an object with one.
    publisher = record.get("publisher")
    if isinstance(publisher, dict):
        publisher = publisher.get("name")
    if publisher and kind in _PUBLISHER:
        data[_PUBLISHER[kind]] = publisher
    return {name: value for name, value in data.items() if value}


_ATOM = {"atom": "http://www.w3.org/2005/Atom"}


def _arxiv(identifier: str, send: zotero.Send) -> dict | None:
    query = urllib.parse.urlencode({"id_list": identifier})
    body = _get(send, f"https://export.arxiv.org/api/query?{query}")
    if body is None:
        return None
    try:
        entry = ElementTree.fromstring(body).find("atom:entry", _ATOM)
    except ElementTree.ParseError as error:
        raise LookupFailed(f"arXiv answered {identifier} with no feed") from error
    # The API answers an identifier it does not know with an empty feed, or an error entry.
    if entry is None or entry.findtext("atom:id", "", _ATOM).endswith("/api/errors"):
        return None

    def text(name: str) -> str:
        return " ".join(entry.findtext(f"atom:{name}", "", _ATOM).split())

    creators = []
    for author in entry.findall("atom:author", _ATOM):
        # As Zotero's arXiv translator does: the last word is the last name.
        first, _, last = " ".join(
            author.findtext("atom:name", "", _ATOM).split()
        ).rpartition(" ")
        creators.append({"creatorType": "author", "firstName": first, "lastName": last})
    data = {
        "itemType": "preprint",
        "title": text("title"),
        "creators": creators,
        "abstractNote": text("summary"),
        "date": text("published")[:10],
        "repository": "arXiv",
        "archiveID": f"arXiv:{identifier}",
        "DOI": f"10.48550/arXiv.{identifier}",
        "url": f"https://arxiv.org/abs/{identifier}",
    }
    return {name: value for name, value in data.items() if value}


def item(identifier: Identifier, send: zotero.Send) -> dict:
    """The Zotero item data of what `identifier` names.

    Raises `LookupFailed` if no service knows it or none could be asked.
    """
    if identifier.kind == "arxiv":
        data = _arxiv(identifier.value, send)
    else:
        data = _crossref(identifier.value, send) or _datacite(identifier.value, send)
    if data is None:
        raise LookupFailed(f"no metadata for {identifier}")
    return data
