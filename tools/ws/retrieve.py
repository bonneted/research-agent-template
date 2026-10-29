"""Retrieval of a document's PDF from the web, for `ws fetch`.

Each source answers one question: given a bibliography entry, here are its PDF's bytes,
or None. The sources are tried in order: a local folder of PDFs named by citekey (such
as the one ZotMoov keeps in sync), then the Zotero Web API, when the user configured
them, then arXiv, then Unpaywall by DOI. Their configuration is the user's
`$XDG_CONFIG_HOME/research-ws/retrieval.yaml` (by default `~/.config/research-ws/`),
never in git. Its top-level keys serve every workspace; a workspace's section under
`workspaces` adds to them or overrides them:

    pdf_folder: /mnt/c/Users/me/OneDrive/Zotero   # holds <citekey>.pdf
    email: you@example.org       # Unpaywall asks for one; without it, it is skipped
    workspaces:
      copv:
        zotero:
          library: groups/1234567    # or users/<id>
          api_key: <a key with write access to the library and its files>
        upload_pdfs: true        # attach PDFs found elsewhere in Zotero (see `zotero`)
"""

import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

import yaml

from ws import resources

CONFIG = Path("research-ws") / "retrieval.yaml"
# The section of the configuration holding each workspace's own keys.
WORKSPACES = "workspaces"

# Fetches a URL with the given headers; returns the body, or raises `OSError`.
Get = Callable[[str, dict[str, str]], bytes]

# A field on a line of its own, as Better BibTeX writes it; a wrapped value is not read.
_FIELD = re.compile(r"^\s*(\w+)\s*=\s*[{\"](.*?)[}\"]\s*,?\s*$", re.MULTILINE)
_ARXIV_DOI = re.compile(r"10\.48550/arxiv\.(.+)", re.IGNORECASE)
_ARXIV_URL = re.compile(r"arxiv\.org/(?:abs|pdf)/([^\s?#]+?)(?:\.pdf)?$")


class RetrievalError(Exception):
    """A source failed to answer: the network, its API or its configuration."""


@dataclass(frozen=True)
class Entry:
    """What a source may look a document up by."""

    citekey: str
    doi: str | None = None
    arxiv: str | None = None


class Retriever(Protocol):
    """A source of PDFs."""

    name: str

    def retrieve(self, entry: Entry) -> bytes | None:
        """The PDF of `entry`, or None if this source does not have it.

        Raises `RetrievalError` if the source could not be asked.
        """


def entries(text: str) -> dict[str, Entry]:
    """The identifiers of each entry of a BibTeX bibliography, by citekey."""
    found = {}
    matches = [
        match
        for match in resources.ENTRY.finditer(text)
        if match.group(1).lower() not in resources.NOT_ENTRIES
    ]
    # Each entry's fields run from its key to the next entry.
    ends = [match.start() for match in matches[1:]] + [len(text)]
    for match, end in zip(matches, ends):
        key = match.group(2)
        fields = {
            name.lower(): value.strip()
            for name, value in _FIELD.findall(text[match.end() : end])
        }
        arxiv = None
        if fields.get("archiveprefix", "").lower() == "arxiv" and fields.get("eprint"):
            arxiv = fields["eprint"]
        elif (match := _ARXIV_DOI.fullmatch(fields.get("doi", ""))) or (match := _ARXIV_URL.search(fields.get("url", ""))):
            arxiv = match.group(1)
        found[key] = Entry(key, fields.get("doi") or None, arxiv)
    return found


def _is_pdf(body: bytes) -> bool:
    return body.startswith(b"%PDF")


def _get(url: str, headers: dict[str, str]) -> bytes:
    request = urllib.request.Request(
        url, headers={"User-Agent": "research-ws (ws fetch)", **headers}
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read()


def _ask(get: Get, url: str, headers: dict[str, str] | None = None) -> bytes | None:
    """The body at `url`, None if it is not there, or `RetrievalError` if it cannot be asked."""
    try:
        return get(url, headers or {})
    except urllib.error.HTTPError as error:
        if error.code == 404:
            return None
        raise RetrievalError(f"{url}: {error}") from error
    except OSError as error:
        raise RetrievalError(f"{url}: {error}") from error


@dataclass
class Folder:
    """The PDF named `<citekey>.pdf` in a local folder, such as the one ZotMoov fills."""

    path: Path
    name: str = "PDF folder"

    def retrieve(self, entry: Entry) -> bytes | None:
        file = self.path / f"{entry.citekey}.pdf"
        try:
            body = file.read_bytes()
        except FileNotFoundError:
            return None
        except OSError as error:
            raise RetrievalError(f"{file}: {error}") from error
        return body if _is_pdf(body) else None


@dataclass
class Zotero:
    """The PDF attached to the item with the citekey in a Zotero library, by its Web API."""

    library: str
    api_key: str
    get: Get = _get
    name: str = "Zotero"

    def _ask(self, path: str) -> bytes | None:
        return _ask(
            self.get,
            f"https://api.zotero.org/{self.library}/{path}",
            {"Zotero-API-Key": self.api_key, "Zotero-API-Version": "3"},
        )

    def _file(self, key: str) -> bytes | None:
        """An attachment's file; None if it cannot be had, so the next one is tried."""
        try:
            return self._ask(f"items/{key}/file")
        except RetrievalError:
            return None

    def _json(self, path: str) -> list[dict]:
        body = self._ask(path)
        try:
            return json.loads(body) if body else []
        except ValueError as error:
            raise RetrievalError(f"Zotero answered {path} with no JSON") from error

    def retrieve(self, entry: Entry) -> bytes | None:
        query = urllib.parse.quote(entry.citekey)
        # Zotero 7 keeps the citekey in its own field; Better BibTeX before it, in Extra.
        items = [
            item
            for item in self._json(f"items?q={query}&qmode=everything&format=json")
            if item.get("data", {}).get("citationKey") == entry.citekey
            or f"Citation Key: {entry.citekey}"
            in item.get("data", {}).get("extra", "").splitlines()
        ]
        for item in items:
            for child in self._json(f"items/{item['key']}/children?format=json"):
                if child.get("data", {}).get("contentType") == "application/pdf":
                    body = self._file(child["key"])
                    if body and _is_pdf(body):
                        return body
        return None


@dataclass
class Arxiv:
    """The PDF of a preprint, by its arXiv identifier."""

    get: Get = _get
    name: str = "arXiv"

    def retrieve(self, entry: Entry) -> bytes | None:
        if entry.arxiv is None:
            return None
        body = _ask(self.get, f"https://arxiv.org/pdf/{entry.arxiv}")
        return body if body and _is_pdf(body) else None


@dataclass
class Unpaywall:
    """The open-access PDF Unpaywall knows of, by DOI."""

    email: str
    get: Get = _get
    name: str = "Unpaywall"

    def retrieve(self, entry: Entry) -> bytes | None:
        if entry.doi is None:
            return None
        doi = urllib.parse.quote(entry.doi, safe="/")
        email = urllib.parse.quote(self.email)
        body = _ask(self.get, f"https://api.unpaywall.org/v2/{doi}?email={email}")
        if not body:
            return None
        try:
            record = json.loads(body)
        except ValueError as error:
            raise RetrievalError(f"Unpaywall answered {entry.doi} with no JSON") from error
        locations = [record.get("best_oa_location")] + (record.get("oa_locations") or [])
        for url in dict.fromkeys(
            location.get("url_for_pdf") for location in locations if location
        ):
            if url:
                # A publisher refusing one copy leaves the others to try.
                try:
                    pdf = _ask(self.get, url)
                except RetrievalError:
                    continue
                if pdf and _is_pdf(pdf):
                    return pdf
        return None


def settings(workspace: str | None = None) -> tuple[dict, list[str], Path]:
    """The user's configuration for `workspace`, what is wrong with it, and its path."""
    home = Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config")
    path = home / CONFIG
    config: dict = {}
    problems = []
    if path.is_file():
        try:
            config = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        except yaml.YAMLError as error:
            problems.append(f"{path}: {error}")
        if not isinstance(config, dict):
            problems.append(f"{path}: expected a mapping")
            config = {}
    sections = config.pop(WORKSPACES, None) or {}
    if not isinstance(sections, dict):
        problems.append(f"{path}: expected '{WORKSPACES}' to map names to settings")
        sections = {}
    own = sections.get(workspace) if workspace else None
    if own is not None and not isinstance(own, dict):
        problems.append(f"{path}: expected '{WORKSPACES}.{workspace}' to be a mapping")
        own = None
    return {**config, **(own or {})}, problems, path


def configured(
    get: Get = _get, workspace: str | None = None
) -> tuple[list[Retriever], list[str]]:
    """The sources the user's configuration for `workspace` allows, in order; and what
    is wrong with it.
    """
    config, problems, path = settings(workspace)
    sources: list[Retriever] = []
    folder = config.get("pdf_folder")
    if folder is not None:
        path = Path(str(folder)).expanduser()
        if path.is_dir():
            sources.append(Folder(path))
        else:
            problems.append(f"{path}: pdf_folder is not a folder")
    zotero = config.get("zotero")
    if zotero is not None:
        if (
            isinstance(zotero, dict)
            and isinstance(zotero.get("library"), str)
            and isinstance(zotero.get("api_key"), str)
        ):
            sources.append(Zotero(zotero["library"].strip("/"), zotero["api_key"], get))
        else:
            problems.append(f"{path}: zotero needs a library and an api_key")
    sources.append(Arxiv(get))
    email = config.get("email")
    if email:
        sources.append(Unpaywall(str(email), get))
    return sources, problems


def retrieve(
    entry: Entry, sources: Sequence[Retriever]
) -> tuple[bytes | None, str | None, list[str]]:
    """The PDF of `entry` and the name of the first source that has it; and each
    source's failure.
    """
    failures = []
    for source in sources:
        try:
            pdf = source.retrieve(entry)
        except RetrievalError as error:
            failures.append(f"{source.name}: {error}")
            continue
        if pdf is not None:
            return pdf, source.name, failures
    return None, None, failures
