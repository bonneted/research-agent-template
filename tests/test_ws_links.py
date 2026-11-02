"""Links on both platforms: symbolic links here, and on Windows junctions for folders and
recorded copies for files. The Windows path runs here with the platform and the junction
primitives stood in for: a junction is played by an absolute symbolic link.
"""

import os
from pathlib import Path

import pytest
from conftest import Workspace, git, make_remote
from ws import links, manifest
from ws.sync import sync


@pytest.fixture
def windows(monkeypatch: pytest.MonkeyPatch) -> list[tuple[str, str]]:
    """Windows, as `links` sees it; returns the junctions made, as (target, link)."""
    made: list[tuple[str, str]] = []

    def create(target: str, link: str) -> None:
        assert os.path.isabs(target), "a junction holds an absolute path"
        made.append((target, link))
        os.symlink(target, link, target_is_directory=True)

    monkeypatch.setattr(links, "WINDOWS", True)
    monkeypatch.setattr(links, "_create_junction", create)
    monkeypatch.setattr(links, "_is_junction", lambda path: Path(path).is_symlink())
    monkeypatch.setattr(links, "_remove_junction", os.unlink)
    return made


def test_folder_link_is_relative_on_linux(tmp_path: Path) -> None:
    (tmp_path / "target").mkdir()
    link = tmp_path / "a" / "link"

    assert links.directory(link, tmp_path / "target") == links.MADE
    assert os.readlink(link) == "../target"
    assert links.directory(link, tmp_path / "target") == links.SAME


def test_folder_link_is_an_absolute_junction_on_windows(
    tmp_path: Path, windows: list
) -> None:
    (tmp_path / "target").mkdir()
    (tmp_path / "moved").mkdir()
    link = tmp_path / "a" / "link"

    assert links.directory(link, tmp_path / "target") == links.MADE
    assert windows == [(str(tmp_path / "target"), str(link))]
    assert links.directory(link, tmp_path / "target") == links.SAME
    assert links.directory(link, tmp_path / "moved") == links.MOVED
    assert link.resolve() == tmp_path / "moved"


def test_folder_in_a_links_place_is_kept_on_both(tmp_path: Path, windows: list) -> None:
    (tmp_path / "link").mkdir()

    assert links.directory(tmp_path / "link", tmp_path) == links.BLOCKED
    assert windows == []


def test_file_link_is_a_symbolic_link_on_linux(tmp_path: Path) -> None:
    target = tmp_path / "hub" / "hook.py"
    target.parent.mkdir()
    target.write_text("v1\n")
    link = tmp_path / "repo" / "hook.py"

    assert links.file(link, target) == []
    assert link.is_symlink() and link.read_text() == "v1\n"
    assert links.file_drift(link, target) is None


def test_file_link_is_a_recorded_copy_on_windows(tmp_path: Path, windows: list) -> None:
    target = tmp_path / "hub" / "hook.py"
    target.parent.mkdir()
    target.write_text("v1\n")
    link = tmp_path / "repo" / "hook.py"

    assert links.file(link, target) == []
    assert not link.is_symlink() and link.read_text() == "v1\n"
    assert (link.parent / links.COPIES).is_file()

    # The hub's file moves on: an untouched copy follows it.
    target.write_text("v2\n")
    assert links.file_drift(link, target) == f"hook.py differs from {target}"
    assert links.file(link, target) == []
    assert link.read_text() == "v2\n"

    # A copy edited by hand is reported, never overwritten.
    link.write_text("mine\n")
    target.write_text("v3\n")
    [note] = links.file(link, target)
    assert "edited since ws copied it" in note
    assert link.read_text() == "mine\n"


def test_sync_on_windows_links_with_junctions_and_absolute_paths(
    workspace: Workspace, windows: list
) -> None:
    lines, ok = sync(workspace.root, manifest.load(workspace.hub))

    assert ok, lines
    study = workspace.root / "demo-framework"
    assert os.readlink(study / "resources") == str(workspace.pool)
    assert (study / ".claude/skills/publish-finding/SKILL.md").is_file()
    mount = workspace.hub / "docs/studies/demo-framework"
    assert os.path.isabs(os.readlink(mount))
    assert all(os.path.isabs(target) for target, _ in windows)


def test_sync_on_windows_replaces_a_skills_link_checked_out_as_text(
    workspace: Workspace, windows: list
) -> None:
    # Without symbolic links, git checks a committed link out as a file holding its target.
    workspace.urls["demo-framework"] = make_remote(
        workspace.remotes / "text-link",
        "demo-framework",
        {".claude/skills": "../.agents/skills", "docs/wiki/index.md": "# Wiki\n"},
    )
    workspace.write_manifest()

    lines, ok = sync(workspace.root, manifest.load(workspace.hub))

    assert ok, lines
    study = workspace.root / "demo-framework"
    assert (study / ".claude/skills").is_symlink()
    assert (study / ".claude/skills/publish-finding/SKILL.md").is_file()
    assert git("status", "--porcelain", cwd=study) == ""
