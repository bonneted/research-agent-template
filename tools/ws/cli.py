"""Command line of the workspace tool."""

import argparse
import sys
from pathlib import Path

import yaml

from ws import lookup, manifest, protocol, refs, zotero
from ws.check import check
from ws.fetch import fetch
from ws.init import InitError, Settings, init
from ws.spawn import SpawnError, spawn
from ws.sync import sync


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ws", description="Build and check a research workspace."
    )
    commands = parser.add_subparsers(dest="command", required=True)
    starter = commands.add_parser(
        "init",
        help="start the workspace <name> in the current folder: make <name>-hub from "
        "the template, write its manifest, commit it, and sync",
    )
    starter.add_argument("name", help="the workspace's short name: copv gives copv-hub")
    starter.add_argument("--gitlab", help="the URL of the GitLab group of its repositories")
    starter.add_argument(
        "--zotero-root", help="the Zotero collection holding each repository's (default: the name)"
    )
    starter.add_argument("--library", help="the library studies pin, if there is one")
    starter.add_argument(
        "--stamp-extras", help="module:function adding fields to every run stamp"
    )
    starter.add_argument(
        "--off-limits",
        type=Path,
        help="a YAML file holding the off_limits block (paths, patterns, deny_connectors, repo)",
    )
    starter.add_argument(
        "--off-limits-path", action="append", default=[], help="an off-limits path glob"
    )
    starter.add_argument(
        "--off-limits-pattern",
        action="append",
        default=[],
        help="a regular expression an agent's tool call may not match",
    )
    starter.add_argument(
        "--deny-connector", action="append", default=[], help="a connector to deny"
    )
    starter.add_argument(
        "--off-limits-repo", help="a repository ws clones but never reads"
    )
    starter.add_argument(
        "--template-url", help="the template's URL for the hub's ws-template remote"
    )
    starter.add_argument(
        "--study-template", help="the URL of the template studies are spawned from"
    )
    starter.add_argument(
        "--no-input", action="store_true", help="never ask: take the flags as they are"
    )
    commands.add_parser(
        "sync",
        help="clone missing repositories, link each to the resource pool and the hub skills, "
        "write the off-limits files, and report dirty or behind ones",
    )
    commands.add_parser(
        "fetch",
        help="retrieve missing PDFs, clone code resources into the pool at their commit, check data checksums, "
        "and list what is missing with a command to copy it in",
    )
    spawner = commands.add_parser(
        "spawn",
        help="create the study <workspace>-<topic> from the template and the overlay, "
        "pin the library, register the study, and sync",
    )
    spawner.add_argument("topic", help="the study's short name: in copv, burst gives copv-burst")
    checker = commands.add_parser(
        "check",
        help="check findings, citations, phases, protocol freezes, conda environments "
        "and off-limits files against the workspace's rules",
    )
    checker.add_argument(
        "--repo", help="the repository to check; by default, the one ws is run from"
    )
    checker.add_argument(
        "--all", action="store_true", help="every repository, and the workspace root"
    )
    freezer = commands.add_parser(
        "freeze", help="record the hash of a confirm phase's protocol in its config.yaml"
    )
    freezer.add_argument("phase", help="the phase folder's name, such as 02-burst")
    freezer.add_argument(
        "--repo", help="the study; by default, the one ws is run from"
    )
    references = commands.add_parser(
        "refs", help="a repository's references.bib, written from its Zotero collection"
    )
    actions = references.add_subparsers(dest="action", required=True)
    puller = actions.add_parser(
        "pull",
        help="rewrite references.bib from the repository's Zotero collection",
    )
    puller.add_argument(
        "--repo", help="the repository to pull; by default, the one ws is run from"
    )
    adder = actions.add_parser(
        "add",
        help="add a reference to the repository's Zotero collection from its DOI, "
        "arXiv identifier, or doi.org or arxiv.org URL, and pull",
    )
    adder.add_argument("identifier", help="a DOI, an arXiv identifier, or a URL to one")
    adder.add_argument(
        "--repo", help="the repository to add it to; by default, the one ws is run from"
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run a `ws` command; returns the exit code."""
    arguments = _parser().parse_args(argv)
    try:
        if arguments.command == "init":
            lines, ok = init(Path.cwd(), _settings(arguments))
        else:
            hub = manifest.find_hub(Path.cwd())
            if arguments.command == "spawn":
                lines, ok = spawn(hub, arguments.topic)
            elif arguments.command == "refs":
                lines, ok = _refs(hub, arguments)
            elif arguments.command == "check":
                lines, ok = _check(hub, arguments)
            elif arguments.command == "freeze":
                lines, ok = _freeze(hub, arguments)
            else:
                command = {"sync": sync, "fetch": fetch}[arguments.command]
                lines, ok = command(hub.parent, manifest.load(hub))
    except (manifest.ManifestError, SpawnError, InitError) as error:
        print(f"ws: {error}", file=sys.stderr)
        return 2
    print("\n".join(lines))
    return 0 if ok else 1


def _ask(question: str, default: str | None, interactive: bool) -> str | None:
    if not interactive:
        return default
    answer = input(f"{question}{f' [{default}]' if default else ''}: ").strip()
    return answer or default


def _settings(arguments: argparse.Namespace) -> Settings:
    """The settings of `ws init` from its flags, asking for what is missing on a terminal."""
    interactive = not arguments.no_input and sys.stdin.isatty()
    name = arguments.name
    off_limits: dict = {}
    if arguments.off_limits is not None:
        try:
            off_limits = yaml.safe_load(arguments.off_limits.read_text(encoding="utf-8")) or {}
        except (OSError, yaml.YAMLError) as error:
            raise InitError(f"{arguments.off_limits}: {error}") from error
        if not isinstance(off_limits, dict):
            raise InitError(f"{arguments.off_limits}: expected an off_limits mapping")
        off_limits = off_limits.get("off_limits", off_limits)
    for key, values in (
        ("paths", arguments.off_limits_path),
        ("patterns", arguments.off_limits_pattern),
        ("deny_connectors", arguments.deny_connector),
    ):
        if values:
            off_limits[key] = [*(off_limits.get(key) or []), *values]
    if arguments.off_limits_repo:
        off_limits["repo"] = arguments.off_limits_repo
    if interactive and not off_limits:
        paths = _ask("Off-limits paths, comma-separated (none)", None, True)
        if paths:
            off_limits["paths"] = [path.strip() for path in paths.split(",") if path.strip()]
            repo = _ask("Off-limits repository (none)", None, True)
            if repo:
                off_limits["repo"] = repo
    return Settings(
        name=name,
        gitlab=arguments.gitlab or _ask("GitLab group URL", None, interactive) or "",
        zotero_root=arguments.zotero_root
        or _ask("Zotero collection root", name, interactive),
        library=arguments.library
        or _ask("Library repository (none)", None, interactive),
        stamp_extras=arguments.stamp_extras,
        off_limits=off_limits,
        template_url=arguments.template_url,
        study_template=arguments.study_template,
    )


def _repository(hub: Path, arguments: argparse.Namespace) -> tuple[Path, manifest.Workspace, str]:
    root, workspace = hub.parent, manifest.load(hub)
    name = arguments.repo or manifest.repository_at(root, workspace.repositories, Path.cwd())
    if workspace.repository(name) is None:
        raise manifest.ManifestError(f"{name} is not in {manifest.FILENAME}")
    return root, workspace, name


def _check(hub: Path, arguments: argparse.Namespace) -> tuple[list[str], bool]:
    workspace = manifest.load(hub)
    if arguments.all:
        names = [repository.name for repository in workspace.repositories]
        return check(hub.parent, workspace, names, everything=True)
    _, workspace, name = _repository(hub, arguments)
    return check(hub.parent, workspace, [name])


def _freeze(hub: Path, arguments: argparse.Namespace) -> tuple[list[str], bool]:
    root, workspace, name = _repository(hub, arguments)
    if workspace.repository(name).role != "study":
        return [f"{name}: FAILED: only a study has phases"], False
    study = root / name
    phase = study / "phases" / arguments.phase
    if not phase.is_dir():
        return [f"{name}: FAILED: no phases/{arguments.phase}"], False
    try:
        return [f"{name}: {protocol.freeze(phase, study / protocol.PLAN)}"], True
    except (protocol.ProtocolError, OSError) as error:
        return [f"{name}: FAILED: {error}"], False


def _refs(hub: Path, arguments: argparse.Namespace) -> tuple[list[str], bool]:
    root, workspace, name = _repository(hub, arguments)
    if workspace.repository(name).role == "off-limits":
        return [f"{name}: FAILED: ws never reads the off-limits repository"], False
    if arguments.action == "add":
        try:
            identifier = lookup.identify(arguments.identifier)
        except lookup.Refused as error:
            return [f"{name}: FAILED: {error}"], False
    library, reason = zotero.configured(workspace=workspace.name)
    if library is None:
        return [f"{name}: FAILED: {reason}"], False
    try:
        if arguments.action == "add":
            return refs.add(root, workspace, name, identifier, library)
        return refs.pull(root, workspace, name, library)
    except zotero.ZoteroError as error:
        return [f"{name}: FAILED: {error}"], False
