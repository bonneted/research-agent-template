"""`ws spawn`: create a study from the template and the overlay, and register it."""

import re
import shutil
from pathlib import Path

from ws import manifest, refs, zotero
from ws.git import GitError, git
from ws.manifest import Repository
from ws.sync import AGENT_SKILLS, CLAUDE_SKILLS, STUDY_INDEX, symlink, sync

# The hub folder holding the overlay: files copied onto the template, `{{key}}` filled in.
OVERLAY = "overlay"
# What the template has and a study replaces: the pool's link takes the place of
# `resources/`, the shared `study/` package that of the template's `src/`, and the hub's
# `ws fetch` that of the template's own fetch step and its tests.
_REPLACED = (
    "resources/README.md",
    "src",
    "tools/fetch",
    "tests/conftest.py",
    "tests/test_fetch.py",
    "tests/test_retrieve.py",
)
_WORDING = {
    "projects": "studies",
    "Projects": "Studies",
    "project": "study",
    "Project": "Study",
}
_TOPIC = re.compile(r"[a-z0-9]+(-[a-z0-9]+)*")


class SpawnError(Exception):
    """The study could not be spawned; nothing was left behind."""


def _reword(study: Path, hub: str) -> None:
    """Say 'study' wherever the template's prose says 'project', and send its fetch to the hub.

    Only Markdown: in code and configuration the word can be a key or part of a URL.
    """
    pattern = re.compile(rf"\b({'|'.join(_WORDING)})\b")
    fetch = "`uv run ws fetch` in the hub"
    for name in git("ls-files", "--", "*.md", cwd=study).splitlines():
        file = study / name
        if file.is_symlink() or not file.is_file():
            continue
        text = file.read_text(encoding="utf-8")
        reworded = pattern.sub(lambda match: _WORDING[match[1]], text)
        reworded = reworded.replace("`uv run fetch`", fetch)
        if reworded != text:
            file.write_text(reworded, encoding="utf-8")


def _overlay(study: Path, overlay: Path, values: dict[str, str]) -> None:
    """Turn a fresh clone of the template into a study, and commit it."""
    git("rm", "-r", "--quiet", "--ignore-unmatch", "--", *_REPLACED, cwd=study)
    _reword(study, values["hub"])
    # Only what git tracks in the hub: running the overlay's tests in place leaves bytecode there.
    tracked = git("ls-files", "-z", cwd=overlay).split("\0")
    for name in sorted(filter(None, tracked)):
        source = overlay / name
        if not source.is_file():
            continue
        text = source.read_text(encoding="utf-8")
        for key, value in values.items():
            text = text.replace(f"{{{{{key}}}}}", value)
        target = study / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
    # Claude Code reads the study's skills through a link, so an edited skill is never stale.
    claude = study / CLAUDE_SKILLS
    if claude.is_dir() and not claude.is_symlink():
        shutil.rmtree(claude)
    symlink(claude, study / AGENT_SKILLS)
    git("add", "--all", cwd=study)
    git(
        "commit",
        "--quiet",
        "-m",
        f"Spawn {study.name} from the template and the spimat overlay",
        cwd=study,
    )


def _collection(name: str, library: zotero.Library | None) -> str:
    """Create the study's Zotero collection; returns what was done, or what is left to do."""
    path = f"{refs.PARENT}/{name}"
    reason = ""
    if library is None:
        library, reason = zotero.configured()
    if library is not None:
        try:
            parent = library.collection([refs.PARENT]) or library.create_collection(
                refs.PARENT
            )
            if library.collection([refs.PARENT, name]) is None:
                library.create_collection(name, parent)
            return f"{name}: Zotero collection {path} created"
        except zotero.ZoteroError as error:
            reason = str(error)
    return f"{name}: create the Zotero collection {path}, where `ws refs` keeps its references ({reason})"


def spawn(
    hub: Path, topic: str, library: zotero.Library | None = None
) -> tuple[list[str], bool]:
    """Create the study `spimat-<topic>` beside the hub, register it, and sync.

    Its Zotero collection is created in `library`, by default the user's configured
    one; without one, or with a read-only key, the researcher is told to create it.

    Raises `SpawnError`, leaving the workspace as it was, if the study cannot be made.
    Returns the report lines and the sync's success.
    """
    if not _TOPIC.fullmatch(topic):
        raise SpawnError(
            f"{topic!r}: a topic is lowercase letters and digits, joined by dashes (mt2)"
        )
    root = hub.parent
    repositories = manifest.load(hub)
    name = f"spimat-{topic}"
    if any(repository.name == name for repository in repositories):
        raise SpawnError(f"{name} is already in {manifest.FILENAME}")
    study = root / name
    if study.exists() or study.is_symlink():
        raise SpawnError(f"{name} already exists in {root}")
    roles = {repository.role: repository for repository in repositories}
    if "library" not in roles:
        raise SpawnError(f"{manifest.FILENAME} lists no library to pin")
    library_repository, hub_repository = roles["library"], roles["hub"]
    try:
        head = git("ls-remote", library_repository.url, "HEAD", cwd=root).split()
    except GitError as error:
        raise SpawnError(f"could not read the library's commit: {error}") from error
    if not head:
        raise SpawnError(f"{library_repository.url} has no default branch to pin")
    commit = head[0]
    # A study lives next to the hub on GitLab.
    url = f"{hub_repository.url.rsplit('/', 1)[0]}/{name}.git"
    template = manifest.template(hub)
    values = {
        "study": name,
        "hub": hub_repository.name,
        "hub_url": hub_repository.url,
        "library_url": library_repository.url,
        "library_commit": commit,
        "runs_env": f"{name.upper().replace('-', '_')}_RUNS",
    }
    index = hub / STUDY_INDEX
    indexed = index.is_file()
    index_text = index.read_text(encoding="utf-8") if indexed else ""
    web = url.removesuffix(".git")
    try:
        git("clone", "--quiet", "--origin", "template", template, str(study), cwd=root)
        # Until the study is pushed to its own remote, it has nothing to compare with.
        git("branch", "--unset-upstream", cwd=study)
        git("remote", "add", "origin", url, cwd=study)
        _overlay(study, hub / OVERLAY, values)
        index.parent.mkdir(parents=True, exist_ok=True)
        index.write_text(
            index_text
            + ("" if not index_text or index_text.endswith("\n") else "\n")
            + f"- **{name}**: <its question, from its PLAN.md> ([GitLab]({web})).\n",
            encoding="utf-8",
        )
        manifest.add(hub, Repository(name, url, "study"))
    except (GitError, OSError, manifest.ManifestError) as error:
        shutil.rmtree(study, ignore_errors=True)
        if indexed:
            index.write_text(index_text, encoding="utf-8")
        else:
            index.unlink(missing_ok=True)
        reason = getattr(error, "strerror", None) or error
        raise SpawnError(f"could not spawn {name}: {reason}") from error
    lines = [
        f"{name}: spawned from the template, library pinned at {commit[:12]}",
        f"{name}: registered in {manifest.FILENAME} and {STUDY_INDEX}: "
        "write its question there, and commit both in the hub",
        f"{name}: to push it, create {web} on GitLab, then: "
        f"git -C ../{name} push -u origin HEAD",
        _collection(name, library),
    ]
    synced, ok = sync(root, manifest.load(hub))
    return lines + synced, ok
