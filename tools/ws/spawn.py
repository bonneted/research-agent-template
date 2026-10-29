"""`ws spawn`: create a study from the template and the overlay, and register it."""

import re
import shutil
import tomllib
from pathlib import Path

from ws import manifest, zotero
from ws.git import GitError, git
from ws.manifest import Repository, Workspace
from ws.sync import AGENT_SKILLS, CLAUDE_SKILLS, STUDY_INDEX, symlink, sync

# The hub folder holding the overlay: files copied onto the template, `{{key}}` filled in.
OVERLAY = "overlay"
# Where a study keeps its copy of the rule packs, and of ws's protocol freeze.
RULES = "rules"
PROTOCOL = "study/protocol.py"
# What the template has and a study replaces: the pool's link takes the place of
# `resources/`, the shared `study/` package that of the template's `src/`, the hub's
# `ws fetch` and `ws refs` that of the template's own fetch step and its tests, and
# the study's own `pyproject.toml` that of the template's, with its lock.
_REPLACED = (
    "resources/README.md",
    "src",
    "talk",
    "tools/fetch",
    "tests/conftest.py",
    "tests/fakes.py",
    "tests/test_fetch.py",
    "tests/test_refs.py",
    "tests/test_retrieve.py",
    "tests/zotero-fields.json",
    "uv.lock",
)
_WORDING = {
    "projects": "studies",
    "Projects": "Studies",
    "project": "study",
    "Project": "Study",
}
_TOPIC = re.compile(r"[a-z0-9]+(-[a-z0-9]+)*")
# The study's Python when the library does not say: the overlay's own floor.
_PYTHON = ">=3.11"
_BLOCK = re.compile(r"^# \{\{(\w+)\}\}\n", re.MULTILINE)


class SpawnError(Exception):
    """The study could not be spawned; nothing was left behind."""


def _reword(study: Path, values: dict[str, str]) -> None:
    """Say 'study' wherever the template's prose says 'project', and send its fetch and
    refs commands to the hub.

    Only Markdown: in code and configuration the word can be a key or part of a URL.
    """
    pattern = re.compile(rf"\b({'|'.join(_WORDING)})\b")
    hub = f"uv run --directory ../{values['hub']} ws refs"
    commands = {
        "`uv run fetch`": "`uv run ws fetch` in the hub",
        "`uv run refs add": f"`{hub} add --repo {values['study']}",
        "`uv run refs pull`": f"`{hub} pull --repo {values['study']}`",
        "`uv run refs`": "`ws refs` in the hub",
    }
    for name in git("ls-files", "--", "*.md", cwd=study).splitlines():
        file = study / name
        if file.is_symlink() or not file.is_file():
            continue
        text = file.read_text(encoding="utf-8")
        reworded = pattern.sub(lambda match: _WORDING[match[1]], text)
        for old, new in commands.items():
            reworded = reworded.replace(old, new)
        if reworded != text:
            file.write_text(reworded, encoding="utf-8")


def _tracked(folder: Path) -> list[str]:
    """The files git tracks under `folder`, relative to it: running the overlay's tests
    in place leaves bytecode there.
    """
    if not folder.is_dir():
        return []
    names = git("ls-files", "-z", cwd=folder).split("\0")
    return sorted(name for name in names if name and (folder / name).is_file())


def _overlay(
    study: Path, hub: Path, workspace: Workspace, values: dict[str, str]
) -> None:
    """Turn a fresh clone of the template into a study, and commit it."""
    git("rm", "-r", "--quiet", "--ignore-unmatch", "--", *_REPLACED, cwd=study)
    _reword(study, values)
    overlay = hub / OVERLAY
    for name in _tracked(overlay):
        text = (overlay / name).read_text(encoding="utf-8")
        # A line that is only `# {{key}}` takes a block of lines, or nothing, so the
        # overlay's files stay valid TOML and Python as they are.
        text = _BLOCK.sub(lambda match: values[match[1]], text)
        for key, value in values.items():
            text = text.replace(f"{{{{{key}}}}}", value)
        target = study / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
    # The protocol freeze is ws's own, so the stamp and `ws check` hash alike.
    shutil.copyfile(Path(__file__).with_name("protocol.py"), study / PROTOCOL)
    # The study keeps the rule packs it answers to; a hub change reaches it only by a
    # copy logged as a deviation.
    packs = hub / workspace.rule_packs_dir
    for name in _tracked(packs):
        target = study / RULES / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(packs / name, target)
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
        f"Spawn {study.name} from the template and the {workspace.name} overlay",
        cwd=study,
    )


def _collection(
    workspace: Workspace, name: str, library: zotero.Library | None
) -> str:
    """Create the study's Zotero collection; returns what was done, or what is left to do."""
    parent = workspace.zotero_root
    path = f"{parent}/{name}"
    reason = ""
    if library is None:
        library, reason = zotero.configured(workspace=workspace.name)
    if library is not None:
        try:
            top = library.collection([parent]) or library.create_collection(parent)
            if library.collection([parent, name]) is None:
                library.create_collection(name, top)
            return f"{name}: Zotero collection {path} created"
        except zotero.ZoteroError as error:
            reason = str(error)
    return f"{name}: create the Zotero collection {path}, where `ws refs` keeps its references ({reason})"


def _pin(root: Path, workspace: Workspace) -> dict[str, str]:
    """The overlay's values that pin the library at its default branch's commit; none for
    a workspace without a library.
    """
    if workspace.library is None:
        return {
            "library": "",
            "library_url": "",
            "library_commit": "",
            "library_dependency": "",
            "library_source": "",
            "requires_python": f'requires-python = "{_PYTHON}"\n',
        }
    library = workspace.repository(workspace.library)
    if library is None:
        raise SpawnError(
            f"the library {workspace.library} is not in {manifest.FILENAME} yet: "
            "add it before spawning a study that pins it"
        )
    try:
        head = git("ls-remote", library.url, "HEAD", cwd=root).split()
    except GitError as error:
        raise SpawnError(f"could not read the library's commit: {error}") from error
    if not head:
        raise SpawnError(f"{library.url} has no default branch to pin")
    commit = head[0]
    python = _requires_python(root / library.name, commit)
    return {
        "requires_python": f'requires-python = "{python}"\n',
        "library": library.name,
        "library_url": library.url,
        "library_commit": commit,
        "library_dependency": f'    "{library.name}",\n',
        "library_source": (
            "# The pin: the library commit this study runs on. Moving it is a deviation\n"
            "# logged in PLAN.md, followed by the canary runs.\n"
            "[tool.uv.sources]\n"
            f'{library.name} = {{ git = "{library.url}", rev = "{commit}" }}\n'
        ),
    }


def _requires_python(clone: Path, commit: str) -> str:
    """The library's `requires-python` at the pinned commit, read from its clone beside
    the hub, so that the study resolves on the same Python; the overlay's floor when the
    clone is missing, lacks the commit, or does not say.
    """
    try:
        text = git("show", f"{commit}:pyproject.toml", cwd=clone)
    except (GitError, OSError):
        return _PYTHON
    try:
        project = tomllib.loads(text).get("project", {})
    except tomllib.TOMLDecodeError:
        return _PYTHON
    value = project.get("requires-python")
    return value if isinstance(value, str) and value else _PYTHON


def spawn(
    hub: Path, topic: str, library: zotero.Library | None = None
) -> tuple[list[str], bool]:
    """Create the study `<workspace>-<topic>` beside the hub, register it, and sync.

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
    workspace = manifest.load(hub)
    name = f"{workspace.name}-{topic}"
    if workspace.repository(name) is not None:
        raise SpawnError(f"{name} is already in {manifest.FILENAME}")
    study = root / name
    if study.exists() or study.is_symlink():
        raise SpawnError(f"{name} already exists in {root}")
    pin = _pin(root, workspace)
    url = workspace.url(name)
    template = manifest.template(hub)
    values = {
        "study": name,
        "workspace": workspace.name,
        "hub": workspace.hub.name,
        "hub_url": workspace.hub.url,
        "runs_env": f"{name.upper().replace('-', '_')}_RUNS",
        "zotero_root": workspace.zotero_root,
        "stamp_extras": workspace.stamp_extras or "",
        **pin,
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
        _overlay(study, hub, workspace, values)
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
    pinned = (
        f"library pinned at {pin['library_commit'][:12]}"
        if pin["library"]
        else "no library to pin"
    )
    lines = [
        f"{name}: spawned from the template, {pinned}",
        (
            f"{name}: registered in {manifest.FILENAME} and {STUDY_INDEX}: "
            "write its question there, and commit both in the hub"
        ),
        (
            f"{name}: to push it, create {web} on GitLab, then: "
            f"git -C ../{name} push -u origin HEAD"
        ),
        _collection(workspace, name, library),
    ]
    synced, ok = sync(root, manifest.load(hub))
    return lines + synced, ok
