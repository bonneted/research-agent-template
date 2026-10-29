"""The manifest's `workspace` block: every workspace-specific name comes from it."""

import shutil

import pytest
from conftest import Workspace
from ws import manifest


def load(workspace: Workspace) -> manifest.Workspace:
    workspace.write_manifest()
    return manifest.load(workspace.hub)


def test_names_derive_from_the_workspace_name(workspace: Workspace) -> None:
    workspace.settings = {"name": "copv-x", "gitlab": "https://gitlab.example.org/g/copv/"}

    loaded = load(workspace)

    assert loaded.variable("RESOURCES") == "COPV_X_RESOURCES"
    assert loaded.zotero_root == "copv-x"
    assert loaded.rule_packs_dir == "rules"
    assert loaded.url("copv-x-burst") == "https://gitlab.example.org/g/copv/copv-x-burst.git"
    assert loaded.library == "demo"


def test_without_a_group_a_repository_lives_beside_the_hub(workspace: Workspace) -> None:
    loaded = load(workspace)

    assert loaded.url("demo-mt2") == workspace.urls["demo-hub"].replace("demo-hub", "demo-mt2")


@pytest.mark.parametrize(
    ("settings", "message"),
    [
        (None, "expected a 'workspace' block with a name"),
        ({"name": "Copv"}, "is not lowercase letters"),
        ({"name": "demo", "colour": "red"}, "unknown keys: colour"),
        ({"name": "demo", "stamp_extras": "nocolon"}, "is not `module:function`"),
        ({"name": "demo", "library": "other"}, "workspace.library is other, but demo has role library"),
        ({"name": "demo", "off_limits": {"patterns": ["("]}}, r"off_limits pattern '\('"),
        ({"name": "demo", "off_limits": {"paths": "confidential/"}}, "off_limits.paths must be a list"),
        ({"name": "demo", "off_limits": {"repo": "demo-framework"}}, "must have role off-limits"),
    ],
)
def test_a_malformed_workspace_block_is_refused(
    workspace: Workspace, settings: dict | None, message: str
) -> None:
    workspace.settings = settings
    workspace.write_manifest()
    if settings is None:
        text = (workspace.hub / "workspace.yaml").read_text()
        (workspace.hub / "workspace.yaml").write_text(text.replace("workspace: null\n", ""))

    with pytest.raises(manifest.ManifestError, match=message):
        manifest.load(workspace.hub)


def test_a_library_or_off_limits_repository_may_be_listed_later(
    workspace: Workspace,
) -> None:
    del workspace.roles["demo"]
    workspace.settings = {
        "name": "demo",
        "library": "demo",
        "off_limits": {"paths": ["confidential/"], "repo": "demo-confidential"},
    }

    loaded = load(workspace)

    assert loaded.library == "demo" and loaded.repository("demo") is None
    assert loaded.off_limits.repo == "demo-confidential"
    result = workspace.sync()
    assert result.returncode == 0, result.stdout + result.stderr


def test_a_private_library_gets_no_pointer_to_the_hub(workspace: Workspace) -> None:
    shutil.rmtree(workspace.hub / "docs/library")

    result = workspace.sync()

    assert result.returncode == 0, result.stdout + result.stderr
    assert not (workspace.root / "demo/CLAUDE.local.md").exists()
    assert not (workspace.root / "demo/AGENTS.md").exists()
