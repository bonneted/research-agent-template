"""Links between an inquiry's folders and the pool, made without admin rights on every platform.

On Linux and macOS a link is a symbolic link, relative where it can be so that the
tree can move. On Windows a symbolic link needs admin rights or Developer Mode, so
a folder link is a directory junction, which needs neither and always holds an absolute
path, and a file link is a copy: its hash is recorded when `rkt` writes it, so that a
copy edited since is reported and kept rather than overwritten.
"""

import hashlib
import json
import os
import shutil
from pathlib import Path

WINDOWS = os.name == "nt"
# Beside the copies made in place of file links, the hash of each when `ws` wrote it.
COPIES = ".rkt-copies.json"

# What `directory` did: the link was already right, made, moved to the target, or
# something else is in its place and was left as is.
SAME, MADE, MOVED, BLOCKED = "same", "made", "moved", "blocked"


def _create_junction(target: str, link: str) -> None:
    import _winapi  # Windows only

    _winapi.CreateJunction(target, link)


def _is_junction(path: Path) -> bool:
    isjunction = getattr(os.path, "isjunction", None)
    if isjunction is not None:
        return isjunction(path)
    try:
        # IO_REPARSE_TAG_MOUNT_POINT, before Python 3.12 had `os.path.isjunction`.
        return getattr(os.lstat(path), "st_reparse_tag", 0) == 0xA0000003
    except OSError:
        return False


def _remove_junction(path: Path) -> None:
    os.rmdir(path)


def is_link(path: Path) -> bool:
    """Whether `path` is a link `ws` could have made: a symbolic link or a junction."""
    return path.is_symlink() or (WINDOWS and _is_junction(path))


def _resolved(path: Path) -> Path:
    return Path(os.path.realpath(path))


def _remove(link: Path) -> None:
    if WINDOWS:
        _remove_junction(link)
    else:
        link.unlink()


def directory(link: Path, target: Path, absolute: bool = False) -> str:
    """Point `link` at the folder `target`, relative to the link unless `absolute`.

    Returns `SAME`, `MADE`, `MOVED`, or `BLOCKED` if something else is in its place.
    """
    text = (
        str(target) if absolute else os.path.relpath(target, link.parent)
    )
    if is_link(link):
        if WINDOWS:
            if _resolved(link) == _resolved(target):
                return SAME
        elif os.readlink(link) == text:
            return SAME
        _remove(link)
        made = MOVED
    elif link.exists():
        return BLOCKED
    else:
        made = MADE
    link.parent.mkdir(parents=True, exist_ok=True)
    if WINDOWS:
        _create_junction(os.path.abspath(target), str(link))
    else:
        link.symlink_to(text, target_is_directory=True)
    return made


def _hash(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def _record(folder: Path) -> dict[str, str]:
    try:
        record = json.loads((folder / COPIES).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return record if isinstance(record, dict) else {}


def _copy(link: Path, target: Path, record: dict[str, str]) -> None:
    link.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(target, link)
    record[link.name] = _hash(link)
    (link.parent / COPIES).write_text(
        json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def file(link: Path, target: Path) -> list[str]:
    """Point the file `link` at `target`: a relative symbolic link, or on Windows a copy.

    Returns what needs attention: a file of the link's name that `ws` did not make, or
    a copy edited since `ws` wrote it, is kept.
    """
    if not WINDOWS:
        text = os.path.relpath(target, link.parent)
        if link.is_symlink():
            if os.readlink(link) == text:
                return []
            link.unlink()
        elif link.exists():
            return [f"{link.name} is not a link to {target}, left as is"]
        link.parent.mkdir(parents=True, exist_ok=True)
        link.symlink_to(text)
        return []
    record = _record(link.parent)
    if link.is_symlink() and _resolved(link) == _resolved(target):
        return []
    if not link.exists():
        _copy(link, target, record)
        return []
    current = _hash(link)
    if current == _hash(target):
        if record.get(link.name) != current:
            record[link.name] = current
            (link.parent / COPIES).write_text(
                json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8"
            )
        return []
    if record.get(link.name) == current:
        # The copy is as `ws` wrote it: the hub's file moved on, so it is copied again.
        _copy(link, target, record)
        return []
    return [f"{link.name} differs from {target} and was edited since rkt copied it, left as is"]


def file_drift(link: Path, target: Path) -> str | None:
    """What is wrong with the file link `link` to `target`, or None if it is current."""
    if link.is_symlink():
        return None if _resolved(link) == _resolved(target) else f"{link.name} links elsewhere"
    if not link.exists():
        return f"{link.name} missing"
    if not WINDOWS:
        return f"{link.name} is not a link to {target}"
    if _hash(link) != _hash(target):
        return f"{link.name} differs from {target}"
    return None
