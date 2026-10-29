"""`ws sync`, driven end to end in a temporary workspace (see `conftest.py`).

Each test runs `ws sync` from the hub and checks only the folders, output and exit code.
"""

from pathlib import Path

import pytest
from conftest import Workspace, git, make_remote


def test_sync_clones_missing_repositories_as_siblings_of_the_hub(
    workspace: Workspace,
) -> None:
    result = workspace.sync()

    assert result.returncode == 0, result.stdout + result.stderr
    for name in ("spimat", "spimat-framework"):
        assert (workspace.root / name / "README.md").read_text() == f"# {name}\n"
        assert f"{name}: cloned" in result.stdout


def snapshot(root: Path) -> dict[str, object]:
    """Every working-tree file with its modification time (the pool's included), and
    every repository's HEAD.

    Git's own bookkeeping (FETCH_HEAD, the index's stat cache) is left out: checking a
    repository against its remote rewrites it without changing anything the user sees.
    """
    state: dict[str, object] = {
        str(path.relative_to(root)): path.stat().st_mtime_ns
        for path in root.rglob("*")
        if ".git" not in path.relative_to(root).parts
    }
    for repository in root.iterdir():
        if not (repository / ".git").exists():
            continue
        state[f"{repository.name}@HEAD"] = git("rev-parse", "HEAD", cwd=repository)
    return state


def test_second_sync_changes_nothing(workspace: Workspace) -> None:
    workspace.sync()
    before = snapshot(workspace.root)

    result = workspace.sync()

    assert result.returncode == 0, result.stdout + result.stderr
    assert "cloned" not in result.stdout
    assert snapshot(workspace.root) == before


def test_dirty_repository_is_reported_and_sync_completes(workspace: Workspace) -> None:
    workspace.sync()
    (workspace.root / "spimat" / "README.md").write_text("edited\n")
    (workspace.root / "spimat" / "notes.txt").write_text("untracked\n")

    result = workspace.sync()

    assert result.returncode == 0, result.stdout + result.stderr
    assert "spimat: dirty (2 uncommitted)" in result.stdout
    assert (workspace.root / "spimat" / "README.md").read_text() == "edited\n"


def test_behind_repository_is_reported_and_left_where_it_is(
    workspace: Workspace,
) -> None:
    workspace.sync()
    head = git("rev-parse", "HEAD", cwd=workspace.root / "spimat")
    pusher = workspace.tmp / "pusher"
    git("clone", "--quiet", workspace.urls["spimat"], str(pusher), cwd=workspace.tmp)
    for message in ("First", "Second"):
        (pusher / f"{message}.md").write_text(message)
        git("add", ".", cwd=pusher)
        git("commit", "--quiet", "-m", message, cwd=pusher)
    git("push", "--quiet", cwd=pusher)

    result = workspace.sync()

    assert result.returncode == 0, result.stdout + result.stderr
    assert "spimat: behind (2 commits)" in result.stdout
    assert git("rev-parse", "HEAD", cwd=workspace.root / "spimat") == head


def test_branch_without_upstream_is_reported(workspace: Workspace) -> None:
    workspace.sync()
    git("checkout", "--quiet", "-b", "local-only", cwd=workspace.root / "spimat")

    result = workspace.sync()

    assert result.returncode == 0, result.stdout + result.stderr
    assert "spimat: no upstream to compare with" in result.stdout


def test_hub_folder_named_differently_from_the_manifest_clones_nothing(
    workspace: Workspace,
) -> None:
    workspace.hub = workspace.hub.rename(workspace.root / "hub")

    result = workspace.sync()

    assert result.returncode != 0
    assert "spimat-hub" in result.stderr
    assert sorted(path.name for path in workspace.root.iterdir()) == ["hub"]


def test_failed_clone_exits_non_zero_with_the_reason(workspace: Workspace) -> None:
    workspace.urls["spimat-framework"] = (workspace.remotes / "missing.git").as_uri()
    workspace.write_manifest()

    result = workspace.sync()

    assert result.returncode != 0
    line = next(
        line for line in result.stdout.splitlines() if "spimat-framework" in line
    )
    assert "FAILED" in line and "missing.git" in line
    assert "spimat: cloned" in result.stdout
    assert not (workspace.root / "spimat-framework").exists()


def test_folder_that_is_not_a_clone_exits_non_zero(workspace: Workspace) -> None:
    (workspace.root / "spimat").mkdir()

    result = workspace.sync()

    assert result.returncode != 0
    assert "spimat: FAILED: exists but is not a git repository" in result.stdout


def test_manifest_with_an_unknown_role_clones_nothing(workspace: Workspace) -> None:
    workspace.roles["spimat-framework"] = "experiment"
    workspace.write_manifest()

    result = workspace.sync()

    assert result.returncode != 0
    assert "spimat-framework has role 'experiment'" in result.stderr
    assert not (workspace.root / "spimat").exists()


def test_sync_gives_the_library_its_private_context_in_ignored_local_files(
    workspace: Workspace,
) -> None:
    result = workspace.sync()

    assert result.returncode == 0, result.stdout + result.stderr
    library = workspace.root / "spimat"
    local = (library / "CLAUDE.local.md").read_text()
    assert "@../spimat-hub/docs/library/CLAUDE.md" in local.splitlines()
    assert git("status", "--porcelain", cwd=library) == ""


def test_local_agent_file_written_by_hand_is_kept_and_reported(
    workspace: Workspace,
) -> None:
    workspace.sync()
    own = workspace.root / "spimat" / "CLAUDE.local.md"
    own.write_text("My own notes\n")

    result = workspace.sync()

    assert result.returncode == 0, result.stdout + result.stderr
    assert own.read_text() == "My own notes\n"
    line = next(
        line for line in result.stdout.splitlines() if line.startswith("spimat:")
    )
    assert "CLAUDE.local.md not written by ws, left as is" in line


def test_library_without_agent_guidance_gets_an_ignored_pointer_to_the_hub(
    workspace: Workspace,
) -> None:
    result = workspace.sync()

    assert result.returncode == 0, result.stdout + result.stderr
    library = workspace.root / "spimat"
    assert "../spimat-hub/docs/library/" in (library / "AGENTS.md").read_text()
    assert git("status", "--porcelain", cwd=library) == ""


def test_agent_guidance_the_library_commits_is_left_alone(
    workspace: Workspace,
) -> None:
    workspace.urls["spimat"] = make_remote(
        workspace.remotes / "committed",
        "spimat",
        {"AGENTS.md": "# Committed guidance\n"},
    )
    workspace.write_manifest()

    result = workspace.sync()

    assert result.returncode == 0, result.stdout + result.stderr
    library = workspace.root / "spimat"
    assert (library / "AGENTS.md").read_text() == "# Committed guidance\n"
    assert "AGENTS.md" not in result.stdout
    assert (library / "CLAUDE.local.md").exists()
    assert git("status", "--porcelain", cwd=library) == ""


def test_stale_local_agent_file_written_by_ws_is_rewritten(
    workspace: Workspace,
) -> None:
    workspace.sync()
    local = workspace.root / "spimat" / "CLAUDE.local.md"
    current = local.read_text()
    local.write_text(current.splitlines()[0] + "\n\n@../elsewhere/CLAUDE.md\n")

    result = workspace.sync()

    assert result.returncode == 0, result.stdout + result.stderr
    assert local.read_text() == current
    assert "CLAUDE.local.md" not in result.stdout


def test_sync_links_every_repository_to_the_pool_out_of_git(
    workspace: Workspace,
) -> None:
    result = workspace.sync()

    assert result.returncode == 0, result.stdout + result.stderr
    assert workspace.pool.is_dir()
    for name in workspace.roles:
        repository = workspace.root / name
        assert (repository / "resources").resolve() == workspace.pool.resolve()
        assert "resources" not in git("status", "--porcelain", cwd=repository)


def test_pool_location_comes_from_the_environment(
    workspace: Workspace, monkeypatch: pytest.MonkeyPatch
) -> None:
    elsewhere = workspace.tmp / "other-drive" / "pool"
    monkeypatch.setenv("SPIMAT_RESOURCES", str(elsewhere))

    result = workspace.sync()

    assert result.returncode == 0, result.stdout + result.stderr
    assert (workspace.hub / "resources").resolve() == elsewhere
    assert not workspace.pool.exists()


def test_moved_pool_is_relinked(
    workspace: Workspace, monkeypatch: pytest.MonkeyPatch
) -> None:
    workspace.sync()
    elsewhere = workspace.tmp / "other-drive" / "pool"
    monkeypatch.setenv("SPIMAT_RESOURCES", str(elsewhere))

    result = workspace.sync()

    assert result.returncode == 0, result.stdout + result.stderr
    assert (workspace.hub / "resources").resolve() == elsewhere
    assert f"spimat: resources relinked to {elsewhere}" in result.stdout


def test_resources_folder_in_the_way_is_kept_and_reported(
    workspace: Workspace,
) -> None:
    workspace.sync()
    study = workspace.root / "spimat-framework"
    (study / "resources").unlink()
    (study / "resources" / "papers").mkdir(parents=True)
    (study / "resources" / "papers" / "key.pdf").write_text("pdf")

    result = workspace.sync()

    assert result.returncode == 0, result.stdout + result.stderr
    assert (study / "resources" / "papers" / "key.pdf").read_text() == "pdf"
    line = next(
        line
        for line in result.stdout.splitlines()
        if line.startswith("spimat-framework:")
    )
    assert "resources/ is a folder, not a link to the pool" in line


def test_link_that_cannot_be_written_fails_that_repository_only(
    workspace: Workspace,
) -> None:
    workspace.sync()
    study = workspace.root / "spimat-framework"
    (study / "resources").unlink()
    study.chmod(0o555)
    try:
        result = workspace.sync()
    finally:
        study.chmod(0o755)

    assert result.returncode != 0
    assert "spimat-framework: FAILED: could not link resources" in result.stdout
    assert (workspace.hub / "resources").resolve() == workspace.pool.resolve()


def test_sync_mounts_each_study_s_notes_in_the_hub_out_of_git(
    workspace: Workspace,
) -> None:
    result = workspace.sync()

    assert result.returncode == 0, result.stdout + result.stderr
    mount = workspace.hub / "docs" / "studies" / "spimat-framework"
    assert (mount / "wiki" / "index.md").read_text() == "# Wiki\n"
    assert not (workspace.hub / "docs" / "studies" / "spimat").exists()
    assert "docs" not in git("status", "--porcelain", cwd=workspace.hub)


def test_study_without_notes_is_reported_and_not_mounted(
    workspace: Workspace,
) -> None:
    workspace.urls["spimat-framework"] = make_remote(
        workspace.remotes / "bare", "spimat-framework"
    )
    workspace.write_manifest()

    result = workspace.sync()

    assert result.returncode == 0, result.stdout + result.stderr
    assert "spimat-framework: cloned, no docs/ to mount" in result.stdout
    mount = workspace.hub / "docs" / "studies" / "spimat-framework"
    assert not mount.exists() and not mount.is_symlink()


def test_folder_in_the_mount_s_place_is_kept_and_reported(
    workspace: Workspace,
) -> None:
    mount = workspace.hub / "docs" / "studies" / "spimat-framework"
    mount.mkdir()
    (mount / "note.md").write_text("mine\n")

    result = workspace.sync()

    assert result.returncode == 0, result.stdout + result.stderr
    assert (mount / "note.md").read_text() == "mine\n"
    assert (
        "spimat-framework: cloned, docs/studies/spimat-framework is not a mount, left as is"
        in result.stdout
    )


def test_study_missing_from_the_hub_s_study_index_is_reported(
    workspace: Workspace,
) -> None:
    workspace.roles["spimat-mt2"] = "study"
    workspace.urls["spimat-mt2"] = make_remote(workspace.remotes, "spimat-mt2")
    workspace.write_manifest()

    result = workspace.sync()

    assert result.returncode == 0, result.stdout + result.stderr
    hub = next(l for l in result.stdout.splitlines() if l.startswith("spimat-hub:"))
    assert "spimat-mt2 missing from docs/studies/index.md" in hub
    assert "spimat-framework missing" not in hub


def test_study_named_only_in_prose_counts_as_missing_from_the_index(
    workspace: Workspace,
) -> None:
    (workspace.hub / "docs" / "studies" / "index.md").write_text(
        "- **other**: soon renamed spimat-framework\n"
    )

    result = workspace.sync()

    assert "spimat-framework missing from docs/studies/index.md" in result.stdout


def test_app_gets_the_pool_and_the_skills_but_no_mount_and_no_index_line(
    workspace: Workspace,
) -> None:
    workspace.roles["spimat-gui"] = "app"
    workspace.urls["spimat-gui"] = make_remote(
        workspace.remotes, "spimat-gui", {"docs/CONTEXT.md": "# GUI\n"}
    )
    workspace.write_manifest()

    result = workspace.sync()

    assert result.returncode == 0, result.stdout + result.stderr
    assert "spimat-gui: cloned" in result.stdout
    assert "spimat-gui missing" not in result.stdout
    app = workspace.root / "spimat-gui"
    assert (app / "resources").resolve() == workspace.pool.resolve()
    assert (app / ".claude" / "skills" / "publish-finding" / "SKILL.md").is_file()
    mount = workspace.hub / "docs" / "studies" / "spimat-gui"
    assert not mount.exists() and not mount.is_symlink()


@pytest.mark.parametrize("name", ["spimat", "spimat-hub", "spimat-framework"])
def test_sync_links_hub_skills_into_every_repository_out_of_git(
    workspace: Workspace, name: str
) -> None:
    result = workspace.sync()

    assert result.returncode == 0, result.stdout + result.stderr
    repository = workspace.root / name
    skill = repository / ".agents" / "skills" / "publish-finding"
    assert skill.resolve() == (workspace.hub / "skills" / "publish-finding").resolve()
    assert (repository / ".claude" / "skills" / "publish-finding" / "SKILL.md").is_file()
    assert git("status", "--porcelain", "--", ".agents", ".claude", cwd=repository) == ""


def test_study_skill_in_the_way_of_a_hub_skill_is_kept_and_reported(
    workspace: Workspace,
) -> None:
    workspace.urls["spimat-framework"] = make_remote(
        workspace.remotes / "own-skill",
        "spimat-framework",
        {".agents/skills/publish-finding/SKILL.md": "# Own\n"},
    )
    workspace.write_manifest()

    result = workspace.sync()

    assert result.returncode == 0, result.stdout + result.stderr
    study = workspace.root / "spimat-framework"
    assert (study / ".agents/skills/publish-finding/SKILL.md").read_text() == "# Own\n"
    assert (
        "spimat-framework: cloned, no docs/ to mount, "
        ".agents/skills/publish-finding is not the hub's skill, left as is"
        in result.stdout
    )


def test_claude_skills_folder_that_is_not_a_link_is_reported(
    workspace: Workspace,
) -> None:
    workspace.sync()
    study = workspace.root / "spimat-framework"
    (study / ".claude" / "skills").unlink()
    (study / ".claude" / "skills" / "copied").mkdir(parents=True)

    result = workspace.sync()

    assert result.returncode == 0, result.stdout + result.stderr
    line = next(
        line
        for line in result.stdout.splitlines()
        if line.startswith("spimat-framework:")
    )
    assert ".claude/skills is not a link to .agents/skills" in line
    assert (study / ".claude" / "skills" / "copied").is_dir()
