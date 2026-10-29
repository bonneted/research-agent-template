"""The pool: the one uncommitted folder holding every resource of the workspace.

Its layout is `papers/<citekey>.pdf`, `code/<name>/` and `data/<name>`. Each repository
reaches it through a git-ignored `resources` link, so its agent reads resources at the
same relative path everywhere.
"""

import os
import re
from pathlib import Path

from ws import links
from ws.git import ignore
from ws.manifest import Workspace

# `<NAME>_RESOURCES` keeps the pool elsewhere, such as on another drive; a relative path
# is taken from the workspace root.
SUFFIX = "RESOURCES"
LINK = "resources"


# A citekey or resource name becomes a file or folder of the pool, so it may not climb
# out of it or hide.
_PLAIN = re.compile(r"\w[\w.:+-]*")


def variable(workspace: Workspace) -> str:
    """The environment variable that moves the workspace's pool."""
    return workspace.variable(SUFFIX)


def location(root: Path, workspace: Workspace) -> Path:
    """Where the pool of the workspace at `root` is."""
    configured = Path(os.environ.get(variable(workspace)) or LINK).expanduser()
    return Path(os.path.abspath(root / configured))


def is_plain(name: str) -> bool:
    """Whether `name` can name a file or folder of the pool."""
    return bool(_PLAIN.fullmatch(name))


def paper(citekey: str) -> str:
    """Where a document's PDF is, relative to the pool."""
    return f"papers/{citekey}.pdf"


def code(name: str) -> str:
    """Where a code resource is cloned, relative to the pool."""
    return f"code/{name}"


def data(name: str) -> str:
    """Where a data resource is, relative to the pool."""
    return f"data/{name}"


def link(path: Path, pool: Path) -> list[str]:
    """Link the repository at `path` to the pool, out of git.

    Returns what needs attention: a real folder in the link's place is kept.
    """
    ignore(path, LINK)
    resources = path / LINK
    # Relative inside the workspace, so the workspace can move; absolute elsewhere.
    made = links.directory(
        resources, pool, absolute=not pool.is_relative_to(path.parent)
    )
    if made == links.MOVED:
        return [f"{LINK} relinked to {pool}"]
    if made == links.BLOCKED:
        return [
            (
                f"{LINK}/ is a folder, not a link to the pool: "
                f"move what it holds into {pool} and delete it"
            )
        ]
    return []
