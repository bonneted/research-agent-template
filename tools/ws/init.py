"""`ws init`: start a workspace, its hub made from this template."""

import re
import shutil
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from ws import manifest
from ws.git import GitError, git
from ws.manifest import NAME
from ws.sync import sync

# The template's folder of the hub's own text at birth, `{{key}}` filled in: each file
# replaces the opening (the text before the first `## ` heading) of the hub's file at
# the same path, or is the whole file where the hub has none.
SKELETON = "skeleton"
# The remote of the hub that names the template, for its fixes to reach the hub by merge.
REMOTE = "ws-template"
# The template studies are spawned from, unless the template ws runs from names another.
STUDY_TEMPLATE = (
    "https://gitlab.kuleuven.be/r2d/collaboration/research-agent-template.git"
)


class InitError(Exception):
    """The workspace could not be started; nothing was left behind."""


@dataclass
class Settings:
    """What `ws init` asks for, or takes as flags."""

    name: str
    gitlab: str
    zotero_root: str | None = None
    library: str | None = None
    stamp_extras: str | None = None
    rule_packs_dir: str = "rules"
    off_limits: dict = field(default_factory=dict)
    # The template's URL for the hub's `ws-template` remote; the study template's URL.
    template_url: str | None = None
    study_template: str | None = None


def source() -> Path:
    """The template `ws` runs from: the git checkout holding this package."""
    return Path(__file__).resolve().parents[2]


def _remote(repository: Path, name: str) -> str | None:
    try:
        return git("remote", "get-url", name, cwd=repository).strip() or None
    except GitError:
        return None


def _opening(text: str) -> tuple[str, str]:
    """A Markdown text split before its first `## ` heading."""
    match = re.search(r"^## ", text, re.MULTILINE)
    return (text, "") if match is None else (text[: match.start()], text[match.start() :])


def _fill(text: str, values: dict[str, str]) -> str:
    for key, value in values.items():
        text = text.replace(f"{{{{{key}}}}}", value)
    return text


def _skeleton(hub: Path, values: dict[str, str]) -> None:
    """Put the skeleton's text into the hub."""

    names = git("ls-files", "-z", "--", SKELETON, cwd=hub).split("\0")
    for name in sorted(filter(None, names)):
        text = _fill((hub / name).read_text(encoding="utf-8"), values)
        target = hub / _fill(str(Path(name).relative_to(SKELETON)), values)
        if target.is_file():
            _, rest = _opening(target.read_text(encoding="utf-8"))
            opening, _ = _opening(text)
            text = opening + rest
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")



def manifest_text(settings: Settings, hub_url: str, study_template: str) -> str:
    """The new hub's `workspace.yaml`."""
    block = {"name": settings.name, "gitlab": settings.gitlab}
    block["zotero_root"] = settings.zotero_root or settings.name
    if settings.library:
        block["library"] = settings.library
    if settings.stamp_extras:
        block["stamp_extras"] = settings.stamp_extras
    block["rule_packs_dir"] = settings.rule_packs_dir
    if settings.off_limits:
        block["off_limits"] = settings.off_limits
    workspace = yaml.safe_dump(
        {"workspace": block}, sort_keys=False, allow_unicode=True, width=1000
    )
    return (
        f"# The workspace manifest of {settings.name}: every repository of the workspace, "
        "cloned side by side\n"
        "# in the hub's parent folder under `name`. `ws` reads it; the keys are in the "
        "hub's README.\n"
        "# Roles: library, hub, study, app, off-limits. `ws spawn` makes a study from "
        "`template`\n"
        "# and appends it to `repositories`: keep that key last.\n"
        f"{workspace}"
        f"template: {study_template}\n"
        "repositories:\n"
        f"  - name: {settings.name}-hub\n"
        f"    url: {hub_url}\n"
        "    role: hub\n"
    )


def init(root: Path, settings: Settings, template: Path | None = None) -> tuple[list[str], bool]:
    """Create the hub `<name>-hub` in `root` from the template at `template` (by default
    the one `ws` runs from), commit it, and sync the new workspace.

    Raises `InitError`, leaving `root` as it was, if the hub cannot be made.
    Returns the report lines and the sync's success.
    """
    if not NAME.fullmatch(settings.name):
        raise InitError(
            f"{settings.name!r}: a workspace name is lowercase letters and digits, "
            "joined by dashes (copv)"
        )
    if not settings.gitlab:
        raise InitError("give the workspace's GitLab group URL (--gitlab)")
    template = template or source()
    if not (template / ".git").exists():
        raise InitError(f"{template} is not a git checkout of the template")
    hub = root / f"{settings.name}-hub"
    if hub.exists() or hub.is_symlink():
        raise InitError(f"{hub.name} already exists in {root}")
    group = settings.gitlab.rstrip("/")
    hub_url = f"{group}/{hub.name}.git"
    template_url = settings.template_url or _remote(template, "origin") or str(template)
    study_template = (
        settings.study_template or _remote(template, "template") or STUDY_TEMPLATE
    )
    values = {
        "name": settings.name,
        "hub": hub.name,
        "hub_url": hub_url,
        "gitlab": group,
        "library": settings.library or f"{settings.name} (none yet)",
        "zotero_root": settings.zotero_root or settings.name,
        "resources_env": f"{settings.name.upper().replace('-', '_')}_RESOURCES",
    }
    try:
        git("clone", "--quiet", "--origin", REMOTE, str(template), str(hub), cwd=root)
        git("remote", "set-url", REMOTE, template_url, cwd=hub)
        # Until the hub is pushed to its own remote, it has nothing to compare with.
        git("branch", "--unset-upstream", cwd=hub)
        git("remote", "add", "origin", hub_url, cwd=hub)
        _skeleton(hub, values)
        (hub / manifest.FILENAME).write_text(
            manifest_text(settings, hub_url, study_template), encoding="utf-8"
        )
        workspace = manifest.load(hub)
        git("add", "--all", cwd=hub)
        git(
            "commit",
            "--quiet",
            "-m",
            f"Start the {settings.name} workspace from the workspace template",
            cwd=hub,
        )
    except (GitError, OSError, manifest.ManifestError) as error:
        shutil.rmtree(hub, ignore_errors=True)
        reason = getattr(error, "strerror", None) or error
        raise InitError(f"could not start {hub.name}: {reason}") from error
    lines = [
        f"{hub.name}: made from the template, remote {REMOTE} {template_url}",
        (
            f"{hub.name}: to push it, create {hub_url.removesuffix('.git')} on GitLab, "
            f"then: git -C {hub.name} push -u origin HEAD"
        ),
    ]
    synced, ok = sync(root, workspace)
    return lines + synced, ok
