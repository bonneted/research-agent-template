"""Run stamping: every run records what it takes to reproduce it (core rule 3).

Each test makes a throwaway study repository with one phase, and stands a fake library
in for the workspace's, so the stamp's report of the install can be checked either way.
"""

import datetime
import json
import subprocess
import sys
import types
from pathlib import Path

import pytest
from study import protocol, stamp


def git(*args: str, cwd: Path) -> str:
    return subprocess.run(
        ["git", *args], cwd=cwd, check=True, capture_output=True, text=True
    ).stdout.strip()


def library(monkeypatch: pytest.MonkeyPatch, report: dict) -> None:
    fake = types.ModuleType("fakelib")
    fake.installed_from = lambda: report
    monkeypatch.setitem(sys.modules, "fakelib", fake)
    monkeypatch.setattr(stamp, "LIBRARY", "fakelib")
    monkeypatch.setattr(stamp, "STAMP_EXTRAS", "")


PINNED = {
    "version": "0.1.0",
    "editable": False,
    "url": "https://gitlab.example.org/fakelib.git",
    "commit": "79ab5939" + "0" * 32,
}

PLAN = """# Plan

## Protocol

Shared: the primary metric is the burst pressure.

### 01-screen

Three liners, one seed each.

### 02-other

Not this phase's.

## Deviations

| Date | Phase | Deviation | Decided before or after launch | Why |
|---|---|---|---|---|
"""


def study(tmp_path: Path, kind: str = "explore", frozen: bool = True) -> Path:
    root = tmp_path / "study"
    phase = root / "phases" / "01-screen"
    phase.mkdir(parents=True)
    (phase / "config.yaml").write_text(f"type: {kind}\nsteps: 10\n")
    (root / "PLAN.md").write_text(PLAN)
    (root / ".gitignore").write_text("/runs/\n")
    if kind == "confirm" and frozen:
        protocol.freeze(phase, root / "PLAN.md", datetime.date(2026, 10, 1))
    for command in (
        ("init", "--quiet"),
        ("config", "user.name", "Test"),
        ("config", "user.email", "test@example.com"),
        ("add", "."),
        ("commit", "--quiet", "-m", "Phase 01"),
    ):
        git(*command, cwd=root)
    return root


def run(root: Path, seed: int = 3, **options: object) -> Path:
    with stamp.run(
        root / "phases/01-screen", seed, root=root, runs=root / "runs", **options
    ) as folder:
        (folder / "result.txt").write_text("done\n")
    return folder


def read(folder: Path) -> dict:
    return json.loads((folder / stamp.STAMP).read_text())


def test_clean_run_records_the_study_commit_and_the_library_install(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    library(monkeypatch, PINNED)
    root = study(tmp_path)

    folder = run(root)

    record = read(folder)
    assert folder.parent == root / "runs" / "01-screen"
    assert record["study"] == {"commit": git("rev-parse", "HEAD", cwd=root), "dirty": False}
    assert record["library"] == PINNED
    assert record["phase"] == {"name": "01-screen", "type": "explore"}
    assert record["config"] == {"type": "explore", "steps": 10}
    assert (folder / "config.yaml").read_text() == "type: explore\nsteps: 10\n"
    assert record["seed"] == 3
    assert record["hardware"]["python"]
    assert record["wall_clock_s"] >= 0 and record["started"] <= record["finished"]
    assert not (folder / stamp.DIFF).exists()
    assert "run_config" not in record and "extras" not in record


def test_a_resolved_configuration_is_recorded_beside_the_phases(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    library(monkeypatch, PINNED)
    resolved = {"steps": 40, "net": {"size": 8}}

    record = read(run(study(tmp_path), config=resolved))

    assert record["config"] == {"type": "explore", "steps": 10}
    assert record["run_config"] == resolved


def test_dirty_run_saves_the_diff(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    library(monkeypatch, PINNED)
    root = study(tmp_path)
    (root / "phases/01-screen/config.yaml").write_text("type: explore\nsteps: 20\n")
    (root / "phases/01-screen/run.py").write_text("print('new')\n")
    (root / "phases/01-screen/weights.bin").write_bytes(bytes(range(256)))

    folder = run(root)

    assert read(folder)["study"]["dirty"] is True
    diff = (folder / stamp.DIFF).read_text()
    assert "+steps: 20" in diff
    assert "+print('new')" in diff
    assert "GIT binary patch" in diff
    # Saving the diff leaves the study as it was.
    status = git("status", "--porcelain", cwd=root)
    assert status == (
        "M phases/01-screen/config.yaml\n?? phases/01-screen/run.py\n"
        "?? phases/01-screen/weights.bin"
    )


def test_editable_library_is_visible_in_the_stamp(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    checkout = tmp_path / "fakelib"
    checkout.mkdir()
    git("init", "--quiet", cwd=checkout)
    git("-c", "user.name=T", "-c", "user.email=t@e", "commit", "--quiet", "--allow-empty", "-m", "c", cwd=checkout)
    (checkout / "edited.py").write_text("x = 1\n")
    editable = {"version": "0.1.0", "editable": True, "path": str(checkout)}
    library(monkeypatch, editable)

    folder = run(study(tmp_path))

    assert read(folder)["library"] == {
        **editable,
        "commit": git("rev-parse", "HEAD", cwd=checkout),
        "dirty": True,
    }


def test_a_library_without_installed_from_is_read_from_its_distribution(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # PyYAML stands in: a module without `installed_from`, installed from an index.
    monkeypatch.setattr(stamp, "LIBRARY", "yaml")
    monkeypatch.setattr(stamp, "_distribution", lambda name: {"name": name, "version": "6"})

    record = read(run(study(tmp_path)))

    assert record["library"] == {"name": "yaml", "version": "6"}


def test_a_workspace_without_a_library_stamps_none(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(stamp, "LIBRARY", "")
    monkeypatch.setattr(stamp, "STAMP_EXTRAS", "")

    assert read(run(study(tmp_path)))["library"] is None


def test_stamp_extras_add_their_fields(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    library(monkeypatch, PINNED)
    extras = types.ModuleType("workspace_extras")
    extras.collect = lambda: {"solver": "nastran 2024.1"}
    monkeypatch.setitem(sys.modules, "workspace_extras", extras)
    monkeypatch.setattr(stamp, "STAMP_EXTRAS", "workspace_extras:collect")

    record = read(run(study(tmp_path)))

    assert record["extras"] == {"solver": "nastran 2024.1"}


def fake_conda(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, listing: str) -> None:
    conda = tmp_path / "conda"
    conda.write_text(f"#!/bin/sh\nprintf '%s' '{listing}'\n")
    conda.chmod(0o755)
    monkeypatch.setenv("CONDA_EXE", str(conda))


def test_conda_environments_the_phase_uses_are_stamped_by_hash(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    library(monkeypatch, PINNED)
    fake_conda(tmp_path, monkeypatch, "@EXPLICIT\nhttps://conda.example.org/fenics-1.0.conda\n")
    root = study(tmp_path)
    (root / "environments").mkdir()
    (root / "environments/fem.yml").write_text("name: fem\ndependencies:\n  - fenics=1.0\n")
    (root / "phases/01-screen/config.yaml").write_text("type: explore\nenvironments: [fem]\n")

    [environment] = read(run(root))["environments"]

    assert environment["name"] == "fem"
    assert environment["file"] == "environments/fem.yml"
    assert len(environment["explicit_sha256"]) == 64
    assert len(environment["file_sha256"]) == 64


def test_a_missing_conda_environment_refuses_the_run(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    library(monkeypatch, PINNED)
    monkeypatch.setenv("CONDA_EXE", str(tmp_path / "no-conda"))
    root = study(tmp_path)
    (root / "phases/01-screen/config.yaml").write_text("type: explore\nenvironments: [fem]\n")

    with pytest.raises(stamp.CondaError, match="fem"):
        run(root)

    assert not (root / "runs").exists()


def test_confirm_run_on_a_dirty_tree_refuses_to_start(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    library(monkeypatch, PINNED)
    root = study(tmp_path, "confirm")
    (root / "study.py").write_text("changed = True\n")

    with pytest.raises(stamp.DirtyTree, match="confirm phase 01-screen.*commit"):
        run(root)

    assert not (root / "runs").exists()


def test_confirm_run_on_a_clean_tree_with_a_frozen_protocol_runs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    library(monkeypatch, PINNED)

    folder = run(study(tmp_path, "confirm"))

    assert read(folder)["phase"]["type"] == "confirm"


def test_confirm_run_without_a_frozen_protocol_refuses_to_start(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    library(monkeypatch, PINNED)
    root = study(tmp_path, "confirm", frozen=False)

    with pytest.raises(protocol.ProtocolError, match="not frozen"):
        run(root)


def test_confirm_run_after_the_protocol_changed_refuses_to_start(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    library(monkeypatch, PINNED)
    root = study(tmp_path, "confirm")
    plan = root / "PLAN.md"
    plan.write_text(plan.read_text().replace("Three liners", "Two liners"))
    git("commit", "--quiet", "-am", "Fewer liners", cwd=root)

    with pytest.raises(protocol.ProtocolError, match="changed since it was frozen"):
        run(root)
    assert not (root / "runs").exists()


def test_another_phases_protocol_does_not_unfreeze_this_one(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    library(monkeypatch, PINNED)
    root = study(tmp_path, "confirm")
    plan = root / "PLAN.md"
    plan.write_text(plan.read_text().replace("Not this phase's.", "Changed later."))
    git("commit", "--quiet", "-am", "Phase 02 protocol", cwd=root)

    assert read(run(root))["phase"]["type"] == "confirm"


def test_phase_without_a_declared_type_refuses_to_start(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    library(monkeypatch, PINNED)
    root = study(tmp_path)
    (root / "phases/01-screen/config.yaml").write_text("steps: 10\n")
    git("commit", "--quiet", "-am", "No type", cwd=root)

    with pytest.raises(ValueError, match="type: explore` or `type: confirm"):
        run(root)
