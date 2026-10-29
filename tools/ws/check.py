"""`ws check`: what a machine can tell of whether a repository keeps the workspace's rules.

Each check reads only committed files, the local clones and conda; nothing goes to the
network. A `FAILED` line breaks a rule, a `WARNING` line may (the number heuristic, a
confirm phase not frozen yet). The off-limits repository is never read.
"""

import json
import os
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

import yaml

from ws import offlimits, protocol, resources
from ws.git import GitError, git
from ws.manifest import Workspace
from ws.sync import ROOT, hook

FINDINGS = "docs/findings"
# The notes of the findings folder that are not findings.
NOT_FINDINGS = {"finding-format.md", "index.md"}
STATUSES = ("hint", "confirmed", "retracted", "superseded")
PHASE_TYPES = ("explore", "confirm")
VERDICTS = ("upheld", "narrowed", "rejected")
# What each kind of evidence must carry (ADR 0007, `docs/findings/finding-format.md`).
KINDS = {
    "run": ("note", "stamp", "phase"),
    "derivation": ("derivation", "check", "phase"),
    "reproduction": ("citekey", "where", "published", "reproduced", "tolerance", "phase"),
    "source": ("citekey", "page"),
    "measurement": ("dataset", "sha256", "phase"),
    "legacy": ("commit", "note"),
}
# Evidence that can make a finding `confirmed`, from a confirm phase.
CONFIRMING = ("run", "derivation", "reproduction", "measurement")
_PERMALINK = re.compile(
    r"(?P<url>[a-z][a-z+.-]*://\S+?)/-/(?P<kind>blob|tree|commit)/(?P<sha>[0-9a-f]{7,40})"
    r"(?:/(?P<path>[^\s#?)]*))?"
)
_PHASE = re.compile(r"\d{2}-[a-z0-9]+(?:-[a-z0-9]+)*")
_PHASE_NOTE = re.compile(r"docs/wiki/phases/(\d{2}-[a-z0-9-]+)\.md")
_GROUP = re.compile(r"\[[^\[\]]*@[^\[\]]*\]")
_KEY = re.compile(r"@([\w][\w:.+/-]*\w|\w)")
_CODE = re.compile(r"```.*?```|`[^`\n]*`", re.DOTALL)
# A number in prose: not part of a word, a year, or a list's numbering.
_NUMBER = re.compile(r"(?<![\w.])\d+(?:[.,]\d+)?(?![\w])")
_YEAR = re.compile(r"(19|20)\d\d")


@dataclass
class Report:
    """The problems found in one repository."""

    failures: list[str]
    warnings: list[str]

    def lines(self, name: str) -> list[str]:
        if not self.failures and not self.warnings:
            return [f"{name}: ok"]
        return [f"{name}: FAILED: {line}" for line in self.failures] + [
            f"{name}: WARNING: {line}" for line in self.warnings
        ]


def _notes(folder: Path) -> list[Path]:
    """The Markdown notes under `folder`, without following links: the hub's study
    mounts and the pool are not its own.
    """
    found = []
    for directory, folders, files in os.walk(folder, followlinks=False):
        folders[:] = sorted(
            name for name in folders if not os.path.islink(os.path.join(directory, name))
        )
        found += [Path(directory) / name for name in sorted(files) if name.endswith(".md")]
    return found


def _citekeys(repository: Path) -> set[str]:
    bibliography = repository / resources.BIBLIOGRAPHY
    if not bibliography.is_file():
        return set()
    text = bibliography.read_text(encoding="utf-8")
    return {
        match[2]
        for match in resources.ENTRY.finditer(text)
        if match[1].lower() not in resources.NOT_ENTRIES
    }


def _prose(text: str) -> str:
    """The text without code, so a `@decorator` or an example is not a citation."""
    return _CODE.sub(lambda match: "\n" * match[0].count("\n"), text)


def _citations(repository: Path, known: set[str], report: Report) -> None:
    """Every `[@citekey]` of `docs/` names an entry of the bibliographies `known`; a
    number beside a citation without a locator is a warning.
    """
    for note in _notes(repository / "docs"):
        relative = note.relative_to(repository).as_posix()
        text = _prose(note.read_text(encoding="utf-8"))
        for number, line in enumerate(text.splitlines(), 1):
            groups = _GROUP.findall(line)
            for group in groups:
                for key in _KEY.findall(group):
                    if key not in known:
                        report.failures.append(
                            f"{relative}:{number}: [@{key}] is not in {resources.BIBLIOGRAPHY}"
                        )
            bare = [
                group
                for group in groups
                if not re.search(r"@[\w:.+/-]+\s*,\s*\S", group)
            ]
            if not bare:
                continue
            rest = re.sub(r"^\s*(\d+\.|[-*])\s+", "", line)
            rest = re.sub(r"\[\[[^\]]*\]\]|\[[^\]]*\]\([^)]*\)|https?://\S+", "", rest)
            rest = _GROUP.sub("", rest)
            numbers = [
                found for found in _NUMBER.findall(rest) if not _YEAR.fullmatch(found)
            ]
            if numbers:
                report.warnings.append(
                    f"{relative}:{number}: {numbers[0]} beside {bare[0]}, which gives no page"
                )


def _front_matter(text: str) -> dict | None:
    if not text.startswith("---\n"):
        return None
    end = text.find("\n---", 4)
    if end < 0:
        return None
    try:
        data = yaml.safe_load(text[4:end])
    except yaml.YAMLError:
        return None
    return data if isinstance(data, dict) else None


def _commit_exists(clone: Path, sha: str, path: str | None) -> bool:
    try:
        git("cat-file", "-e", f"{sha}^{{commit}}", cwd=clone)
        if path:
            git("cat-file", "-e", f"{sha}:{path}", cwd=clone)
    except GitError:
        return False
    return True


def _phase_type(clone: Path, sha: str, phase: str) -> str | None:
    """The type a phase's configuration declares at a commit, or None if it cannot be read."""
    try:
        text = git("show", f"{sha}:phases/{phase}/{protocol.CONFIG}", cwd=clone)
        config = yaml.safe_load(text) or {}
    except (GitError, yaml.YAMLError):
        return None
    return config.get("type") if isinstance(config, dict) else None


class _Links:
    """Evidence permalinks checked against the local clones."""

    def __init__(self, root: Path, workspace: Workspace) -> None:
        self.root = root
        self.workspace = workspace
        self.clones = {
            repository.url.removesuffix(".git"): repository
            for repository in workspace.repositories
        }

    def check(self, value: str, where: str, report: Report) -> list[tuple[Path, str, str]]:
        """Check every permalink in `value`; returns the readable ones as (clone, sha, path)."""
        found = []
        for match in _PERMALINK.finditer(value):
            repository = self.clones.get(match["url"])
            if repository is None:
                report.warnings.append(
                    f"{where}: {match['url']} is not a repository of the workspace"
                )
                continue
            clone = self.root / repository.name
            if repository.role == "off-limits" or not (clone / ".git").exists():
                continue
            path = match["path"] if match["kind"] == "blob" else None
            if not _commit_exists(clone, match["sha"], path):
                report.failures.append(
                    f"{where}: {match['sha'][:12]}{':' + path if path else ''} is not in "
                    f"the clone of {repository.name}: a wrong permalink, or fetch it"
                )
                continue
            found.append((clone, match["sha"], match["path"] or ""))
        return found


def _evidence_item(
    item: object, where: str, links: _Links, report: Report
) -> str | None:
    """Check one evidence item; returns its phase type when it counts toward `confirmed`."""
    if not isinstance(item, dict) or item.get("kind") not in KINDS:
        report.failures.append(
            f"{where}: each evidence item needs a kind, one of {', '.join(KINDS)}"
        )
        return None
    kind = item["kind"]
    missing = [field for field in KINDS[kind] if item.get(field) in (None, "")]
    if missing:
        report.failures.append(f"{where}: {kind} evidence needs {', '.join(missing)}")
        return None
    phase = item.get("phase")
    if "phase" in KINDS[kind] and phase not in PHASE_TYPES:
        report.failures.append(f"{where}: phase is {phase!r}, not explore or confirm")
        return None
    for value in item.values():
        for clone, sha, path in links.check(str(value), where, report):
            # The phase a run's note belongs to declares its type at that commit.
            if kind == "run" and (note := _PHASE_NOTE.fullmatch(path)):
                declared = _phase_type(clone, sha, note[1])
                if declared is not None and declared != phase:
                    report.failures.append(
                        f"{where}: says phase {phase}, but phase {note[1]} is {declared} "
                        f"at {sha[:12]}"
                    )
    if kind in ("run", "derivation", "legacy"):
        fields = ("note",) if kind == "run" else ("derivation", "check") if kind == "derivation" else ("commit", "note")
        for field in fields:
            if not _PERMALINK.search(str(item[field])):
                report.failures.append(
                    f"{where}: {field} must be a permalink at a commit (/-/blob/<sha>/...)"
                )
    return phase if kind in CONFIRMING else None


def _datasets(root: Path, workspace: Workspace) -> dict[str, set[str]]:
    """The checksums each dataset name has in the readable clones' resource manifests."""
    found: dict[str, set[str]] = {}
    for repository in workspace.repositories:
        clone = root / repository.name
        if repository.role == "off-limits" or not clone.is_dir():
            continue
        try:
            listed = resources.load(clone)
        except resources.ResourceError:
            continue
        for data in listed.data:
            found.setdefault(data.name, set()).add(data.sha256)
    return found


def _findings(root: Path, workspace: Workspace, hub: Path, known: set[str], report: Report) -> None:
    """Each finding's front matter against the format of `docs/findings/finding-format.md`."""
    links = _Links(root, workspace)
    datasets = _datasets(root, workspace)
    folder = hub / FINDINGS
    for note in sorted(folder.glob("*.md")) if folder.is_dir() else []:
        if note.name in NOT_FINDINGS:
            continue
        where = f"{FINDINGS}/{note.name}"
        data = _front_matter(note.read_text(encoding="utf-8"))
        if data is None:
            report.failures.append(f"{where}: no front matter in --- lines")
            continue
        status = data.get("status")
        if status not in STATUSES:
            report.failures.append(
                f"{where}: status is {status!r}, not one of {', '.join(STATUSES)}"
            )
        evidence = data.get("evidence")
        if not isinstance(evidence, list) or not evidence:
            report.failures.append(f"{where}: evidence must be a list of items")
            evidence = []
        phases = []
        for index, item in enumerate(evidence):
            phases.append(_evidence_item(item, f"{where} evidence {index + 1}", links, report))
            if not isinstance(item, dict):
                continue
            if (
                item.get("kind") in ("source", "reproduction")
                and item.get("citekey")
                and str(item["citekey"]) not in known
            ):
                report.failures.append(
                    f"{where} evidence {index + 1}: {item['citekey']} is in no "
                    f"{resources.BIBLIOGRAPHY} of the workspace"
                )
            if item.get("kind") == "measurement" and item.get("dataset"):
                sums = datasets.get(str(item["dataset"]))
                if sums is None:
                    report.warnings.append(
                        f"{where} evidence {index + 1}: dataset {item['dataset']} is in "
                        f"no cloned {resources.FILENAME}"
                    )
                elif str(item["sha256"]).lower() not in sums:
                    report.failures.append(
                        f"{where} evidence {index + 1}: dataset {item['dataset']} has "
                        f"another sha256 in {resources.FILENAME}"
                    )
        if status == "superseded" and not data.get("superseded_by"):
            report.failures.append(f"{where}: a superseded finding names its superseded_by")
        reviewed = data.get("reviewed")
        if reviewed is not None and (
            not isinstance(reviewed, dict)
            or reviewed.get("verdict") not in VERDICTS
            or not reviewed.get("date")
        ):
            report.failures.append(
                f"{where}: reviewed needs a date and a verdict, one of {', '.join(VERDICTS)}"
            )
        if status == "confirmed":
            if "confirm" not in phases:
                report.failures.append(
                    f"{where}: confirmed needs evidence from a confirm phase other than "
                    "legacy or source"
                )
            if not isinstance(reviewed, dict) or reviewed.get("verdict") != "upheld":
                report.failures.append(
                    f"{where}: confirmed needs a review-finding verdict of upheld in reviewed"
                )


def _phases(study: Path, report: Report) -> None:
    """Each phase folder has its note and a type; a confirm phase is frozen at its protocol."""
    plan_file = study / protocol.PLAN
    plan = plan_file.read_text(encoding="utf-8") if plan_file.is_file() else ""
    phases = study / "phases"
    for folder in sorted(phases.iterdir()) if phases.is_dir() else []:
        if not folder.is_dir() or not _PHASE.fullmatch(folder.name):
            continue
        name = folder.name
        if not (study / f"docs/wiki/phases/{name}.md").is_file():
            report.failures.append(f"phases/{name} has no note docs/wiki/phases/{name}.md")
        try:
            config = yaml.safe_load((folder / protocol.CONFIG).read_text(encoding="utf-8")) or {}
        except (OSError, yaml.YAMLError):
            config = None
        if not isinstance(config, dict) or config.get("type") not in PHASE_TYPES:
            report.failures.append(
                f"phases/{name}/{protocol.CONFIG} declares no type: explore or confirm"
            )
            continue
        if config["type"] != "confirm":
            continue
        record = protocol.frozen(config)
        if record is None:
            report.warnings.append(
                f"phases/{name}: confirm phase not frozen; freeze it before its first run"
            )
            continue
        if protocol.digest(plan, name) != record["hash"]:
            report.failures.append(
                f"phases/{name}: the protocol changed since it was frozen on "
                f"{record.get('frozen')}: log a deviation, then freeze it again"
            )
        logged = protocol.deviations(plan, name)
        for previous in record.get("previous") or []:
            since = str(previous.get("frozen") if isinstance(previous, dict) else "")
            if not any(date >= since for date in logged):
                report.failures.append(
                    f"phases/{name}: refrozen with no deviation logged since {since}"
                )


def _rule_packs(study: Path, report: Report) -> None:
    """Each rule pack `PLAN.md` selects is in the study's `rules/`."""
    plan_file = study / protocol.PLAN
    if not plan_file.is_file():
        return
    text = re.sub(r"<!--.*?-->", "", plan_file.read_text(encoding="utf-8"), flags=re.DOTALL)
    for line in protocol._section(text, "Rule packs"):
        match = re.match(r"\s*[-*]\s+`?([a-z0-9-]+)`?", line)
        if match and not (study / "rules" / f"{match[1]}.md").is_file():
            report.failures.append(
                f"{protocol.PLAN} selects the rule pack {match[1]}, not in rules/"
            )


def _conda() -> str | None:
    return os.environ.get("CONDA_EXE") or shutil.which("conda")


def _pins(file: Path) -> dict[str, str | None]:
    """The packages an environment file pins, with their exact version (None if not exact)."""
    data = yaml.safe_load(file.read_text(encoding="utf-8")) or {}
    pins: dict[str, str | None] = {}
    for entry in data.get("dependencies") or []:
        if not isinstance(entry, str):
            continue
        spec = entry.split("::")[-1].replace("==", "=")
        name, _, rest = spec.partition("=")
        pins[name.strip()] = rest.split("=")[0].strip() or None
    return pins


def _environments(repository: Path, report: Report) -> None:
    """Each declared conda environment that exists here matches its pinned file."""
    folder = repository / "environments"
    files = sorted(folder.glob("*.yml")) if folder.is_dir() else []
    conda = _conda() if files else None
    if conda is None:
        return
    try:
        listed = json.loads(
            subprocess.run(
                [conda, "env", "list", "--json"], capture_output=True, check=True, text=True
            ).stdout
        )
        present = {Path(path).name for path in listed.get("envs", [])}
    except (OSError, subprocess.CalledProcessError, ValueError):
        return
    for file in files:
        name = file.stem
        pins = _pins(file)
        for package, version in pins.items():
            if version is None:
                report.warnings.append(
                    f"environments/{file.name}: {package} is not pinned to a version"
                )
        if name not in present:
            continue
        try:
            installed = {
                package["name"]: package["version"]
                for package in json.loads(
                    subprocess.run(
                        [conda, "list", "-n", name, "--json"],
                        capture_output=True,
                        check=True,
                        text=True,
                    ).stdout
                )
            }
        except (OSError, subprocess.CalledProcessError, ValueError, KeyError, TypeError):
            report.warnings.append(f"environments/{file.name}: conda list -n {name} failed")
            continue
        drift = [
            f"{package} {installed.get(package, 'missing')} (pinned {version})"
            for package, version in pins.items()
            if version is not None and installed.get(package) != version
        ]
        if drift:
            report.failures.append(
                f"conda environment {name} drifted from environments/{file.name}: "
                + ", ".join(drift)
            )


def check_repository(root: Path, workspace: Workspace, name: str) -> Report:
    """The problems of the repository `name` of the workspace at `root`."""
    repository = workspace.repository(name)
    path = root / name
    hub = root / workspace.hub.name
    report = Report([], [])
    known = _citekeys(path) | _citekeys(hub)
    if repository.role == "hub":
        # Findings and digests in the hub cite the studies' documents too.
        for other in workspace.repositories:
            if other.role != "off-limits":
                known |= _citekeys(root / other.name)
        _findings(root, workspace, hub, known, report)
    _citations(path, known, report)
    if repository.role == "study":
        _phases(path, report)
        _rule_packs(path, report)
    _environments(path, report)
    report.failures += offlimits.drift(path, workspace, hook(hub))
    return report


def check(
    root: Path, workspace: Workspace, names: list[str], everything: bool = False
) -> tuple[list[str], bool]:
    """Check the repositories `names`, and the workspace root's off-limits files when
    `everything`; returns the report lines and whether nothing failed.
    """
    lines, ok = [], True
    for name in names:
        repository = workspace.repository(name)
        if repository.role == "off-limits":
            lines.append(f"{name}: skipped: ws never reads the off-limits repository")
            continue
        if not (root / name / ".git").exists():
            lines.append(f"{name}: not cloned, run ws sync")
            ok = False
            continue
        report = check_repository(root, workspace, name)
        ok = ok and not report.failures
        lines += report.lines(name)
    if everything and workspace.off_limits:
        report = Report(offlimits.drift(root, workspace, hook(root / workspace.hub.name)), [])
        ok = ok and not report.failures
        lines += report.lines(ROOT)
    return lines, ok
