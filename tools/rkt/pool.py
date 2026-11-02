"""The pool: the one uncommitted folder holding every resource of the tree.

Its layout is `papers/<citekey>.pdf`, `code/<name>/` and `data/<name>`. Each inquiry
reaches it through a git-ignored `resources` link, so its agent reads resources at the
same relative path everywhere. One pool serves every tree on the machine.
"""

import os
import re
from pathlib import Path

from rkt import links, retrieve
from rkt.git import ignore

# Moves the pool for one shell, overriding the configuration's `pool`.
VARIABLE = "RKT_POOL"
DEFAULT = Path("~/research-pool")
LINK = "resources"


# A citekey or resource name becomes a file or folder of the pool, so it may not climb
# out of it or hide.
_PLAIN = re.compile(r"\w[\w.:+-]*")


def location() -> Path:
    """Where the pool is: `RKT_POOL`, else the configuration's `pool`, else ~/research-pool."""
    configured = os.environ.get(VARIABLE) or retrieve.settings()[0].get("pool") or DEFAULT
    return Path(os.path.abspath(Path(str(configured)).expanduser()))


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
    """Link the inquiry at `path` to the pool, out of git.

    Returns what needs attention: a real folder in the link's place is kept.
    """
    if (path / ".git").exists():
        ignore(path, LINK)
    resources = path / LINK
    made = links.directory(resources, pool, absolute=True)
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
