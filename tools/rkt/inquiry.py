"""An inquiry's relations, from its `inquiry.yaml`, and the tree of inquiries below it.

An inquiry is a folder holding `inquiry.yaml`. Its sub-inquiries are cloned into its
`inquiries/<name>/`, so the folder tree is the knowledge tree: a parent is two folders up.
"""

import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml

FILENAME = "inquiry.yaml"
OFF_LIMITS = ".off-limits.yaml"
CHILDREN = "inquiries"

NAME = re.compile(r"[a-z0-9]+(-[a-z0-9]+)*")


class InquiryError(Exception):
    """An inquiry's files are missing or malformed."""


@dataclass(frozen=True)
class Child:
    """A sub-inquiry as its parent's `inquiry.yaml` lists it."""

    name: str
    url: str


@dataclass(frozen=True)
class Blocked:
    """A regular expression an agent's tool call may not match, and what it guards."""

    pattern: str
    what: str


@dataclass(frozen=True)
class OffLimits:
    """Material an agent never reads (see `offlimits`); empty when the inquiry has none."""

    # Globs: relative (`confidential/`, `**/resources/secret/`), `~/`-relative or absolute.
    paths: tuple[str, ...] = ()
    patterns: tuple[Blocked, ...] = ()
    deny_connectors: tuple[str, ...] = ()

    def __bool__(self) -> bool:
        return bool(self.paths or self.patterns or self.deny_connectors)

    def covers(self, other: "OffLimits") -> list[str]:
        """What `other` lists that this does not: empty when this is a superset."""
        mine = {blocked.pattern for blocked in self.patterns}
        return [
            *(f"path {path}" for path in other.paths if path not in self.paths),
            *(
                f"pattern {blocked.pattern}"
                for blocked in other.patterns
                if blocked.pattern not in mine
            ),
            *(
                f"connector {name}"
                for name in other.deny_connectors
                if name not in self.deny_connectors
            ),
        ]


@dataclass(frozen=True)
class Inquiry:
    """One inquiry, as its `inquiry.yaml` describes it."""

    path: Path
    question: str
    parent: str | None
    children: tuple[Child, ...]
    zotero_collection: str | None
    rule_packs: tuple[str, ...]
    kit: dict = field(default_factory=dict)
    # How the inquiry is named in reports: its path of names from the top of the tree.
    label: str = ""

    @property
    def name(self) -> str:
        return self.path.name

    def child_path(self, name: str) -> Path:
        return self.path / CHILDREN / name

    @property
    def parent_path(self) -> Path | None:
        """The parent's folder, when this inquiry sits in one's `inquiries/`."""
        above = self.path.parent
        if above.name == CHILDREN and (above.parent / FILENAME).is_file():
            return above.parent
        return None


def find(start: Path) -> Path:
    """The inquiry holding `start`: the nearest folder at or above it with `inquiry.yaml`."""
    start = start.resolve()
    for folder in (start, *start.parents):
        if (folder / FILENAME).is_file():
            return folder
    raise InquiryError(
        f"no {FILENAME} in {start} or above it: run rkt in an inquiry, or `rkt init`"
    )


def _text(path: Path, data: dict, key: str) -> str | None:
    value = data.get(key)
    if value is None or value == "":
        return None
    if not isinstance(value, str):
        raise InquiryError(f"{path}: {key} must be text")
    return value


def _children(path: Path, data: object) -> tuple[Child, ...]:
    if data is None:
        return ()
    if not isinstance(data, list):
        raise InquiryError(f"{path}: inquiries must be a list")
    children = []
    for index, entry in enumerate(data):
        if not (
            isinstance(entry, dict)
            and isinstance(entry.get("name"), str)
            and isinstance(entry.get("url"), str)
        ):
            raise InquiryError(f"{path}: inquiries[{index}] needs a name and a url")
        if not NAME.fullmatch(entry["name"]):
            raise InquiryError(
                f"{path}: sub-inquiry name {entry['name']!r} is not lowercase letters "
                "and digits joined by dashes"
            )
        children.append(Child(entry["name"], entry["url"]))
    names = [child.name for child in children]
    if duplicates := sorted({name for name in names if names.count(name) > 1}):
        raise InquiryError(f"{path}: sub-inquiries listed twice: {', '.join(duplicates)}")
    return tuple(children)


_KEYS = {"question", "parent", "inquiries", "zotero_collection", "rule_packs", "kit"}


def load(folder: Path, label: str | None = None) -> Inquiry:
    """The inquiry at `folder`. Raises `InquiryError` if its `inquiry.yaml` is malformed."""
    path = folder / FILENAME
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError) as error:
        raise InquiryError(f"{path}: {error}") from error
    if not isinstance(data, dict):
        raise InquiryError(f"{path}: expected a mapping")
    if unknown := sorted(set(data) - _KEYS):
        raise InquiryError(f"{path}: unknown keys: {', '.join(unknown)}")
    packs = data.get("rule_packs") or []
    if not isinstance(packs, list) or not all(isinstance(pack, str) for pack in packs):
        raise InquiryError(f"{path}: rule_packs must be a list of pack names")
    kit = data.get("kit") or {}
    if not isinstance(kit, dict):
        raise InquiryError(f"{path}: kit must be a mapping")
    return Inquiry(
        path=folder,
        question=_text(path, data, "question") or "",
        parent=_text(path, data, "parent"),
        children=_children(path, data.get("inquiries")),
        zotero_collection=_text(path, data, "zotero_collection"),
        rule_packs=tuple(packs),
        kit=kit,
        label=label or folder.name,
    )


def tree(top: Inquiry) -> list[Inquiry]:
    """`top` and every sub-inquiry cloned below it, depth first; uncloned ones are skipped."""
    found = [top]
    for child in top.children:
        folder = top.child_path(child.name)
        if (folder / FILENAME).is_file():
            found += tree(load(folder, f"{top.label}/{child.name}"))
    return found


def _strings(path: Path, data: dict, key: str) -> tuple[str, ...]:
    values = data.get(key) or []
    if not isinstance(values, list) or not all(
        isinstance(value, str) and value for value in values
    ):
        raise InquiryError(f"{path}: {key} must be a list of strings")
    return tuple(values)


def off_limits(folder: Path) -> OffLimits:
    """The off-limits material `.off-limits.yaml` lists at `folder`; empty if it has none."""
    path = folder / OFF_LIMITS
    if not path.is_file():
        return OffLimits()
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as error:
        raise InquiryError(f"{path}: {error}") from error
    if data is None:
        return OffLimits()
    if not isinstance(data, dict):
        raise InquiryError(f"{path}: expected a mapping")
    if unknown := sorted(set(data) - {"paths", "patterns", "deny_connectors"}):
        raise InquiryError(f"{path}: unknown keys: {', '.join(unknown)}")
    patterns = []
    for index, entry in enumerate(data.get("patterns") or []):
        # A pattern is a regular expression, or one with what it guards.
        if isinstance(entry, str):
            entry = {"pattern": entry}
        if not isinstance(entry, dict) or not isinstance(entry.get("pattern"), str):
            raise InquiryError(f"{path}: pattern {index} needs a regular expression")
        try:
            re.compile(entry["pattern"])
        except re.error as error:
            raise InquiryError(f"{path}: pattern {entry['pattern']!r}: {error}") from error
        patterns.append(
            Blocked(entry["pattern"], str(entry.get("what") or "off-limits material"))
        )
    return OffLimits(
        _strings(path, data, "paths"),
        tuple(patterns),
        _strings(path, data, "deny_connectors"),
    )
