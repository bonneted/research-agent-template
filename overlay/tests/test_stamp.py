"""Run stamping: every run records what it takes to reproduce it (study rule 7).

Each test makes a throwaway study repository with one phase, and stands a fake spimat in
for the library so the stamp's report of the install can be checked either way.
"""

import json
import subprocess
import sys
import types
from pathlib import Path

import pytest

from study import stamp


def git(*args: str, cwd: Path) -> str:
    return subprocess.run(
        ["git", *args], cwd=cwd, check=True, capture_output=True, text=True
    ).stdout.strip()


def library(monkeypatch: pytest.MonkeyPatch, report: dict) -> None:
    fake = types.ModuleType("spimat")
    fake.installed_from = lambda: report
    monkeypatch.setitem(sys.modules, "spimat", fake)


PINNED = {
    "version": "0.1.0",
    "editable": False,
    "url": "https://gitlab.example.org/spimat.git",
    "commit": "79ab5939" + "0" * 32,
}


def study(tmp_path: Path, kind: str = "explore") -> Path:
    root = tmp_path / "study"
    phase = root / "phases" / "01-screen"
    phase.mkdir(parents=True)
    (phase / "config.yaml").write_text(f"type: {kind}\nsteps: 10\n")
    (root / ".gitignore").write_text("/runs/\n")
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
    assert "run_config" not in record


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
    checkout = tmp_path / "spimat"
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


def test_confirm_run_on_a_dirty_tree_refuses_to_start(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    library(monkeypatch, PINNED)
    root = study(tmp_path, "confirm")
    (root / "study.py").write_text("changed = True\n")

    with pytest.raises(stamp.DirtyTree, match="confirm phase 01-screen.*commit"):
        run(root)

    assert not (root / "runs").exists()


def test_confirm_run_on_a_clean_tree_runs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    library(monkeypatch, PINNED)

    folder = run(study(tmp_path, "confirm"))

    assert read(folder)["phase"]["type"] == "confirm"


def test_phase_without_a_declared_type_refuses_to_start(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    library(monkeypatch, PINNED)
    root = study(tmp_path)
    (root / "phases/01-screen/config.yaml").write_text("steps: 10\n")
    git("commit", "--quiet", "-am", "No type", cwd=root)

    with pytest.raises(ValueError, match="type: explore` or `type: confirm"):
        run(root)
