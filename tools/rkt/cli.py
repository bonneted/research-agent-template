"""Command line of the knowledge tree's tool, `rkt`."""

import argparse
import sys
from pathlib import Path

from rkt import inquiry, kit, lookup, protocol, refs, resources, zotero
from rkt.check import check
from rkt.fetch import fetch


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="rkt", description="References, resources and checks of a knowledge tree."
    )
    parser.add_argument("--version", action="version", version=f"rkt {kit.version()}")
    commands = parser.add_subparsers(dest="command", required=True)
    starter = commands.add_parser("init", help="make a folder an inquiry from the kit")
    starter.add_argument("folder", nargs="?", default=".", type=Path)
    starter.add_argument("--question", default="", help="the inquiry's question")
    fetcher = commands.add_parser(
        "fetch",
        help="pull references.bib from Zotero, bring every listed resource into the pool, "
        "link resources/ to it, and list what is missing",
    )
    fetcher.add_argument(
        "--tree",
        action="store_true",
        help="also every sub-inquiry cloned below this one",
    )
    checker = commands.add_parser(
        "check",
        help="check links, indexes, routes, findings, citations and phases against the rules",
    )
    checker.add_argument(
        "--tree",
        action="store_true",
        help="also every sub-inquiry cloned below this one",
    )
    freezer = commands.add_parser(
        "freeze", help="rigour pack: record the hash of a confirm phase's protocol"
    )
    freezer.add_argument("phase", help="the phase folder, such as phases/02-burst")
    references = commands.add_parser(
        "refs", help="the inquiry's references.bib: never written by hand"
    )
    actions = references.add_subparsers(dest="action", required=True)
    actions.add_parser("pull", help="rewrite references.bib from the Zotero collection")
    adder = actions.add_parser(
        "add",
        help="add a reference by its DOI, arXiv identifier, or a doi.org or arxiv.org URL",
    )
    adder.add_argument("identifier", help="a DOI, an arXiv identifier, or a URL to one")
    return parser


def _members(arguments: argparse.Namespace) -> list[inquiry.Inquiry]:
    top = inquiry.load(inquiry.find(Path.cwd()))
    return inquiry.tree(top) if arguments.tree else [top]


def _refs(arguments: argparse.Namespace) -> tuple[list[str], bool]:
    here = inquiry.load(inquiry.find(Path.cwd()))
    identifier = None
    if arguments.action == "add":
        # Refused before Zotero is asked: an agent never cites what has no identifier.
        try:
            identifier = lookup.identify(arguments.identifier)
        except lookup.Refused as error:
            return [f"{here.label}: FAILED: {error}"], False
    if not here.zotero_collection:
        # Bib-only: the inquiry keeps references.bib itself, through refs add.
        if identifier is None:
            return [
                (
                    f"{here.label}: no zotero_collection in {inquiry.FILENAME}: "
                    f"{resources.BIBLIOGRAPHY} is kept by `rkt refs add`, nothing to pull"
                )
            ], True
        return refs.add_to_bibliography(here, identifier)
    library, reason = zotero.configured()
    if library is None:
        return [
            (
                f"{here.label}: FAILED: {reason}; configure Zotero, or remove "
                f"zotero_collection from {inquiry.FILENAME} to keep {resources.BIBLIOGRAPHY} "
                "without it"
            )
        ], False
    try:
        if identifier is None:
            return refs.pull(here, library)
        return refs.add(here, identifier, library)
    except zotero.ZoteroError as error:
        return [f"{here.label}: FAILED: {error}"], False


def _freeze(arguments: argparse.Namespace) -> tuple[list[str], bool]:
    here = inquiry.find(Path.cwd())
    phase = (Path.cwd() / arguments.phase).resolve()
    try:
        return [protocol.freeze(phase, here / protocol.PLAN)], True
    except protocol.ProtocolError as error:
        return [f"FAILED: {error}"], False


def main(argv: list[str] | None = None) -> int:
    """Run an `rkt` command; returns the exit code."""
    arguments = _parser().parse_args(argv)
    try:
        if arguments.command == "init":
            lines, ok = kit.init(arguments.folder.resolve(), arguments.question)
        elif arguments.command == "fetch":
            lines, ok = fetch(_members(arguments))
        elif arguments.command == "check":
            lines, ok = check(_members(arguments))
        elif arguments.command == "freeze":
            lines, ok = _freeze(arguments)
        else:
            lines, ok = _refs(arguments)
    except inquiry.InquiryError as error:
        print(f"rkt: {error}", file=sys.stderr)
        return 2
    print("\n".join(lines))
    return 0 if ok else 1
