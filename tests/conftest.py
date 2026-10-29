"""The temporary workspace every `ws` test drives.

Local bare repositories stand in for GitLab: a workspace root holds the hub (with its
workspace manifest) and a folder of remotes; `ws` runs from the hub as the researcher
would run it.
"""

import subprocess
import sys
from pathlib import Path

import pytest
import yaml

HUB = Path(__file__).resolve().parents[1]

# A stand-in for the research agent template: its layout and its "project" wording.
TEMPLATE = {
    "AGENTS.md": "# Project\n\nThe wiki is the project memory.\n",
    "CLAUDE.md": "@AGENTS.md\n",
    "pyproject.toml": '[project]\nname = "research-project"\n',
    ".gitignore": "resources/*\n!resources/README.md\n.claude/skills/\n",
    "resources/README.md": "# Resources\n",
    "references.bib": "% Exported from Zotero. See resources/README.md.\n",
    "docs/CONTEXT.md": "# Context\n\nThe project's vocabulary.\n",
    "docs/wiki/index.md": "# Wiki\n\nWhy the project is built the way it is.\n",
    "docs/wiki/reading-list.md": "Needed by the project, for Project work and projects.\n",
    ".agents/skills/digest-source/SKILL.md": (
        "Judge it against the project line. Missing: run `uv run fetch`.\n"
        "Add it with `uv run refs add <DOI>`, then `uv run refs pull`.\n"
    ),
    "src/research_project/__init__.py": "",
    "tools/zotero.py": 'API = "https://api.example.org/projects/"\n',
    "tests/test_import.py": "def test_package_imports():\n    import research_project\n",
    # The template's own fetch step, which a study leaves to the hub's `ws fetch`.
    "resources.yaml": "# Fetched into resources/ by `uv run fetch` (see resources/README.md).\ncode: []\n",
    "tools/fetch/__init__.py": "",
    "tools/fetch/cli.py": "def main():\n    pass\n",
    "tests/conftest.py": "from pathlib import Path\n",
    "tests/test_fetch.py": "from fetch.cli import main\n\n\ndef test_main():\n    main()\n",
    "tests/test_retrieve.py": "from fetch import retrieve  # noqa: F401\n",
    "tests/test_refs.py": "from fetch import refs  # noqa: F401\n",
    "uv.lock": "version = 1\n",
}


def hub_files() -> dict[str, str]:
    """The hub's overlay, rule packs and off-limits hook as tracked in this repository, a
    hub skill, the library's private context, and the hub's ignores.
    """
    tracked = git(
        "ls-files", "-z", "--", "overlay", "rules", "tools/ws/guard_off_limits.py", cwd=HUB
    ).split("\0")
    files = {name: (HUB / name).read_text() for name in filter(None, tracked)}
    files[".gitignore"] = "__pycache__/\n"
    files["skills/publish-finding/SKILL.md"] = "# Publish a finding\n"
    files["docs/studies/index.md"] = "- **demo-framework**: framework\n"
    files["docs/library/CLAUDE.md"] = "# The library's private context\n"
    return files


@pytest.fixture(autouse=True)
def isolated_git(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Keep the user's git configuration and pool out of the tests."""
    monkeypatch.delenv("DEMO_RESOURCES", raising=False)
    # No retrieval configuration of the user's: no Zotero, and no email for Unpaywall.
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
    # `git init --initial-branch` needs git 2.28; r2d2 has 2.25.
    git("checkout", "--quiet", "-b", "main", cwd=work)
    for path, text in {"README.md": f"# {name}\n", **(files or {})}.items():
        (work / path).parent.mkdir(parents=True, exist_ok=True)
        (work / path).write_text(text)
    git("add", ".", cwd=work)
    git("commit", "--quiet", "-m", "Initial commit", cwd=work)
    bare = remotes / f"{name}.git"
    git("clone", "--quiet", "--bare", str(work), str(bare), cwd=remotes)
    return bare.as_uri()


class Workspace:
    """A workspace root holding only the hub, as on a machine right after cloning it."""

    def __init__(self, tmp: Path) -> None:
        self.tmp = tmp
        self.remotes = tmp / "remotes"
        self.root = tmp / "ws"
        self.root.mkdir()
        self.roles = {
            "demo": "library",
            "demo-hub": "hub",
            "demo-framework": "study",
        }
        # The hub indexes its study, and the study has notes to mount.
        seeds = {
            "demo-hub": hub_files(),
            "demo-framework": {"docs/wiki/index.md": "# Wiki\n"},
        }
        self.urls = {
            name: make_remote(self.remotes, name, seeds.get(name))
            for name in self.roles
        }
        self.template = make_remote(self.remotes, "template", TEMPLATE)
        # The manifest's `workspace` block; a test adds keys such as `off_limits`.
        self.settings: dict = {"name": "demo"}
        self.hub = self.root / "demo-hub"
        git("clone", "--quiet", self.urls["demo-hub"], str(self.hub), cwd=self.root)
        self.write_manifest()

    def write_manifest(self) -> None:
        lines = [
            yaml.safe_dump({"workspace": self.settings}, sort_keys=False).rstrip(),
            f"template: {self.template}",
            "repositories:",
        ]
        for name, role in self.roles.items():
            lines += [
                f"  - name: {name}",
                f"    url: {self.urls[name]}",
                f"    role: {role}",
            ]
        (self.hub / "workspace.yaml").write_text("\n".join(lines) + "\n")

    @property
    def pool(self) -> Path:
        """Where the pool is when `DEMO_RESOURCES` is not set."""
        return self.root / "resources"

    def sync(self) -> subprocess.CompletedProcess[str]:
        return self.run("sync")

    def fetch(self) -> subprocess.CompletedProcess[str]:
        return self.run("fetch")

    def spawn(self, topic: str) -> subprocess.CompletedProcess[str]:
        return self.run("spawn", topic)

    def run(self, *command: str) -> subprocess.CompletedProcess[str]:
        return self.run_in(self.hub, *command)

    def run_in(self, folder: Path, *command: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, "-m", "ws", *command],
            cwd=folder,
            capture_output=True,
            text=True,
            check=False,
        )


@pytest.fixture
def workspace(tmp_path: Path) -> Workspace:
    return Workspace(tmp_path)
