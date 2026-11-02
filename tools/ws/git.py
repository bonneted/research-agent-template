"""Git, run without a terminal so that a refused remote fails instead of prompting."""

import os
import subprocess
from pathlib import Path

# An HTTPS remote that refuses us (a private project, or one not created yet) would
# otherwise make git wait for a password on the terminal instead of failing.
_ENV = {**os.environ, "GIT_TERMINAL_PROMPT": "0"}


class GitError(Exception):
    """A git command failed; the message is git's reason."""


def git(*args: str, cwd: Path) -> str:
    """Run git in `cwd` and return its output; raise `GitError` with git's reason if it fails."""
    process = subprocess.run(
        ["git", *args],
        cwd=cwd,
        env=_ENV,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if process.returncode != 0:
        lines = [line.strip() for line in process.stderr.splitlines() if line.strip()]
        fatal = [line for line in lines if line.startswith("fatal:")]
        raise GitError((fatal or lines or [f"git exited with {process.returncode}"])[0])
    return process.stdout


def ignore(path: Path, name: str) -> None:
    """Keep the root entry `name` out of git in the clone at `path`, without a commit to it."""
    exclude = path / git("rev-parse", "--git-path", "info/exclude", cwd=path).strip()
    exclude.parent.mkdir(parents=True, exist_ok=True)
    lines = exclude.read_text(encoding="utf-8").splitlines() if exclude.exists() else []
    if f"/{name}" not in lines:
        exclude.write_text("\n".join([*lines, f"/{name}"]) + "\n", encoding="utf-8")
