"""Links between an inquiry's folders and the pool, made without admin rights on every platform.

On Linux and macOS a link is a symbolic link, relative where it can be so that the
tree can move. On Windows a symbolic link needs admin rights or Developer Mode, so
a folder link is a directory junction, which needs neither and always holds an absolute
path.
"""

import os
from pathlib import Path

WINDOWS = os.name == "nt"
# Beside the copies made in place of file links, the hash of each when `ws` wrote it.

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
