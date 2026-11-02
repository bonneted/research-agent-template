"""The workspace manifest: what the workspace is called, which repositories make it up,
and where to fetch them.
"""

import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml

FILENAME = "workspace.yaml"
ROLES = ("library", "hub", "study", "app", "off-limits")
# A workspace name prefixes its repositories, its `ask-<name>` skill and its
# environment variables (`<NAME>_RESOURCES`).
NAME = re.compile(r"[a-z0-9]+(-[a-z0-9]+)*")


class ManifestError(Exception):
    """The workspace manifest is missing or malformed."""


@dataclass(frozen=True)
class Repository:
    """One repository of the workspace, cloned at `<workspace root>/<name>`."""

    name: str
    url: str
    role: str
    # The key of its Zotero collection, when it is not found by name (see `refs`).
    zotero_collection: str | None = None


@dataclass(frozen=True)
class Blocked:
    """A regular expression an agent's tool call may not match, and what it guards."""

    pattern: str
    what: str


@dataclass(frozen=True)
class OffLimits:
    """Material an agent never reads (see `offlimits`); empty when the workspace has none."""

    # Globs: relative (`confidential/`, `**/resources/secret/`), `~/`-relative or absolute.
    paths: tuple[str, ...] = ()
    patterns: tuple[Blocked, ...] = ()
    deny_connectors: tuple[str, ...] = ()
    # A repository `ws sync` clones but never links, mounts or lists.
    repo: str | None = None

    def __bool__(self) -> bool:
        return bool(self.paths or self.patterns or self.deny_connectors or self.repo)


@dataclass(frozen=True)
class Workspace:
    """The workspace as its manifest describes it."""

    name: str
    repositories: list[Repository]
    # The GitLab group the workspace's repositories live in, as a URL.
    gitlab: str | None = None
    # Each repository's Zotero collection is `<zotero_root>/<repository>`.
    zotero_root: str = ""
    # The library studies pin and runs stamp; None for a workspace without one.
    library: str | None = None
    # `module:function`, called by every run stamp for fields of its own.
    stamp_extras: str | None = None
    # The hub folder of rule packs, copied into each study at spawn.
    rule_packs_dir: str = "rules"
    off_limits: OffLimits = field(default_factory=OffLimits)

    @property
    def hub(self) -> Repository:
        return next(
            repository for repository in self.repositories if repository.role == "hub"
        )

    def repository(self, name: str) -> Repository | None:
        return next(
            (repository for repository in self.repositories if repository.name == name),
            None,
        )

    def variable(self, suffix: str) -> str:
        """The environment variable `<NAME>_<suffix>` of this workspace."""
        return f"{self.name.upper().replace('-', '_')}_{suffix}"

    def url(self, name: str) -> str:
        """Where the repository `name` lives on GitLab: in the workspace's group, or else
        beside the hub.
        """
        group = self.gitlab or self.hub.url.rsplit("/", 1)[0]
        return f"{group.rstrip('/')}/{name}.git"


def find_hub(start: Path) -> Path:
    """The hub of the workspace `start` is in: the nearest folder at or above `start`
    holding the workspace manifest, or else beside one.
    """
    for folder in (start, *start.parents):
        if (folder / FILENAME).is_file():
            return folder
        try:
            hubs = [child for child in folder.iterdir() if (child / FILENAME).is_file()]
        except OSError:
            hubs = []
        if len(hubs) == 1:
            return hubs[0]
    raise ManifestError(f"no {FILENAME} in {start} or above: run ws from the hub")


def repository_at(root: Path, repositories: list[Repository], folder: Path) -> str:
    """The name of the repository of the workspace at `root` that `folder` is in."""
    for repository in repositories:
        if folder.resolve().is_relative_to((root / repository.name).resolve()):
            return repository.name
    raise ManifestError(f"{folder} is in no repository of the workspace: give --repo")


def _read(hub: Path) -> object:
    path = hub / FILENAME
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as error:
        raise ManifestError(f"{path}: {error}") from error


def template(hub: Path) -> str:
    """The URL of the template every study is spawned from."""
    data = _read(hub)
    url = data.get("template") if isinstance(data, dict) else None
    if not isinstance(url, str):
        raise ManifestError(f"{hub / FILENAME}: expected a 'template' URL")
    return url


def add(hub: Path, repository: Repository) -> None:
    """List `repository` last in the manifest, keeping the file's comments.

    The entry is appended as text, so `repositories` must be the manifest's last key;
    the manifest is left as it was if it is not.
    """
    path = hub / FILENAME
    text = path.read_text(encoding="utf-8")
    entry = (
        f"  - name: {repository.name}\n"
        f"    url: {repository.url}\n"
        f"    role: {repository.role}\n"
    )
    path.write_text(
        text + ("" if text.endswith("\n") else "\n") + entry, encoding="utf-8"
    )
    try:
        added = repository in load(hub).repositories
    except ManifestError:
        added = False
    if not added:
        path.write_text(text, encoding="utf-8")
        raise ManifestError(
            f"{path}: could not add {repository.name}: keep 'repositories' the last key"
        )


def _strings(path: Path, data: dict, key: str) -> tuple[str, ...]:
    """The list of strings at `key` of the off-limits block; empty if absent."""
    values = data.get(key) or []
    if not isinstance(values, list) or not all(
        isinstance(value, str) and value for value in values
    ):
        raise ManifestError(f"{path}: off_limits.{key} must be a list of strings")
    return tuple(values)


def _off_limits(path: Path, data: object) -> OffLimits:
    if data is None:
        return OffLimits()
    if not isinstance(data, dict):
        raise ManifestError(f"{path}: off_limits must be a mapping")
    unknown = sorted(set(data) - {"paths", "patterns", "deny_connectors", "repo"})
    if unknown:
        raise ManifestError(f"{path}: off_limits has unknown keys: {', '.join(unknown)}")
    patterns = []
    for index, entry in enumerate(data.get("patterns") or []):
        # A pattern is a regular expression, or one with what it guards.
        if isinstance(entry, str):
            entry = {"pattern": entry}
        if not isinstance(entry, dict) or not isinstance(entry.get("pattern"), str):
            raise ManifestError(
                f"{path}: off_limits pattern {index} needs a regular expression"
            )
        try:
            re.compile(entry["pattern"])
        except re.error as error:
            raise ManifestError(
                f"{path}: off_limits pattern {entry['pattern']!r}: {error}"
            ) from error
        patterns.append(
            Blocked(entry["pattern"], str(entry.get("what") or "off-limits material"))
        )
    repo = data.get("repo")
    if repo is not None and not isinstance(repo, str):
        raise ManifestError(f"{path}: off_limits.repo must be a repository name")
    return OffLimits(
        _strings(path, data, "paths"),
        tuple(patterns),
        _strings(path, data, "deny_connectors"),
        repo,
    )


_KEYS = (
    "name",
    "gitlab",
    "zotero_root",
    "library",
    "stamp_extras",
    "rule_packs_dir",
    "off_limits",
)


def _workspace(path: Path, data: object) -> dict:
    """The keys of the manifest's `workspace` block, checked."""
    if not isinstance(data, dict) or not isinstance(data.get("name"), str):
        raise ManifestError(f"{path}: expected a 'workspace' block with a name")
    if not NAME.fullmatch(data["name"]):
        raise ManifestError(
            f"{path}: workspace name {data['name']!r} is not lowercase letters and "
            "digits joined by dashes"
        )
    if unknown := sorted(set(data) - set(_KEYS)):
        raise ManifestError(f"{path}: workspace has unknown keys: {', '.join(unknown)}")
    for key in _KEYS[1:-1]:
        if data.get(key) is not None and not isinstance(data[key], str):
            raise ManifestError(f"{path}: workspace.{key} must be text")
    extras = data.get("stamp_extras") or None
    if extras is not None and not re.fullmatch(r"[\w.]+:\w+", extras):
        raise ManifestError(
            f"{path}: workspace.stamp_extras {extras!r} is not `module:function`"
        )
    return {
        "name": data["name"],
        "gitlab": data.get("gitlab") or None,
        "zotero_root": data.get("zotero_root") or data["name"],
        "library": data.get("library") or None,
        "stamp_extras": extras,
        "rule_packs_dir": data.get("rule_packs_dir") or "rules",
        "off_limits": _off_limits(path, data.get("off_limits")),
    }


def load(hub: Path) -> Workspace:
    """The workspace described by the hub's manifest."""
    path = hub / FILENAME
    data = _read(hub)
    if not isinstance(data, dict):
        raise ManifestError(
            f"{path}: expected a 'workspace' block and a 'repositories' list"
        )
    settings = _workspace(path, data.get("workspace"))
    entries = data.get("repositories")
    if not isinstance(entries, list):
        raise ManifestError(f"{path}: expected a 'repositories' list")
    repositories = []
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict) or not all(
            isinstance(entry.get(key), str) for key in ("name", "url", "role")
        ):
            raise ManifestError(
                f"{path}: repository {index} needs a name, url and role"
            )
        if entry["role"] not in ROLES:
            raise ManifestError(
                f"{path}: {entry['name']} has role {entry['role']!r}, expected one of {ROLES}"
            )
        collection = entry.get("zotero_collection")
        if collection is not None and not isinstance(collection, str):
            raise ManifestError(
                f"{path}: {entry['name']} has a zotero_collection that is not a key"
            )
        repositories.append(
            Repository(entry["name"], entry["url"], entry["role"], collection)
        )
    names = [repository.name for repository in repositories]
    if duplicates := sorted({name for name in names if names.count(name) > 1}):
        raise ManifestError(f"{path}: listed more than once: {', '.join(duplicates)}")
    # The workspace root is the hub's parent: a hub folder named otherwise would be
    # cloned a second time beside itself.
    hubs = [repository.name for repository in repositories if repository.role == "hub"]
    if hubs != [hub.name]:
        raise ManifestError(
            f"{path}: the hub is the folder {hub.name!r}, but the manifest lists "
            f"{hubs or 'no hub'} as hub"
        )

    def named(role: str) -> list[str]:
        return [
            repository.name for repository in repositories if repository.role == role
        ]

    # The library and the off-limits repository are named in the workspace block; one
    # not listed yet is a repository still to come.
    libraries = named("library")
    if len(libraries) > 1:
        raise ManifestError(f"{path}: more than one library: {', '.join(libraries)}")
    library = settings["library"] or (libraries[0] if libraries else None)
    if libraries and libraries != [library]:
        raise ManifestError(
            f"{path}: workspace.library is {library}, but {libraries[0]} has role library"
        )
    if library in names and library not in libraries:
        raise ManifestError(f"{path}: the library {library} must have role library")
    settings["library"] = library
    off_limits = settings["off_limits"]
    for name in named("off-limits"):
        if name != off_limits.repo:
            raise ManifestError(
                f"{path}: {name} has role off-limits but is not off_limits.repo"
            )
    if off_limits.repo in names and off_limits.repo not in named("off-limits"):
        raise ManifestError(
            f"{path}: the off-limits repository {off_limits.repo} must have role off-limits"
        )
    return Workspace(repositories=repositories, **settings)
