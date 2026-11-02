"""A repository's resource manifest: its bibliography, and its list of code and data.

The bibliography (`references.bib`, exported from Zotero) names the documents by citekey;
`resources.yaml` lists the code resources, each at a pinned commit, and the data
resources, each with its checksum. A repository without them has no resources.
"""

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from ws import pool

BIBLIOGRAPHY = "references.bib"
FILENAME = "resources.yaml"

_COMMIT = re.compile(r"[0-9a-f]{7,40}")
_SHA256 = re.compile(r"[0-9a-f]{64}")
# An entry opens a line; Better BibTeX writes its comment lines with `%`.
ENTRY = re.compile(r"^\s*@\s*(\w+)\s*[{(]\s*([^\s,{}()]+)\s*,", re.MULTILINE)
NOT_ENTRIES = {"comment", "preamble", "string"}


class ResourceError(Exception):
    """A resource manifest is malformed."""


@dataclass(frozen=True)
class Code:
    """A repository read for what it does, cloned at `code/<name>` in the pool."""

    name: str
    url: str
    commit: str
    # The citekey of the document this repository is the source form of, such as a
    # thesis's LaTeX.
    source_of: str | None = None
    # The citekeys of the documents whose methods this repository implements: read as
    # code, beside those documents.
    code_of: tuple[str, ...] = ()


@dataclass(frozen=True)
class Data:
    """A dataset, the file `data/<name>` in the pool."""

    name: str
    source: str
    sha256: str


@dataclass(frozen=True)
class Resources:
    """The code and data one repository lists."""

    code: list[Code]
    data: list[Data]


def _entries(
    path: Path, data: dict[str, Any], section: str, fields: tuple[str, ...]
) -> list[dict[str, Any]]:
    """The entries of one section, each checked to name a plain file and give `fields` as text."""
    entries = data.get(section) or []
    if not isinstance(entries, list):
        raise ResourceError(f"{path}: expected '{section}' to be a list")
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict) or any(
            entry.get(field) is None for field in fields
        ):
            raise ResourceError(
                f"{path}: {section} resource {index} needs {', '.join(fields)}"
            )
        for field in fields:
            # YAML reads a hash made only of digits as a number, dropping leading zeros.
            if not isinstance(entry[field], str):
                raise ResourceError(
                    f"{path}: {section} resource {index} has a {field} that YAML reads "
                    "as a number: write it in quotes"
                )
        if not pool.is_plain(entry["name"]):
            raise ResourceError(
                f"{path}: {section} resource name {entry['name']!r} is not a plain file name"
            )
    return entries


def load(repository: Path) -> Resources:
    """The code and data listed by the repository at `repository`."""
    path = repository / FILENAME
    if not path.is_file():
        return Resources([], [])
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as error:
        raise ResourceError(f"{path}: {error}") from error
    if not isinstance(data, dict):
        raise ResourceError(f"{path}: expected 'code' and 'data' lists")
    code = []
    for entry in _entries(path, data, "code", ("name", "url", "commit")):
        # A branch or tag would move under the pin: only a commit keeps it.
        if not _COMMIT.fullmatch(entry["commit"]):
            raise ResourceError(
                f"{path}: code resource {entry['name']} is pinned at "
                f"{entry['commit']!r}, not a commit hash"
            )
        source_of = entry.get("source_of")
        if source_of is not None and not isinstance(source_of, str):
            raise ResourceError(
                f"{path}: code resource {entry['name']} has a source_of that is not a citekey"
            )
        code_of = entry.get("code_of", [])
        if isinstance(code_of, str):
            code_of = [code_of]
        if not isinstance(code_of, list) or not all(
            isinstance(citekey, str) for citekey in code_of
        ):
            raise ResourceError(
                f"{path}: code resource {entry['name']} has a code_of that is not a "
                "citekey or a list of citekeys"
            )
        if source_of is not None and code_of:
            raise ResourceError(
                f"{path}: code resource {entry['name']} has both a source_of and a "
                "code_of: a repository is a document's source form or its code, not both"
            )
        code.append(
            Code(entry["name"], entry["url"], entry["commit"], source_of, tuple(code_of))
        )
    data_resources = []
    for entry in _entries(path, data, "data", ("name", "source", "sha256")):
        sha256 = entry["sha256"].lower()
        if not _SHA256.fullmatch(sha256):
            raise ResourceError(
                f"{path}: data resource {entry['name']} has a sha256 that is not 64 hex digits"
            )
        data_resources.append(Data(entry["name"], entry["source"], sha256))
    return Resources(code, data_resources)
