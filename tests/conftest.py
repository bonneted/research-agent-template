"""The temporary knowledge tree every `rkt` test drives.

A root inquiry, `demo`, made from the kit by `rkt init`, with one sub-inquiry,
`framework`, cloned into its `inquiries/`. Local bare repositories stand in for the
forge; the pool is a folder of the temporary directory.
"""

import subprocess
import sys
from pathlib import Path

import pytest
import yaml
from rkt import kit

TEMPLATE = Path(__file__).resolve().parents[1]
# The rigour pack's code, imported as an inquiry imports it: `study`.
sys.path.insert(0, str(TEMPLATE / "kit" / "rules" / "rigour"))


@pytest.fixture(autouse=True)
def isolated(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Keep the user's git configuration, rkt configuration and pool out of the tests."""
    # The pool is the temporary one, never the user's.
    monkeypatch.setenv("RKT_POOL", str(tmp_path / "pool"))
    monkeypatch.delenv("RKT_SSH_HOST", raising=False)
    # No configuration of the user's: no Zotero, no email for Unpaywall, no pool.
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", str(tmp_path / "gitconfig"))
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    for role in ("AUTHOR", "COMMITTER"):
        monkeypatch.setenv(f"GIT_{role}_NAME", "Test")
        monkeypatch.setenv(f"GIT_{role}_EMAIL", "test@example.com")


def git(*args: str, cwd: Path) -> str:
    return subprocess.run(
        ["git", *args], cwd=cwd, check=True, capture_output=True, text=True
    ).stdout.strip()


def make_remote(remotes: Path, name: str, files: dict[str, str] | None = None) -> str:
    """A bare repository with one commit on `main` holding a README and `files`; returns its URL."""
    work = remotes / f"{name}-seed"
    work.mkdir(parents=True)
    git("init", "--quiet", cwd=work)
    git("checkout", "--quiet", "-b", "main", cwd=work)
    for path, text in {"README.md": f"# {name}\n", **(files or {})}.items():
        (work / path).parent.mkdir(parents=True, exist_ok=True)
        (work / path).write_text(text)
    git("add", ".", cwd=work)
    git("commit", "--quiet", "-m", "Initial commit", cwd=work)
    bare = remotes / f"{name}.git"
    git("clone", "--quiet", "--bare", str(work), str(bare), cwd=remotes)
    return bare.as_uri()


def write_yaml(path: Path, **changes: object) -> None:
    """Change keys of an `inquiry.yaml`."""
    data = yaml.safe_load(path.read_text()) or {}
    data.update(changes)
    path.write_text(yaml.safe_dump(data, sort_keys=False))


def commit_all(folder: Path, message: str = "Work") -> str:
    git("add", "-A", cwd=folder)
    git("commit", "--quiet", "--allow-empty", "-m", message, cwd=folder)
    return git("rev-parse", "HEAD", cwd=folder)


class Tree:
    """A root inquiry and one sub-inquiry, each a git repository made from the kit."""

    def __init__(self, tmp: Path) -> None:
        self.tmp = tmp
        self.remotes = tmp / "remotes"
        self.remotes.mkdir()
        self.root = tmp / "demo"
        self.pool = tmp / "pool"
        self.pool.mkdir()
        self.urls = {name: make_remote(self.remotes, name) for name in ("demo", "framework")}
        self.root = self._inquiry(tmp / "demo", "demo", "What does the demo show?")
        self.child = self._inquiry(
            self.root / "inquiries" / "framework", "framework", "Does the framework hold?"
        )
        write_yaml(self.root / "inquiry.yaml", zotero_collection="demo",
                   inquiries=[{"name": "framework", "url": self.urls["framework"]}])
        write_yaml(self.child / "inquiry.yaml", zotero_collection="demo/framework",
                   parent=self.urls["demo"])
        self.route()

    def _inquiry(self, folder: Path, name: str, question: str) -> Path:
        git("clone", "--quiet", self.urls[name], str(folder), cwd=self.tmp)
        lines, ok = kit.init(folder, question)
        assert ok, lines
        commit_all(folder, "Start the inquiry")
        return folder

    @property
    def hub(self) -> Path:
        """The root inquiry, by the name the older tests use."""
        return self.root

    def route(self) -> None:
        """Route the root's index to the sub-inquiry, as `spawn` would."""
        index = self.root / "docs/wiki/index.md"
        text = index.read_text()
        route = (
            "- [framework](../../inquiries/framework/docs/wiki/index.md): "
            "Does the framework hold? Active. Dive here for: the framework.\n"
        )
        index.write_text(text.replace("### Open\n", f"{route}\n### Open\n"))

    def run(self, *command: str) -> subprocess.CompletedProcess[str]:
        return self.run_in(self.root, *command)

    def run_in(self, folder: Path, *command: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, "-m", "rkt", *command],
            cwd=folder,
            capture_output=True,
            text=True,
            check=False,
        )

    def fetch(self) -> subprocess.CompletedProcess[str]:
        return self.run("fetch", "--tree")


@pytest.fixture
def tree(tmp_path: Path) -> Tree:
    return Tree(tmp_path)
