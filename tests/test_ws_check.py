"""`ws check`, driven end to end in a temporary workspace (see `conftest.py`): findings
against their format, evidence permalinks against the clones, citations, phases and
their protocol freeze, rule packs and conda environments.
"""

import datetime
import json
from pathlib import Path

import pytest
from conftest import Workspace, git
from ws import protocol

STUDY_PLAN = """# Plan

## Rule packs

- fe-simulation

## Protocol

### 01-burst

Three meshes.

## Deviations

| Date | Phase | Deviation | Decided | Why |
|---|---|---|---|---|
"""


def commit(repository: Path, files: dict[str, str], message: str = "Work") -> str:
    for name, text in files.items():
        (repository / name).parent.mkdir(parents=True, exist_ok=True)
        (repository / name).write_text(text)
    git("add", "--all", cwd=repository)
    git("commit", "--quiet", "-m", message, cwd=repository)
    return git("rev-parse", "HEAD", cwd=repository)


@pytest.fixture
def checked(workspace: Workspace) -> Workspace:
    """The workspace synced, its study with a confirm phase frozen and committed."""
    result = workspace.sync()
    assert result.returncode == 0, result.stdout + result.stderr
    study = workspace.root / "demo-framework"
    commit(
        study,
        {
            "PLAN.md": STUDY_PLAN,
            "rules/fe-simulation.md": "# fe-simulation\n",
            "phases/01-burst/config.yaml": "type: confirm\n",
            "docs/wiki/phases/01-burst.md": "# 01-burst\n\nBurst at 70 MPa [@smith2020, p. 4].\n",
            "references.bib": "@article{smith2020,\n  title = {Burst},\n}\n",
        },
    )
    protocol.freeze(
        study / "phases/01-burst", study / "PLAN.md", datetime.date(2026, 10, 1)
    )
    workspace.sha = commit(study, {}, "Freeze 01-burst")
    commit(workspace.hub, {"workspace.yaml": (workspace.hub / "workspace.yaml").read_text()})
    return workspace


def permalink(workspace: Workspace, path: str, sha: str | None = None) -> str:
    url = workspace.urls["demo-framework"].removesuffix(".git")
    return f"{url}/-/blob/{sha or workspace.sha}/{path}"


def finding(workspace: Workspace, front: dict, name: str = "burst.md") -> None:
    text = "---\n" + json.dumps(front) + "\n---\n\n# Burst holds\n"
    (workspace.hub / "docs/findings").mkdir(parents=True, exist_ok=True)
    (workspace.hub / "docs/findings" / name).write_text(text)


def confirmed(workspace: Workspace, **changes: object) -> dict:
    return {
        "status": "confirmed",
        "evidence": [
            {
                "kind": "run",
                "phase": "confirm",
                "note": permalink(workspace, "docs/wiki/phases/01-burst.md"),
                "stamp": "01-burst/20261001T120000-seed1",
            }
        ],
        "reviewed": {"date": "2026-10-02", "verdict": "upheld", "notes": "holds"},
        **changes,
    }


def check(workspace: Workspace, *arguments: str):
    return workspace.run("check", *arguments)


def test_a_clean_workspace_checks_ok(checked: Workspace) -> None:
    finding(checked, confirmed(checked))

    result = check(checked, "--all")

    assert result.returncode == 0, result.stdout + result.stderr
    assert "demo-hub: ok" in result.stdout
    assert "demo-framework: ok" in result.stdout


def test_check_runs_on_the_repository_it_is_run_from(checked: Workspace) -> None:
    result = checked.run_in(checked.root / "demo-framework" / "docs", "check")

    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout.strip() == "demo-framework: ok"


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"status": "proven"}, "status is 'proven'"),
        ({"reviewed": None}, "confirmed needs a review-finding verdict of upheld"),
        (
            {"reviewed": {"date": "2026-10-02", "verdict": "narrowed"}},
            "confirmed needs a review-finding verdict of upheld",
        ),
        ({"evidence": ["https://example.org/x"]}, "each evidence item needs a kind"),
        (
            {"evidence": [{"kind": "run", "phase": "confirm", "note": "x"}]},
            "run evidence needs stamp",
        ),
        (
            {"evidence": [{"kind": "legacy", "commit": "https://h/g/r/-/commit/abc1234", "note": "https://h/g/r/-/blob/abc1234/n.md"}]},
            "confirmed needs evidence from a confirm phase",
        ),
        (
            {"status": "superseded", "reviewed": None},
            "a superseded finding names its superseded_by",
        ),
        (
            {"evidence": [{"kind": "source", "citekey": "nobody2020", "page": 3}]},
            "nobody2020 is in no references.bib",
        ),
    ],
)
def test_a_finding_against_its_format_fails(
    checked: Workspace, changes: dict, message: str
) -> None:
    finding(checked, confirmed(checked, **changes))

    result = check(checked, "--repo", "demo-hub")

    assert result.returncode == 1
    assert message in result.stdout


def test_a_permalink_to_a_commit_the_clone_lacks_fails(checked: Workspace) -> None:
    missing = "0" * 40
    front = confirmed(checked)
    front["evidence"][0]["note"] = permalink(
        checked, "docs/wiki/phases/01-burst.md", missing
    )
    finding(checked, front)

    result = check(checked, "--repo", "demo-hub")

    assert result.returncode == 1
    assert f"{missing[:12]}:docs/wiki/phases/01-burst.md is not in the clone" in result.stdout


def test_evidence_claiming_a_confirm_phase_from_an_explore_one_fails(
    checked: Workspace,
) -> None:
    study = checked.root / "demo-framework"
    sha = commit(
        study,
        {
            "phases/02-screen/config.yaml": "type: explore\n",
            "docs/wiki/phases/02-screen.md": "# 02-screen\n",
        },
    )
    front = confirmed(checked)
    front["evidence"][0]["note"] = permalink(checked, "docs/wiki/phases/02-screen.md", sha)
    finding(checked, front)

    result = check(checked, "--repo", "demo-hub")

    assert result.returncode == 1
    assert "says phase confirm, but phase 02-screen is explore" in result.stdout


def test_a_citation_missing_from_the_bibliography_fails(checked: Workspace) -> None:
    note = checked.root / "demo-framework/docs/wiki/concepts/gci.md"
    note.parent.mkdir(parents=True, exist_ok=True)
    note.write_text("The GCI [@roache1994; @smith2020, p. 2].\n\n`[@not_a_cite]`\n")

    result = check(checked, "--repo", "demo-framework")

    assert result.returncode == 1
    assert "docs/wiki/concepts/gci.md:1: [@roache1994] is not in references.bib" in result.stdout
    assert "not_a_cite" not in result.stdout


def test_a_number_beside_a_citation_without_a_page_is_a_warning(
    checked: Workspace,
) -> None:
    note = checked.root / "demo-framework/docs/wiki/concepts/burst.md"
    note.parent.mkdir(parents=True, exist_ok=True)
    note.write_text("Smith (2020) burst the liner at 68.5 MPa [@smith2020].\n")

    result = check(checked, "--repo", "demo-framework")

    assert result.returncode == 0
    assert "WARNING: docs/wiki/concepts/burst.md:1: 68.5 beside [@smith2020]" in result.stdout


def test_a_phase_without_its_note_or_type_fails(checked: Workspace) -> None:
    study = checked.root / "demo-framework"
    (study / "phases/02-mesh").mkdir()
    (study / "phases/02-mesh/config.yaml").write_text("steps: 3\n")

    result = check(checked, "--repo", "demo-framework")

    assert result.returncode == 1
    assert "phases/02-mesh has no note docs/wiki/phases/02-mesh.md" in result.stdout
    assert "phases/02-mesh/config.yaml declares no type" in result.stdout


def test_a_confirm_phase_not_frozen_is_a_warning(checked: Workspace) -> None:
    study = checked.root / "demo-framework"
    (study / "phases/02-mesh").mkdir()
    (study / "phases/02-mesh/config.yaml").write_text("type: confirm\n")
    (study / "docs/wiki/phases/02-mesh.md").write_text("# 02-mesh\n")

    result = check(checked, "--repo", "demo-framework")

    assert result.returncode == 0
    assert "WARNING: phases/02-mesh: confirm phase not frozen" in result.stdout


def test_a_protocol_changed_after_its_freeze_fails(checked: Workspace) -> None:
    plan = checked.root / "demo-framework/PLAN.md"
    plan.write_text(plan.read_text().replace("Three meshes", "Two meshes"))

    result = check(checked, "--repo", "demo-framework")

    assert result.returncode == 1
    assert "phases/01-burst: the protocol changed since it was frozen on 2026-10-01" in result.stdout


def test_a_refreeze_without_a_logged_deviation_fails(checked: Workspace) -> None:
    study = checked.root / "demo-framework"
    plan = study / "PLAN.md"
    plan.write_text(plan.read_text().replace("Three meshes", "Two meshes"))
    config = study / "phases/01-burst/config.yaml"
    config.write_text(
        "type: confirm\nprotocol:\n"
        f"  hash: {protocol.digest(plan.read_text(), '01-burst')}\n"
        "  frozen: '2026-10-03'\n"
        "  previous:\n  - hash: abc\n    frozen: '2026-10-01'\n"
    )

    result = check(checked, "--repo", "demo-framework")

    assert result.returncode == 1
    assert "refrozen with no deviation logged since 2026-10-01" in result.stdout


def test_a_selected_rule_pack_the_study_lacks_fails(checked: Workspace) -> None:
    plan = checked.root / "demo-framework/PLAN.md"
    plan.write_text(plan.read_text().replace("- fe-simulation", "- fe-simulation\n- uq-reliability"))

    result = check(checked, "--repo", "demo-framework")

    assert result.returncode == 1
    assert "selects the rule pack uq-reliability, not in rules/" in result.stdout


def fake_conda(workspace: Workspace, monkeypatch: pytest.MonkeyPatch, version: str) -> None:
    """A conda that has the environment `fem`, with gmsh at `version`."""
    conda = workspace.tmp / "conda"
    envs = json.dumps({"envs": ["/opt/conda", "/opt/conda/envs/fem"]})
    packages = json.dumps([{"name": "gmsh", "version": version}])
    conda.write_text(
        "#!/bin/sh\n"
        f"if [ \"$1\" = env ]; then echo '{envs}'; else echo '{packages}'; fi\n"
    )
    conda.chmod(0o755)
    monkeypatch.setenv("CONDA_EXE", str(conda))


def test_a_conda_environment_drifted_from_its_pins_fails(
    checked: Workspace, monkeypatch: pytest.MonkeyPatch
) -> None:
    study = checked.root / "demo-framework"
    (study / "environments").mkdir()
    (study / "environments/fem.yml").write_text(
        "name: fem\ndependencies:\n  - conda-forge::gmsh=4.11.1=h1\n"
    )
    fake_conda(checked, monkeypatch, "4.13.0")

    result = check(checked, "--repo", "demo-framework")

    assert result.returncode == 1
    assert "conda environment fem drifted from environments/fem.yml: gmsh 4.13.0 (pinned 4.11.1)" in result.stdout

    fake_conda(checked, monkeypatch, "4.11.1")
    assert check(checked, "--repo", "demo-framework").returncode == 0


def test_check_outside_any_repository_asks_for_one(checked: Workspace) -> None:
    result = checked.run_in(checked.root, "check")

    assert result.returncode == 2
    assert "give --repo" in result.stderr


def test_ws_freeze_records_the_protocol(checked: Workspace) -> None:
    study = checked.root / "demo-framework"
    plan = study / "PLAN.md"
    plan.write_text(plan.read_text().replace("## Deviations", "### 02-mesh\n\nFour meshes.\n\n## Deviations"))
    (study / "phases/02-mesh").mkdir()
    (study / "phases/02-mesh/config.yaml").write_text("type: confirm\n")

    result = checked.run_in(study, "freeze", "02-mesh")

    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout.startswith("demo-framework: 02-mesh: protocol frozen at ")
    assert "hash:" in (study / "phases/02-mesh/config.yaml").read_text()
