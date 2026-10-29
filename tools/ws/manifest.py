"""The workspace manifest: which repositories make up the workspace, and where to fetch them."""

from dataclasses import dataclass
from pathlib import Path

import yaml

FILENAME = "workspace.yaml"
ROLES = ("library", "hub", "study", "app")


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
        added = repository in load(hub)
    except ManifestError:
        added = False
    if not added:
        path.write_text(text, encoding="utf-8")
        raise ManifestError(
            f"{path}: could not add {repository.name}: keep 'repositories' the last key"
        )


def load(hub: Path) -> list[Repository]:
    """The repositories listed in the hub's workspace manifest."""
    path = hub / FILENAME
    data = _read(hub)
    entries = data.get("repositories") if isinstance(data, dict) else None
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
    return repositories
