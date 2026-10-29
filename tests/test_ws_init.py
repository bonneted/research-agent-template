"""`ws init`: a workspace started from a copy of this template, its hub made, committed
and synced, without a question asked.
"""

import json
import os
import re
from pathlib import Path

import pytest
import yaml
from conftest import HUB, git
from ws import cli, init, manifest

GITLAB = "https://gitlab.example.org/group/acme"


@pytest.fixture
def template(tmp_path: Path) -> Path:
    """A clone of this template as git tracks it now, committed, with its remotes."""
    source = tmp_path / "research-ws-template"
    source.mkdir()
    for name in filter(None, git("ls-files", "-z", cwd=HUB).split("\0")):
        if (HUB / name).is_file() and not (HUB / name).is_symlink():
            (source / name).parent.mkdir(parents=True, exist_ok=True)
            (source / name).write_bytes((HUB / name).read_bytes())
    git("init", "--quiet", cwd=source)
    git("checkout", "--quiet", "-b", "main", cwd=source)
    git("add", "--all", cwd=source)
    git("commit", "--quiet", "-m", "Template", cwd=source)
    git("remote", "add", "origin", "https://gitlab.example.org/ws-template.git", cwd=source)
    git("remote", "add", "template", "https://gitlab.example.org/agent-template.git", cwd=source)
    return source


@pytest.fixture
def root(tmp_path: Path, template: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    folder = tmp_path / "acme-ws"
    folder.mkdir()
    monkeypatch.chdir(folder)
    monkeypatch.setattr(init, "source", lambda: template)
    return folder


def start(*flags: str) -> int:
    return cli.main(["init", "acme", "--no-input", "--gitlab", GITLAB, *flags])


def test_init_makes_the_hub_commits_it_and_syncs(
    root: Path, capsys: pytest.CaptureFixture
) -> None:
    assert start("--library", "acme") == 0

    out = capsys.readouterr().out
    hub = root / "acme-hub"
    assert "acme-hub: made from the template" in out
    # Until it is pushed, the hub has no remote branch to compare with.
    assert "acme-hub: no upstream to compare with" in out
    assert git("status", "--porcelain", cwd=hub) == ""
    assert git("rev-list", "--count", "HEAD", cwd=hub) == "2"
    assert git("remote", "get-url", "origin", cwd=hub) == f"{GITLAB}/acme-hub.git"
    assert (
        git("remote", "get-url", "ws-template", cwd=hub)
        == "https://gitlab.example.org/ws-template.git"
    )
    workspace = manifest.load(hub)
    assert workspace.name == "acme" and workspace.library == "acme"
    assert workspace.zotero_root == "acme"
    assert manifest.template(hub) == "https://gitlab.example.org/agent-template.git"
    assert [repository.name for repository in workspace.repositories] == ["acme-hub"]
    assert (hub / "resources").resolve() == (root / "resources").resolve()


def test_init_fills_the_skeleton(root: Path) -> None:
    start()

    hub = root / "acme-hub"
    readme = (hub / "README.md").read_text()
    assert readme.startswith("# acme hub\n")
    assert f"git clone {GITLAB}/acme-hub.git" in readme
    # The template's manual follows the hub's own opening.
    assert "## The off-limits module" in readme
    agents = (hub / "AGENTS.md").read_text()
    assert agents.startswith("# acme hub\n") and "## Off-limits material" in agents
    assert (hub / "docs/CONTEXT.md").read_text().startswith("# acme workspace\n")
    skill = hub / "skills/ask-acme/SKILL.md"
    assert "name: ask-acme" in skill.read_text()
    assert (hub / ".claude/skills/ask-acme/SKILL.md").is_file()
    unfilled = re.compile(r"\{\{(name|hub|hub_url|gitlab|library|zotero_root|resources_env)\}\}")
    for name in git("ls-files", cwd=hub).splitlines():
        if not name.startswith(("skeleton/", "overlay/", "tests/")) and name.endswith(".md"):
            assert not unfilled.search((hub / name).read_text()), name


def test_init_writes_the_off_limits_module_everywhere(
    root: Path, tmp_path: Path
) -> None:
    config = tmp_path / "off-limits.yaml"
    config.write_text(
        yaml.safe_dump(
            {
                "off_limits": {
                    "paths": ["confidential/"],
                    "patterns": [{"pattern": r"\.msg\b", "what": "an e-mail"}],
                }
            }
        )
    )

    assert start(
        "--off-limits", str(config), "--deny-connector", "mcp__claude_ai_Gmail",
        "--off-limits-repo", "acme-confidential",
    ) == 0

    hub = root / "acme-hub"
    off_limits = manifest.load(hub).off_limits
    assert off_limits.paths == ("confidential/",)
    assert off_limits.deny_connectors == ("mcp__claude_ai_Gmail",)
    assert off_limits.repo == "acme-confidential"
    for folder in (root, hub):
        settings = json.loads((folder / ".claude/settings.json").read_text())
        assert "Read(**/confidential/**)" in settings["permissions"]["deny"]
        assert (folder / ".claude/hooks/guard_off_limits.py").is_file()
    assert git("status", "--porcelain", cwd=hub) == ""
    assert cli.main(["check", "--all"]) == 0


def test_init_refuses_an_existing_hub_and_a_bad_name(
    root: Path, capsys: pytest.CaptureFixture
) -> None:
    (root / "acme-hub").mkdir()

    assert start() == 2
    assert "acme-hub already exists" in capsys.readouterr().err
    assert cli.main(["init", "Acme Corp", "--no-input", "--gitlab", GITLAB]) == 2
    assert "lowercase" in capsys.readouterr().err


def test_init_without_a_group_fails_and_leaves_nothing(
    root: Path, capsys: pytest.CaptureFixture
) -> None:
    assert cli.main(["init", "acme", "--no-input"]) == 2

    assert "--gitlab" in capsys.readouterr().err
    assert os.listdir(root) == []

