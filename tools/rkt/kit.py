"""The kit: the files every new inquiry starts from, and `rkt init`, which copies them."""

import importlib.metadata
import re
import shutil
from pathlib import Path

from rkt import inquiry

PACKAGE = "research-knowledge-tree"


def version() -> str:
    try:
        return importlib.metadata.version(PACKAGE)
    except importlib.metadata.PackageNotFoundError:
        return "0+unknown"


def folder() -> Path:
    """The kit's files: in the installed package, or `kit/` of the template's checkout."""
    installed = Path(__file__).with_name("kit")
    return installed if installed.is_dir() else Path(__file__).resolve().parents[2] / "kit"


def files() -> list[Path]:
    """The kit's files, relative to its folder."""
    root = folder()
    return sorted(
        path.relative_to(root)
        for path in root.rglob("*")
        if path.is_file() and "__pycache__" not in path.parts
    )


def init(target: Path, question: str = "") -> tuple[list[str], bool]:
    """Make `target` an inquiry from the kit, without overwriting a file already there.

    Returns the report lines and success.
    """
    if (target / inquiry.FILENAME).exists():
        return [f"{target}: already an inquiry ({inquiry.FILENAME} exists)"], False
    root = folder()
    kept = []
    for relative in files():
        destination = target / relative
        if destination.exists():
            kept.append(relative.as_posix())
            continue
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(root / relative, destination)
    manifest = target / inquiry.FILENAME
    text = manifest.read_text(encoding="utf-8")
    text = re.sub(r'^question: ""', f"question: {question!r}" if question else 'question: ""', text, flags=re.MULTILINE)
    text = re.sub(r"^(  version: )\S+", rf"\g<1>{version()}", text, flags=re.MULTILINE)
    manifest.write_text(text, encoding="utf-8")
    lines = [f"{target}: an inquiry, from kit {version()}"]
    lines += [f"{target}: kept {name}, already there" for name in kept]
    lines += [
        "",
        "Next: open it with your agent and ask it to start the inquiry: it interviews you",
        "on the question and the rules, then fills AGENTS.md, inquiry.yaml and PLAN.md.",
    ]
    return lines, True
