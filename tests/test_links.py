"""Links on both platforms: symbolic links here, and on Windows junctions for folders and
recorded copies for files. The Windows path runs here with the platform and the junction
primitives stood in for: a junction is played by an absolute symbolic link.
"""

import os
from pathlib import Path

import pytest
from rkt import links


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
