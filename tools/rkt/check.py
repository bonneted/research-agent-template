"""`rkt check`: what a machine can tell of whether an inquiry keeps the kit's rules.

Each check reads only the inquiry's files, the clones of its parent and sub-inquiries
where they are present, and conda; nothing goes to the network. A `FAILED` line breaks
a rule, a `WARNING` line may (the number heuristic, a confirm phase not frozen yet).
"""

import json
import os
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

import yaml

from rkt import inquiry as inquiries
from rkt import protocol, resources
from rkt.git import GitError, git
from rkt.inquiry import CHILDREN, Inquiry

FINDINGS = "docs/findings"
WIKI = "docs/wiki"
ENTRY = f"{WIKI}/index.md"
INDEX = "index.md"
# The notes of the findings folder that are not findings.
NOT_FINDINGS = {"finding-format.md", INDEX}
STATUSES = ("hint", "confirmed", "retracted", "superseded")
PHASE_TYPES = ("explore", "confirm")
LEVELS = ("scout", "build", "publish")
VERDICTS = ("upheld", "narrowed", "rejected")
ROUTES = "Sub-inquiries"
# What each kind of evidence must carry (`docs/findings/finding-format.md`).
KINDS = {
    "run": ("note", "run", "phase"),
    "derivation": ("derivation", "check", "phase"),
    "reproduction": ("citekey", "where", "published", "reproduced", "tolerance", "phase"),
    "source": ("citekey", "page"),
    "measurement": ("dataset", "sha256", "phase"),
    "legacy": ("commit", "note"),
    "sub-inquiry": ("finding", "status"),
}
# Evidence that can make a finding `confirmed`, from a confirm phase.
CONFIRMING = ("run", "derivation", "reproduction", "measurement")
# Fields that must be permalinks at a commit.
PERMALINKS = {
    "run": ("note",),
    "derivation": ("derivation", "check"),
    "legacy": ("commit", "note"),
    "sub-inquiry": ("finding",),
}
# A bibliography field that identifies a reference (rule 8).
IDENTIFIERS = ("doi", "eprint", "url", "isbn")
_PERMALINK = re.compile(
    r"(?P<url>[a-z][a-z+.-]*://\S+?)/-/(?P<kind>blob|tree|commit)/(?P<sha>[0-9a-f]{7,40})"
    r"(?:/(?P<path>[^\s#?)]*))?"
)
_PHASE = re.compile(r"\d{2}-[a-z0-9]+(?:-[a-z0-9]+)*")
_PHASE_NOTE = re.compile(r"docs/wiki/phases/(\d{2}-[a-z0-9-]+)\.md")
_GROUP = re.compile(r"\[[^\[\]]*@[^\[\]]*\]")
_KEY = re.compile(r"@([\w][\w:.+/-]*\w|\w)")
_CODE = re.compile(r"```.*?```|`[^`\n]*`", re.DOTALL)
_COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)
_LINK = re.compile(r"(?<!!)\[[^\[\]]*\]\(([^()\s]+)(?:\s+\"[^\"]*\")?\)")
_WIKILINK = re.compile(r"\[\[[^\]]+\]\]")
_EXTERNAL = re.compile(r"^[a-z][a-z+.-]*:", re.IGNORECASE)
# A number in prose: not part of a word, a year, or a list's numbering.
_NUMBER = re.compile(r"(?<![\w.])\d+(?:[.,]\d+)?(?![\w])")
_YEAR = re.compile(r"(19|20)\d\d")
_FIELD = re.compile(r"^\s*(\w+)\s*=", re.MULTILINE)


@dataclass
class Report:
    """The problems found in one inquiry."""

    failures: list[str]
    warnings: list[str]

    def lines(self, name: str) -> list[str]:
        if not self.failures and not self.warnings:
            return [f"{name}: ok"]
        return [f"{name}: FAILED: {line}" for line in self.failures] + [
            f"{name}: WARNING: {line}" for line in self.warnings
        ]


def _own(root: Path, path: Path) -> bool:
    """Whether `path` belongs to the inquiry at `root`, and not to a sub-inquiry of it."""
    try:
        parts = path.relative_to(root).parts
    except ValueError:
        return False
    return not parts or parts[0] != CHILDREN


def _notes(root: Path, folder: str = "docs") -> list[Path]:
    """The inquiry's own Markdown notes under `folder`, without following links."""
    found = []
    for directory, folders, files in os.walk(root / folder, followlinks=False):
        folders[:] = sorted(
            name
            for name in folders
            if not os.path.islink(os.path.join(directory, name))
            and not name.startswith(".")
        )
        found += [Path(directory) / name for name in sorted(files) if name.endswith(".md")]
    return found


def _prose(text: str) -> str:
    """The text without code and comments, keeping line numbers: an example is not a link."""
    blank = lambda match: "\n" * match[0].count("\n")
    return _CODE.sub(blank, _COMMENT.sub(blank, text))


def _relative(inquiry: Inquiry, path: Path) -> str:
    return path.relative_to(inquiry.path).as_posix()


# Links: every link resolves, and goes up one level, down one level, or stays home.


class _Tree:
    """The inquiries a note of `inquiry` may link to: itself, its parent and its children."""

    def __init__(self, inquiry: Inquiry) -> None:
        self.root = inquiry.path.resolve()
        self.parent = inquiry.parent_path.resolve() if inquiry.parent_path else None
        self.children = {
            child.name: (self.root / CHILDREN / child.name) for child in inquiry.children
        }

    def home(self, target: Path) -> tuple[str, Path] | None:
        """Where a link's target lies, `self`, `parent` or `child`, and that inquiry's
        folder; None for elsewhere.
        """
        if _own(self.root, target):
            return "self", self.root
        for path in self.children.values():
            if _own(path, target):
                return "child", path
        parent = self.parent
        # A parent not checked out: two folders up from an inquiry in `inquiries/`.
        if parent is None and self.root.parent.name == CHILDREN:
            parent = self.root.parent.parent
        if parent is not None and _own(parent, target):
            return "parent", parent
        return None


def _targets(inquiry: Inquiry, note: Path, report: Report) -> list[Path]:
    """Check the links of `note`; returns the targets inside the inquiry that exist."""
    tree = _Tree(inquiry)
    where = _relative(inquiry, note)
    text = _prose(note.read_text(encoding="utf-8"))
    found = []
    for number, line in enumerate(text.splitlines(), 1):
        if wiki := _WIKILINK.search(line):
            report.failures.append(
                f"{where}:{number}: {wiki[0]} is a wikilink: use a relative Markdown link"
            )
        for target in _LINK.findall(line):
            if _EXTERNAL.match(target) or target.startswith("#"):
                continue
            path = target.split("#")[0]
            if not path:
                continue
            if path.startswith("/"):
                report.failures.append(
                    f"{where}:{number}: {target} is absolute: links are relative"
                )
                continue
            resolved = Path(os.path.normpath(note.parent.resolve() / path))
            found_home = tree.home(resolved)
            if found_home is None:
                report.failures.append(
                    f"{where}:{number}: {target} leaves this inquiry, its parent and its "
                    "children: link through the common ancestor instead"
                )
                continue
            home, folder = found_home
            # The pool, and an inquiry not checked out, cannot be read: trust the link.
            if not (folder / inquiries.FILENAME).is_file() or (
                resolved.relative_to(folder).parts[:1] == ("resources",)
            ):
                continue
            if not resolved.exists():
                report.failures.append(f"{where}:{number}: {target} does not exist")
                continue
            if home == "self":
                found.append(resolved)
    return found


def _links(inquiry: Inquiry, report: Report) -> None:
    """Links resolve and stay in the tree's reach; every note is reachable from the entry
    index; every notes folder has its index.
    """
    notes = _notes(inquiry.path) + [
        path
        for name in ("GLOSSARY.md", "PLAN.md", "README.md")
        if (path := inquiry.path / name).is_file()
    ]
    graph = {note.resolve(): _targets(inquiry, note, report) for note in notes}
    entry = (inquiry.path / ENTRY).resolve()
    if entry not in graph:
        report.failures.append(f"{ENTRY} missing: it is the entry to the wiki")
        return
    seen, todo = {entry}, [entry]
    while todo:
        for target in graph.get(todo.pop(), []):
            if target.suffix == ".md" and target not in seen:
                seen.add(target)
                todo.append(target)
    for folder in (WIKI, FINDINGS):
        for note in _notes(inquiry.path, folder):
            if note.resolve() not in seen:
                report.failures.append(
                    f"{_relative(inquiry, note)} is not reachable from {ENTRY}: "
                    "link it from its folder's index"
                )
        for directory in sorted({note.parent for note in _notes(inquiry.path, folder)}):
            if not (directory / INDEX).is_file():
                report.failures.append(
                    f"{_relative(inquiry, directory)}/ has notes but no {INDEX}"
                )


def _section(text: str, heading: str) -> str:
    """The text under the `## heading` of a note, up to the next `## `."""
    match = re.search(rf"^## {re.escape(heading)}\s*$(.*?)(?=^## |\Z)", text, re.MULTILINE | re.DOTALL)
    return match[1] if match else ""


def _routes(inquiry: Inquiry, report: Report) -> None:
    """The entry index routes to each sub-inquiry of `inquiry.yaml`, and to no other."""
    entry = inquiry.path / ENTRY
    if not entry.is_file():
        return
    section = _section(_prose(entry.read_text(encoding="utf-8")), ROUTES)
    routed = set(re.findall(rf"\]\((?:\.\./)*{CHILDREN}/([a-z0-9-]+)/", section))
    listed = {child.name for child in inquiry.children}
    for name in sorted(listed - routed):
        report.failures.append(
            f"{ENTRY}: sub-inquiry {name} has no route under ## {ROUTES}"
        )
    for name in sorted(routed - listed):
        report.failures.append(
            f"{ENTRY}: routes to {name}, which {inquiries.FILENAME} does not list"
        )


# Citations: every key is in a bibliography, and every reference has an identifier.


def _entries(folder: Path) -> dict[str, str]:
    """The bibliography's entries at `folder`, by citekey, with their text."""
    bibliography = folder / resources.BIBLIOGRAPHY
    if not bibliography.is_file():
        return {}
    text = bibliography.read_text(encoding="utf-8")
    matches = list(resources.ENTRY.finditer(text))
    return {
        match[2]: text[match.start() : (matches[i + 1].start() if i + 1 < len(matches) else len(text))]
        for i, match in enumerate(matches)
        if match[1].lower() not in resources.NOT_ENTRIES
    }


def _known(inquiry: Inquiry) -> set[str]:
    """The citekeys a note of `inquiry` may cite: its own, and its ancestors' present ones."""
    known = set(_entries(inquiry.path))
    folder = inquiry.parent_path
    while folder is not None:
        known |= set(_entries(folder))
        folder = inquiries.load(folder).parent_path
    return known


def _identifiers(inquiry: Inquiry, report: Report) -> None:
    for key, text in _entries(inquiry.path).items():
        fields = {field.lower() for field in _FIELD.findall(text)}
        if not fields & set(IDENTIFIERS):
            report.warnings.append(
                f"{resources.BIBLIOGRAPHY}: {key} has no DOI, arXiv id, URL or ISBN: "
                "check it exists (a thesis or report added by hand in Zotero is fine)"
            )


def _citations(inquiry: Inquiry, known: set[str], report: Report) -> None:
    """Every `[@citekey]` of `docs/` names a known entry; a number beside a citation
    without a locator is a warning.
    """
    for note in _notes(inquiry.path):
        relative = _relative(inquiry, note)
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
                group for group in groups if not re.search(r"@[\w:.+/-]+\s*,\s*\S", group)
            ]
            if not bare:
                continue
            rest = re.sub(r"^\s*(\d+\.|[-*])\s+", "", line)
            rest = re.sub(r"\[[^\]]*\]\([^)]*\)|https?://\S+", "", rest)
            rest = _GROUP.sub("", rest)
            numbers = [found for found in _NUMBER.findall(rest) if not _YEAR.fullmatch(found)]
            if numbers:
                report.warnings.append(
                    f"{relative}:{number}: {numbers[0]} beside {bare[0]}, which gives no page"
                )


# Findings: the format, the denominator, the review and approval, and rule 11.


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


def _show(clone: Path, sha: str, path: str) -> str | None:
    try:
        return git("show", f"{sha}:{path}", cwd=clone)
    except GitError:
        return None


def _phase_type(clone: Path, sha: str, phase: str) -> str | None:
    """The type a phase's configuration declares at a commit, or None if it cannot be read."""
    try:
        config = yaml.safe_load(_show(clone, sha, f"phases/{phase}/{protocol.CONFIG}") or "") or {}
    except yaml.YAMLError:
        return None
    return config.get("type") if isinstance(config, dict) else None


def _origin(folder: Path) -> str | None:
    try:
        return git("remote", "get-url", "origin", cwd=folder).strip()
    except GitError:
        return None


class _Clones:
    """Evidence permalinks checked against the clones of the inquiry and its sub-inquiries."""

    def __init__(self, inquiry: Inquiry) -> None:
        self.clones: dict[str, Path] = {}
        for url, path in [
            (_origin(inquiry.path), inquiry.path),
            *((child.url, inquiry.child_path(child.name)) for child in inquiry.children),
        ]:
            if url and (path / ".git").exists():
                self.clones[url.removesuffix(".git")] = path

    def check(self, value: str, where: str, report: Report) -> list[tuple[Path, str, str]]:
        """Check every permalink in `value`; returns the readable ones as (clone, sha, path)."""
        found = []
        for match in _PERMALINK.finditer(value):
            clone = self.clones.get(match["url"].removesuffix(".git"))
            if clone is None:
                continue
            path = match["path"] if match["kind"] == "blob" else None
            if not _commit_exists(clone, match["sha"], path):
                report.failures.append(
                    f"{where}: {match['sha'][:12]}{':' + path if path else ''} is not in "
                    f"the clone of {clone.name}: a wrong permalink, or pull it"
                )
                continue
            found.append((clone, match["sha"], match["path"] or ""))
        return found


def _evidence_item(item: object, where: str, clones: _Clones, report: Report) -> str | None:
    """Check one evidence item; returns its phase type when it counts toward `confirmed`,
    or `sub-inquiry:<status>` for a child's finding.
    """
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
    if kind == "sub-inquiry" and item["status"] not in STATUSES:
        report.failures.append(f"{where}: status is {item['status']!r}, not a finding status")
        return None
    for field in PERMALINKS.get(kind, ()):
        if not _PERMALINK.search(str(item[field])):
            report.failures.append(
                f"{where}: {field} must be a permalink at a commit (/-/blob/<sha>/...)"
            )
    for value in item.values():
        for clone, sha, path in clones.check(str(value), where, report):
            # The phase a run's note belongs to declares its type at that commit.
            if kind == "run" and (note := _PHASE_NOTE.fullmatch(path)):
                declared = _phase_type(clone, sha, note[1])
                if declared is not None and declared != phase:
                    report.failures.append(
                        f"{where}: says phase {phase}, but phase {note[1]} is {declared} "
                        f"at {sha[:12]}"
                    )
            # A child's finding is cited with its status at that commit.
            if kind == "sub-inquiry" and path:
                child = _front_matter(_show(clone, sha, path) or "") or {}
                if child.get("status") not in (None, item["status"]):
                    report.failures.append(
                        f"{where}: says the sub-inquiry's finding is {item['status']}, "
                        f"but it is {child.get('status')} at {sha[:12]}"
                    )
    if kind == "sub-inquiry":
        return f"sub-inquiry:{item['status']}"
    return phase if kind in CONFIRMING else None


def _datasets(inquiry: Inquiry) -> dict[str, set[str]]:
    """The checksums each dataset name has in the tree's resource manifests."""
    found: dict[str, set[str]] = {}
    for member in inquiries.tree(inquiry):
        try:
            listed = resources.load(member.path)
        except resources.ResourceError:
            continue
        for data in listed.data:
            found.setdefault(data.name, set()).add(data.sha256)
    return found


def _findings(inquiry: Inquiry, known: set[str], report: Report) -> None:
    """Each finding's front matter against `docs/findings/finding-format.md`."""
    clones = _Clones(inquiry)
    datasets = _datasets(inquiry)
    folder = inquiry.path / FINDINGS
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
        tried = data.get("tried")
        if not isinstance(tried, int) or isinstance(tried, bool) or tried < 1:
            report.failures.append(
                f"{where}: tried must be the number of variants, analyses or runs tried "
                "to reach the claim (rule 10)"
            )
        evidence = data.get("evidence")
        if not isinstance(evidence, list) or not evidence:
            report.failures.append(f"{where}: evidence must be a list of items")
            evidence = []
        counted = []
        for index, item in enumerate(evidence):
            counted.append(_evidence_item(item, f"{where} evidence {index + 1}", clones, report))
            if not isinstance(item, dict):
                continue
            if (
                item.get("kind") in ("source", "reproduction")
                and item.get("citekey")
                and str(item["citekey"]) not in known
            ):
                report.failures.append(
                    f"{where} evidence {index + 1}: {item['citekey']} is not in "
                    f"{resources.BIBLIOGRAPHY}"
                )
            if item.get("kind") == "measurement" and item.get("dataset"):
                sums = datasets.get(str(item["dataset"]))
                if sums is None:
                    report.warnings.append(
                        f"{where} evidence {index + 1}: dataset {item['dataset']} is in "
                        f"no {resources.FILENAME} of the tree"
                    )
                elif str(item["sha256"]).lower() not in sums:
                    report.failures.append(
                        f"{where} evidence {index + 1}: dataset {item['dataset']} has "
                        f"another sha256 in {resources.FILENAME}"
                    )
        if status == "superseded":
            successor = data.get("superseded_by")
            if not successor:
                report.failures.append(f"{where}: a superseded finding names its superseded_by")
            elif not (folder / str(successor)).is_file():
                report.failures.append(f"{where}: superseded_by {successor} does not exist")
        reviewed = data.get("reviewed")
        if reviewed is not None and (
            not isinstance(reviewed, dict)
            or reviewed.get("verdict") not in VERDICTS
            or not reviewed.get("date")
        ):
            report.failures.append(
                f"{where}: reviewed needs a date and a verdict, one of {', '.join(VERDICTS)}"
            )
        if status != "confirmed":
            continue
        children = [entry.split(":", 1)[1] for entry in counted if entry and ":" in entry]
        if "confirm" not in counted and not children:
            report.failures.append(
                f"{where}: confirmed needs evidence from a confirm phase other than "
                "legacy or source, or confirmed sub-inquiry findings"
            )
        if weaker := [found for found in children if found != "confirmed"]:
            report.failures.append(
                f"{where}: confirmed, but rests on a sub-inquiry finding that is "
                f"{weaker[0]}: the tree never strengthens a claim (rule 11)"
            )
        if not isinstance(reviewed, dict) or reviewed.get("verdict") != "upheld":
            report.failures.append(
                f"{where}: confirmed needs a review-finding verdict of upheld in reviewed"
            )
        if not data.get("approved"):
            report.failures.append(
                f"{where}: confirmed needs the date the user approved it in approved (rule 12)"
            )


# Phases, rule packs, and the rigour pack's freezes and environments.


def _phases(inquiry: Inquiry, rigour: bool, report: Report) -> None:
    """Each phase folder has its note, a type and a level; with the rigour pack, a confirm
    phase is frozen at its protocol.
    """
    plan_file = inquiry.path / protocol.PLAN
    plan = plan_file.read_text(encoding="utf-8") if plan_file.is_file() else ""
    phases = inquiry.path / "phases"
    for folder in sorted(phases.iterdir()) if phases.is_dir() else []:
        if not folder.is_dir() or not _PHASE.fullmatch(folder.name):
            continue
        name = folder.name
        if not (inquiry.path / f"{WIKI}/phases/{name}.md").is_file():
            report.failures.append(f"phases/{name} has no note {WIKI}/phases/{name}.md")
        try:
            config = yaml.safe_load((folder / protocol.CONFIG).read_text(encoding="utf-8")) or {}
        except (OSError, yaml.YAMLError):
            config = None
        if not isinstance(config, dict) or config.get("type") not in PHASE_TYPES:
            report.failures.append(
                f"phases/{name}/{protocol.CONFIG} declares no type: explore or confirm"
            )
            continue
        if config.get("consolidation") not in LEVELS:
            report.failures.append(
                f"phases/{name}/{protocol.CONFIG} declares no consolidation: "
                f"{', '.join(LEVELS)} (rule 2)"
            )
        if config["type"] != "confirm" or not rigour:
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


def _rule_packs(inquiry: Inquiry, report: Report) -> None:
    """Each selected pack is in `rules/`, and every pack the parent selected is kept."""
    for pack in inquiry.rule_packs:
        if not (inquiry.path / "rules" / f"{pack}.md").is_file():
            report.failures.append(
                f"{inquiries.FILENAME} selects the rule pack {pack}, not in rules/"
            )
    if inquiry.parent_path is not None:
        parent = inquiries.load(inquiry.parent_path)
        for pack in parent.rule_packs:
            if pack not in inquiry.rule_packs:
                report.failures.append(
                    f"the parent selects the rule pack {pack}: a sub-inquiry keeps it"
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


def _environments(folder: Path, report: Report) -> None:
    """Each declared conda environment that exists here matches its pinned file."""
    files = sorted((folder / "environments").glob("*.yml"))
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


def check_inquiry(inquiry: Inquiry) -> Report:
    """The problems of one inquiry."""
    report = Report([], [])
    known = _known(inquiry)
    _links(inquiry, report)
    _routes(inquiry, report)
    _citations(inquiry, known, report)
    _identifiers(inquiry, report)
    _findings(inquiry, known, report)
    _phases(inquiry, "rigour" in inquiry.rule_packs, report)
    _rule_packs(inquiry, report)
    if "rigour" in inquiry.rule_packs:
        _environments(inquiry.path, report)
    return report


def check(members: list[Inquiry]) -> tuple[list[str], bool]:
    """Check each inquiry of `members`; returns the report lines and whether nothing failed."""
    lines, ok = [], True
    for member in members:
        report = check_inquiry(member)
        ok = ok and not report.failures
        lines += report.lines(member.label)
    return lines, ok
