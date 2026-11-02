"""`ws spawn`, driven end to end in a temporary workspace (see `conftest.py`).

Each test spawns a throwaway study from the stand-in template and the hub's overlay, and
checks only the study's files, the hub's registers, the output and the exit code.
"""

import os
import re
import subprocess
import sys
import tomllib
from pathlib import Path

import pytest
import ws
import yaml
from conftest import Workspace, git
from fakes import Web
from ws.spawn import spawn

STUDY = "demo-mt2"


@pytest.fixture
def spawned(workspace: Workspace) -> Path:
    """The workspace, synced, with the study `demo-mt2` spawned in it."""
    workspace.sync()
    result = workspace.spawn("mt2")
    assert result.returncode == 0, result.stdout + result.stderr
    return workspace.root / STUDY


def test_spawned_study_has_the_overlay_layout(spawned: Path) -> None:
    for path in (
        "PLAN.md",
        "study/__init__.py",
        "phases",
        "docs/wiki/phases",
        "docs/wiki/index.md",
        "tests/test_import.py",
    ):
        assert (spawned / path).exists(), path
    plan = (spawned / "PLAN.md").read_text()
    assert "## Claim type" in plan and "## Protocol" in plan
    assert not (spawned / "src").exists()
    # The template's own resources folder gives way to the link to the pool.
    assert (spawned / "resources").is_symlink()
    assert git("ls-files", "resources", cwd=spawned) == ""


def test_spawned_study_carries_the_default_study_rules_and_the_hub_pointer(
    workspace: Workspace, spawned: Path
) -> None:
    guidance = (spawned / "AGENTS.md").read_text()
    assert "1. Each phase is **explore** or **confirm**." in guidance
    assert "10. **Units**" in guidance
    assert "prior-work check" in guidance.lower()
    assert "ask-demo" in guidance
    assert f"git clone {workspace.urls['demo-hub']} ../demo-hub" in guidance


def test_spawned_study_says_study_where_the_template_says_project(
    spawned: Path,
) -> None:
    for name in git("ls-files", "--", "*.md", cwd=spawned).splitlines():
        text = (spawned / name).read_text()
        assert not re.search(r"\bprojects?\b", text, re.IGNORECASE), name
    reading = (spawned / "docs/wiki/reading-list.md").read_text()
    assert reading == "Needed by the study, for Study work and studies.\n"
    # Code and configuration keep the word: there it can be a key or part of a URL.
    zotero = (spawned / "tools/zotero.py").read_text()
    assert zotero == 'API = "https://api.example.org/projects/"\n'


def test_spawned_study_has_the_rule_packs_and_the_protocol_freeze(
    workspace: Workspace, spawned: Path
) -> None:
    for pack in ("ml-training", "fe-simulation", "uq-reliability", "literature-check"):
        assert (spawned / "rules" / f"{pack}.md").read_text() == (
            workspace.hub / "rules" / f"{pack}.md"
        ).read_text()
    assert "## Rule packs" in (spawned / "PLAN.md").read_text()
    freeze = (spawned / "study/protocol.py").read_text()
    assert freeze == (Path(ws.__file__).parent / "protocol.py").read_text()


def test_spawned_study_leaves_fetching_to_the_hub(
    workspace: Workspace, spawned: Path
) -> None:
    for path in (
        "tools/fetch",
        "tests/test_fetch.py",
        "tests/test_retrieve.py",
        "tests/conftest.py",
        "tests/test_refs.py",
        "uv.lock",
    ):
        assert not (spawned / path).exists(), path
    skill = (spawned / ".agents/skills/digest-source/SKILL.md").read_text()
    assert "Missing: run `uv run ws fetch` in the hub.\n" in skill
    assert (
        f"`uv run --directory ../demo-hub ws refs add --repo {STUDY} <DOI>`, then "
        f"`uv run --directory ../demo-hub ws refs pull --repo {STUDY}`."
    ) in skill
    for name in (
        "resources.yaml",
        "references.bib",
        *git("ls-files", "--", "*.md", cwd=spawned).split(),
    ):
        text = (spawned / name).read_text()
        assert "uv run fetch" not in text and "resources/README.md" not in text, name
    assert yaml.safe_load((spawned / "resources.yaml").read_text()) == {
        "code": [],
        "data": [],
    }


def test_spawned_study_is_one_clean_commit_on_the_template_kept_as_remote(
    workspace: Workspace, spawned: Path
) -> None:
    assert git("status", "--porcelain", cwd=spawned) == ""
    assert git("remote", "get-url", "template", cwd=spawned) == workspace.template
    template_head = git("rev-parse", "template/main", cwd=spawned)
    assert git("rev-parse", "HEAD~1", cwd=spawned) == template_head
    origin = git("remote", "get-url", "origin", cwd=spawned)
    assert origin == workspace.urls["demo-hub"].replace("demo-hub", STUDY)


def test_spawned_study_pins_the_library_at_its_default_branch_commit(
    workspace: Workspace, spawned: Path
) -> None:
    library_head = git("ls-remote", workspace.urls["demo"], "HEAD", cwd=spawned)
    pyproject = tomllib.loads((spawned / "pyproject.toml").read_text())

    assert pyproject["project"]["name"] == STUDY
    assert "demo" in pyproject["project"]["dependencies"]
    assert pyproject["tool"]["uv"]["sources"]["demo"] == {
        "git": workspace.urls["demo"],
        "rev": library_head.split()[0],
    }
    assert 'LIBRARY = "demo"' in (spawned / "study/stamp.py").read_text()


def test_spawned_study_runs_on_the_librarys_python(workspace: Workspace) -> None:
    # The library's pinned commit says which Python it needs; the study follows it.
    library = workspace.root / "demo"
    workspace.sync()
    (library / "pyproject.toml").write_text(
        '[project]\nname = "demo"\nrequires-python = ">=3.13,<3.14"\n'
    )
    git("add", "pyproject.toml", cwd=library)
    git("commit", "--quiet", "-m", "Pin the Python", cwd=library)
    git("push", "--quiet", "origin", "HEAD:main", cwd=library)

    result = workspace.spawn("mt2")

    assert result.returncode == 0, result.stdout + result.stderr
    pyproject = tomllib.loads((workspace.root / STUDY / "pyproject.toml").read_text())
    assert pyproject["project"]["requires-python"] == ">=3.13,<3.14"


def test_a_study_without_the_librarys_word_on_python_keeps_the_overlays(
    spawned: Path,
) -> None:
    pyproject = tomllib.loads((spawned / "pyproject.toml").read_text())
    assert pyproject["project"]["requires-python"] == ">=3.11"


def test_a_workspace_without_a_library_spawns_studies_with_no_pin(
    workspace: Workspace,
) -> None:
    del workspace.roles["demo"]
    workspace.write_manifest()

    result = workspace.spawn("mt2")

    assert result.returncode == 0, result.stdout + result.stderr
    assert "no library to pin" in result.stdout
    pyproject = tomllib.loads((workspace.root / STUDY / "pyproject.toml").read_text())
    assert pyproject["project"]["dependencies"] == ["pyyaml"]
    assert "uv" not in pyproject["tool"]


def test_a_library_named_but_not_listed_yet_refuses_to_spawn(
    workspace: Workspace,
) -> None:
    del workspace.roles["demo"]
    workspace.settings["library"] = "demo"
    workspace.write_manifest()

    result = workspace.spawn("mt2")

    assert result.returncode != 0
    assert "the library demo is not in workspace.yaml yet" in result.stderr
    assert not (workspace.root / STUDY).exists()


def test_spawned_study_is_registered_in_the_manifest_and_the_study_index(
    workspace: Workspace, spawned: Path
) -> None:
    manifest = yaml.safe_load((workspace.hub / "workspace.yaml").read_text())
    assert {
        "name": STUDY,
        "url": git("remote", "get-url", "origin", cwd=spawned),
        "role": "study",
    } in manifest["repositories"]
    assert manifest["template"] == workspace.template
    index = (workspace.hub / "docs/studies/index.md").read_text()
    assert f"- **{STUDY}**" in index

    result = workspace.sync()

    assert result.returncode == 0, result.stdout + result.stderr
    assert "missing from" not in result.stdout


def test_spawn_syncs_the_workspace(workspace: Workspace) -> None:
    result = workspace.spawn("mt2")

    assert result.returncode == 0, result.stdout + result.stderr
    assert "demo-framework: cloned" in result.stdout
    mount = workspace.hub / "docs/studies" / STUDY
    assert (mount / "wiki/index.md").is_file()


def test_hub_skills_are_available_in_the_spawned_study(
    workspace: Workspace, spawned: Path
) -> None:
    hub_skill = workspace.hub / "skills/publish-finding"
    assert (spawned / ".agents/skills/publish-finding").resolve() == hub_skill.resolve()
    # Claude Code sees the template's skills and the hub's through one link, not a copy.
    claude = spawned / ".claude/skills"
    assert claude.is_symlink()
    assert claude.resolve() == (spawned / ".agents/skills").resolve()
    assert (claude / "digest-source/SKILL.md").is_file()
    assert (claude / "publish-finding/SKILL.md").read_text() == "# Publish a finding\n"
    assert git("status", "--porcelain", cwd=spawned) == ""


def test_run_folder_is_outside_git_and_configurable(
    workspace: Workspace, spawned: Path
) -> None:
    def runs(environment: dict[str, str]) -> Path:
        output = subprocess.run(
            [sys.executable, "-c", "from study.paths import RUNS; print(RUNS)"],
            cwd=spawned,
            env={**os.environ, **environment},
            capture_output=True,
            text=True,
            check=True,
        ).stdout
        return Path(output.strip())

    assert runs({}) == spawned / "runs"
    (spawned / "runs" / "01-screen").mkdir(parents=True)
    assert git("status", "--porcelain", cwd=spawned) == ""
    elsewhere = workspace.tmp / "other-drive"
    assert runs({"DEMO_MT2_RUNS": str(elsewhere)}) == elsewhere


def test_spawn_copies_only_the_overlay_files_git_tracks(
    workspace: Workspace,
) -> None:
    # Running the overlay's tests in place leaves bytecode there, which git ignores.
    cache = workspace.hub / "overlay/tests/__pycache__/test_stamp.cpython-312.pyc"
    cache.parent.mkdir(parents=True)
    cache.write_bytes(b"\x00\xff\xfe compiled")
    (workspace.hub / "overlay/scratch.md").write_text("# {{study}} notes\n")

    result = workspace.spawn("mt2")

    assert result.returncode == 0, result.stdout + result.stderr
    study = workspace.root / STUDY
    assert not (study / "tests/__pycache__").exists()
    assert not (study / "scratch.md").exists()
    assert "{{" not in (study / "AGENTS.md").read_text()


def test_spawning_a_study_already_in_the_workspace_changes_nothing(
    workspace: Workspace,
) -> None:
    manifest = (workspace.hub / "workspace.yaml").read_text()

    result = workspace.spawn("framework")

    assert result.returncode != 0
    assert "demo-framework is already in workspace.yaml" in result.stderr
    assert (workspace.hub / "workspace.yaml").read_text() == manifest
    assert not (workspace.root / "demo-framework").exists()


def test_spawning_over_an_existing_folder_changes_nothing(
    workspace: Workspace,
) -> None:
    (workspace.root / STUDY).mkdir()
    manifest = (workspace.hub / "workspace.yaml").read_text()

    result = workspace.spawn("mt2")

    assert result.returncode != 0
    assert f"{STUDY} already exists" in result.stderr
    assert (workspace.hub / "workspace.yaml").read_text() == manifest
    assert list((workspace.root / STUDY).iterdir()) == []


def test_topic_that_is_not_a_slug_is_refused(workspace: Workspace) -> None:
    result = workspace.spawn("MT 2")

    assert result.returncode != 0
    assert "lowercase" in result.stderr
    assert sorted(path.name for path in workspace.root.iterdir()) == ["demo-hub"]


def test_unreachable_template_leaves_no_study_behind(workspace: Workspace) -> None:
    workspace.template = (workspace.remotes / "missing.git").as_uri()
    workspace.write_manifest()
    manifest = (workspace.hub / "workspace.yaml").read_text()

    result = workspace.spawn("mt2")

    assert result.returncode != 0
    assert "missing.git" in result.stderr
    assert not (workspace.root / STUDY).exists()
    assert (workspace.hub / "workspace.yaml").read_text() == manifest


def test_spawned_study_passes_its_own_tests(spawned: Path) -> None:
    # The overlay's run-stamp tests stand a fake library in for the library.
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", "tests"],
        check=False,
        cwd=spawned,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stdout + result.stderr


def test_spawn_creates_the_study_collection_in_zotero(workspace: Workspace) -> None:
    web = Web()
    zotero_root = web.collection("demo")

    lines, ok = spawn(workspace.hub, "mt2", web.library())

    assert ok, lines
    [created] = [
        collection["data"]
        for collection in web.collections.values()
        if collection["data"]["name"] == STUDY
    ]
    assert created["parentCollection"] == zotero_root
    assert f"{STUDY}: Zotero collection demo/{STUDY} created" in lines


def test_spawn_creates_the_workspace_collection_if_needed(workspace: Workspace) -> None:
    web = Web()

    spawn(workspace.hub, "mt2", web.library())

    assert web.library().collection(["demo", STUDY]) is not None


@pytest.mark.parametrize("writable", [False, None])
def test_spawn_leaves_the_collection_to_the_researcher_when_it_cannot(
    workspace: Workspace, writable: bool | None
) -> None:
    web = Web()
    web.writable = bool(writable)
    library = web.library() if writable is not None else None

    lines, ok = spawn(workspace.hub, "mt2", library)

    assert ok, lines
    assert web.collections == {}
    assert any(
        line.startswith(f"{STUDY}: create the Zotero collection demo/{STUDY}")
        for line in lines
    ), lines
