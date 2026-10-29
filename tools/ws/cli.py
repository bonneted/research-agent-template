"""Command line of the workspace tool."""

import argparse
import sys
from pathlib import Path

from ws import lookup, manifest, refs, zotero
from ws.fetch import fetch
from ws.spawn import SpawnError, spawn
from ws.sync import sync


def main(argv: list[str] | None = None) -> int:
    """Run a `ws` command; returns the exit code."""
    parser = argparse.ArgumentParser(
        prog="ws", description="Build and check the spimat workspace."
    )
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser(
        "sync",
        help="clone missing repositories, write the library's local agent files, "
        "link each to the resource pool and the hub skills, and report dirty or behind ones",
    )
    commands.add_parser(
        "fetch",
        help="retrieve missing PDFs, clone code resources into the pool at their commit, check data checksums, "
        "and list what is missing with a command to copy it in",
    )
    spawner = commands.add_parser(
        "spawn",
        help="create the study spimat-<topic> from the template and the overlay, "
        "pin the library, register the study, and sync",
    )
    spawner.add_argument("topic", help="the study's short name: mt2 gives spimat-mt2")
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
    arguments = parser.parse_args(argv)

    try:
        hub = manifest.find_hub(Path.cwd())
        if arguments.command == "spawn":
            lines, ok = spawn(hub, arguments.topic)
        elif arguments.command == "refs":
            lines, ok = _refs(hub, arguments)
        else:
            command = {"sync": sync, "fetch": fetch}[arguments.command]
            lines, ok = command(hub.parent, manifest.load(hub))
    except (manifest.ManifestError, SpawnError) as error:
        print(f"ws: {error}", file=sys.stderr)
        return 2
    print("\n".join(lines))
    return 0 if ok else 1


def _refs(hub: Path, arguments: argparse.Namespace) -> tuple[list[str], bool]:
    root, repositories = hub.parent, manifest.load(hub)
    name = arguments.repo or manifest.repository_at(root, repositories, Path.cwd())
    if name not in [repository.name for repository in repositories]:
        raise manifest.ManifestError(f"{name} is not in {manifest.FILENAME}")
    if arguments.action == "add":
        try:
            identifier = lookup.identify(arguments.identifier)
        except lookup.Refused as error:
            return [f"{name}: FAILED: {error}"], False
    library, reason = zotero.configured()
    if library is None:
        return [f"{name}: FAILED: {reason}"], False
    try:
        if arguments.action == "add":
            return refs.add(root, repositories, name, identifier, library)
        return refs.pull(root, repositories, name, library)
    except zotero.ZoteroError as error:
        return [f"{name}: FAILED: {error}"], False
