"""The project's resource manifest: its bibliography, and its list of code and data.

The bibliography (`references.bib`, exported from Zotero) names the documents by citekey;
`resources.yaml` lists the code resources, each at a pinned commit, and the data
resources, each with its checksum. A project without them has no resources.
"""

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

BIBLIOGRAPHY = "references.bib"
FILENAME = "resources.yaml"

_COMMIT = re.compile(r"[0-9a-f]{7,40}")
_SHA256 = re.compile(r"[0-9a-f]{64}")
# A citekey or resource name becomes a file or folder of `resources/`, so it may not
# climb out of it or hide.
_PLAIN = re.compile(r"\w[\w.:+-]*")
# An entry opens a line; Better BibTeX writes its comment lines with `%`.
_ENTRY = re.compile(r"^\s*@\s*(\w+)\s*[{(]\s*([^\s,{}()]+)\s*,", re.MULTILINE)
_NOT_ENTRIES = {"comment", "preamble", "string"}
# A field on a line of its own, as Better BibTeX writes it; a wrapped value is not read.
_FIELD = re.compile(r"^\s*(\w+)\s*=\s*[{\"](.*?)[}\"]\s*,?\s*$", re.MULTILINE)
_ARXIV_DOI = re.compile(r"10\.48550/arxiv\.(.+)", re.IGNORECASE)
_ARXIV_URL = re.compile(r"arxiv\.org/(?:abs|pdf)/([^\s?#]+?)(?:\.pdf)?$")


class ManifestError(Exception):
    """A resource manifest is malformed."""


@dataclass(frozen=True)
class Entry:
    """A document of the bibliography, with what a source may look it up by."""

    citekey: str
    doi: str | None = None
    arxiv: str | None = None


@dataclass(frozen=True)
class Code:
    """A repository read for what it does, cloned at `resources/code/<name>`."""

    name: str
    url: str
    commit: str
    # The citekey of the document this repository is the source form of, such as a
    # thesis's LaTeX.
    source_of: str | None = None


@dataclass(frozen=True)
class Data:
    """A dataset, the file `resources/data/<name>`."""

    name: str
    source: str
    sha256: str


@dataclass(frozen=True)
class Resources:
    """The code and data a project lists."""

    code: list[Code]
    data: list[Data]


def is_plain(name: str) -> bool:
    """Whether `name` can name a file or folder of `resources/`."""
    return bool(_PLAIN.fullmatch(name))


def entries(text: str) -> dict[str, Entry]:
    """Each entry of a BibTeX bibliography, by citekey."""
    found = {}
    matches = [
        match
        for match in _ENTRY.finditer(text)
        if match.group(1).lower() not in _NOT_ENTRIES
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
        elif found_doi := _ARXIV_DOI.fullmatch(fields.get("doi", "")):
            arxiv = found_doi.group(1)
        elif found_url := _ARXIV_URL.search(fields.get("url", "")):
            arxiv = found_url.group(1)
        found[key] = Entry(key, fields.get("doi") or None, arxiv)
    return found


def bibliography(project: Path) -> dict[str, Entry]:
    """The documents the project at `project` lists, by citekey."""
    path = project / BIBLIOGRAPHY
    return entries(path.read_text(encoding="utf-8")) if path.is_file() else {}


def _entries(
    path: Path, data: dict[str, Any], section: str, fields: tuple[str, ...]
) -> list[dict[str, Any]]:
    """The entries of one section, each checked to name a plain file and give `fields` as text."""
    listed = data.get(section) or []
    if not isinstance(listed, list):
        raise ManifestError(f"{FILENAME}: expected '{section}' to be a list")
    for index, entry in enumerate(listed):
        if not isinstance(entry, dict) or any(
            entry.get(field) is None for field in fields
        ):
            raise ManifestError(
                f"{FILENAME}: {section} resource {index} needs {', '.join(fields)}"
            )
        for field in fields:
            # YAML reads a hash made only of digits as a number, dropping leading zeros.
            if not isinstance(entry[field], str):
                raise ManifestError(
                    f"{FILENAME}: {section} resource {index} has a {field} that YAML "
                    "reads as a number: write it in quotes"
                )
        if not is_plain(entry["name"]):
            raise ManifestError(
                f"{FILENAME}: {section} resource name {entry['name']!r} is not a plain file name"
            )
    return listed


def load(project: Path) -> Resources:
    """The code and data listed by the project at `project`."""
    path = project / FILENAME
    if not path.is_file():
        return Resources([], [])
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as error:
        raise ManifestError(f"{FILENAME}: {error}") from error
    if not isinstance(data, dict):
        raise ManifestError(f"{FILENAME}: expected 'code' and 'data' lists")
    code = []
    for entry in _entries(path, data, "code", ("name", "url", "commit")):
        # A branch or tag would move under the pin: only a commit keeps it.
        if not _COMMIT.fullmatch(entry["commit"]):
            raise ManifestError(
                f"{FILENAME}: code resource {entry['name']} is pinned at "
                f"{entry['commit']!r}, not a commit hash"
            )
        source_of = entry.get("source_of")
        if source_of is not None and not isinstance(source_of, str):
            raise ManifestError(
                f"{FILENAME}: code resource {entry['name']} has a source_of that is not a citekey"
            )
        code.append(Code(entry["name"], entry["url"], entry["commit"], source_of))
    data_resources = []
    for entry in _entries(path, data, "data", ("name", "source", "sha256")):
        sha256 = entry["sha256"].lower()
        if not _SHA256.fullmatch(sha256):
            raise ManifestError(
                f"{FILENAME}: data resource {entry['name']} has a sha256 that is not 64 hex digits"
            )
        data_resources.append(Data(entry["name"], entry["source"], sha256))
    return Resources(code, data_resources)
