"""The run stamp: what it takes to reproduce a run, written into its folder (core rule 4,
rigour pack 1).

A phase's `run.py` wraps its work in `run`:

    with stamp.run(Path(__file__).parent, seed) as folder:
        ...  # write results into `folder`

The stamp records the inquiry's commit and whether the tree was clean (the diff is saved
beside it when not), the library's install, the phase's configuration, the seed, the
hardware and the wall-clock. The library's install is what its `installed_from()`
reports when it has one, or else its distribution's version and origin, with the commit
and state of the checkout when it is installed editable. A runner that builds each run's
configuration (a base file plus overrides) passes it as `config`: the stamp records it
as `run_config`, beside the phase's.

Each conda environment the phase's configuration lists under `environments` (a run
that calls `conda run -n <name>`) is recorded by the hash of its `conda list
--explicit`, beside the hash of its pinned file `environments/<name>.yml`. The
`STAMP_EXTRAS` function, a `module:function` returning a mapping, adds its fields
under `extras`.

A run in a confirm phase refuses to start on a dirty tree, and on a `PLAN.md` whose
protocol is not the one frozen for the phase (`study/protocol.py`).
"""

import copy
import hashlib
import importlib
import importlib.metadata
import json
import os
import platform
import shutil
import subprocess
import time
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path

import yaml

from study import protocol
from study.paths import ROOT, RUNS

STAMP = "stamp.json"
DIFF = "diff.patch"
CONFIG = "config.yaml"
# Set when the pack is adopted: the library's distribution and import name (empty for
# an inquiry without one), and a `module:function` returning extra fields for the stamp.
LIBRARY = ""
STAMP_EXTRAS = ""
# The folder of the pinned conda environments, `environments/<name>.yml`.
ENVIRONMENTS = "environments"


class DirtyTree(RuntimeError):
    """A confirm run was asked for on an inquiry tree with uncommitted changes."""


class CondaError(RuntimeError):
    """A conda environment the phase uses could not be recorded."""


def _git(*args: str, root: Path, check: bool = True) -> str:
    return subprocess.run(
        ["git", *args], cwd=root, check=check, capture_output=True, text=True
    ).stdout


def _diff(root: Path) -> bytes:
    """The uncommitted changes, untracked files included, without touching the index.

    Bytes: a binary patch, or a file in another encoding, is saved as git writes it.
    """
    command = ["git", "diff", "--binary"]
    diff = subprocess.run([*command, "HEAD"], cwd=root, check=True, capture_output=True).stdout
    for name in _git("ls-files", "--others", "--exclude-standard", "-z", root=root).split("\0"):
        if not name:
            continue
        untracked = subprocess.run(
            [*command, "--no-index", "--", os.devnull, name],
            cwd=root,
            capture_output=True,
            check=False,
        )
        # Exits 1 when the files differ, which they always do here; more is an error.
        if untracked.returncode > 1:
            raise subprocess.CalledProcessError(untracked.returncode, untracked.args, stderr=untracked.stderr)
        diff += untracked.stdout
    return diff


def _distribution(name: str) -> dict:
    """The library's install as its distribution's metadata records it (PEP 610)."""
    distribution = importlib.metadata.distribution(name)
    report: dict = {"version": distribution.version, "editable": False}
    origin = distribution.read_text("direct_url.json")
    if origin:
        url = json.loads(origin)
        report["url"] = url.get("url")
        report["editable"] = bool(url.get("dir_info", {}).get("editable"))
        if commit := url.get("vcs_info", {}).get("commit_id"):
            report["commit"] = commit
        if report["editable"] and str(report["url"]).startswith("file://"):
            report["path"] = report["url"].removeprefix("file://")
    return report


def _library() -> dict | None:
    """The library's install; for an editable one, the commit and state of its checkout."""
    if not LIBRARY:
        return None
    # Imported here, so the study's tests can stand a fake library in before the import.
    module = importlib.import_module(LIBRARY)
    installed_from = getattr(module, "installed_from", None)
    report = dict(installed_from()) if callable(installed_from) else _distribution(LIBRARY)
    path = report.get("path")
    if report.get("editable") and path and (Path(path) / ".git").exists():
        checkout = Path(path)
        report = {
            **report,
            "commit": _git("rev-parse", "HEAD", root=checkout).strip(),
            "dirty": bool(_git("status", "--porcelain", root=checkout).strip()),
        }
    return report


def _environments(names: list[str], root: Path) -> list[dict]:
    """Each conda environment by the hash of its explicit package list, and of its pinned file."""
    conda = os.environ.get("CONDA_EXE") or "conda"
    records = []
    for name in names:
        try:
            listing = subprocess.run(
                [conda, "list", "--explicit", "-n", name],
                check=True,
                capture_output=True,
            ).stdout
        except (OSError, subprocess.CalledProcessError) as error:
            raise CondaError(
                f"conda environment {name}: `conda list --explicit` failed ({error})"
            ) from error
        pinned = root / ENVIRONMENTS / f"{name}.yml"
        records.append(
            {
                "name": name,
                "explicit_sha256": hashlib.sha256(listing).hexdigest(),
                "file": f"{ENVIRONMENTS}/{name}.yml",
                "file_sha256": (
                    hashlib.sha256(pinned.read_bytes()).hexdigest()
                    if pinned.is_file()
                    else None
                ),
            }
        )
    return records


def _extras() -> dict | None:
    """The fields `STAMP_EXTRAS` adds, or None without one."""
    if not STAMP_EXTRAS:
        return None
    module, _, function = STAMP_EXTRAS.partition(":")
    return dict(getattr(importlib.import_module(module), function)())


def _hardware() -> dict:
    hardware = {
        "host": platform.node(),
        "platform": platform.platform(),
        "processor": platform.processor() or platform.machine(),
        "cpus": os.cpu_count(),
        "python": platform.python_version(),
    }
    try:
        import jax
    except ImportError:
        return hardware
    hardware["jax"] = jax.__version__
    hardware["devices"] = [str(device) for device in jax.devices()]
    return hardware


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


@contextmanager
def run(
    phase: Path,
    seed: int,
    *,
    name: str | None = None,
    config: dict | None = None,
    root: Path = ROOT,
    runs: Path = RUNS,
) -> Iterator[Path]:
    """Stamp a run of `phase` (its folder) in a new folder `runs/<phase>/<name>`, and yield it.

    `name` defaults to the start time and the seed. `config`, the run's resolved
    configuration, is recorded as `run_config` beside the phase's. The stamp gets its
    wall-clock and end time when the block ends, even by an exception (then `failed` is
    true).
    Raises `DirtyTree` for a confirm phase whose study has uncommitted changes,
    `protocol.ProtocolError` for one whose protocol is not frozen as it is, and
    `ValueError` for a phase whose `config.yaml` declares no type.
    """
    phase = Path(phase).resolve()
    text = (phase / CONFIG).read_text(encoding="utf-8")
    phase_config = yaml.safe_load(text) or {}
    kind = phase_config.get("type")
    if kind not in ("explore", "confirm"):
        raise ValueError(f"{phase / CONFIG}: declare the phase `type: explore` or `type: confirm`")
    dirty = bool(_git("status", "--porcelain", root=root).strip())
    if dirty and kind == "confirm":
        raise DirtyTree(
            f"confirm phase {phase.name}: the study has uncommitted changes; "
            "commit them (or stash them) before a confirm run, so it stamps a commit alone"
        )
    if kind == "confirm":
        protocol.check(phase, Path(root) / protocol.PLAN)
    environments = _environments(list(phase_config.get("environments") or []), Path(root))
    extras = _extras()
    started = _now()
    stamp_time = datetime.fromisoformat(started).strftime("%Y%m%dT%H%M%S")
    folder = Path(runs) / phase.name / (name or f"{stamp_time}-seed{seed}")
    folder.mkdir(parents=True)
    if dirty:
        (folder / DIFF).write_bytes(_diff(root))
    shutil.copyfile(phase / CONFIG, folder / CONFIG)
    record = {
        "study": {"commit": _git("rev-parse", "HEAD", root=root).strip(), "dirty": dirty},
        "library": _library(),
        "phase": {"name": phase.name, "type": kind},
        "config": phase_config,
        **({"run_config": copy.deepcopy(config)} if config is not None else {}),
        **({"environments": environments} if environments else {}),
        **({"extras": extras} if extras is not None else {}),
        "seed": seed,
        "hardware": _hardware(),
        "started": started,
    }

    def write(**end: object) -> None:
        (folder / STAMP).write_text(json.dumps({**record, **end}, indent=2) + "\n", encoding="utf-8")

    write()
    clock = time.perf_counter()
    failed = True
    try:
        yield folder
        failed = False
    finally:
        write(finished=_now(), wall_clock_s=time.perf_counter() - clock, failed=failed)
