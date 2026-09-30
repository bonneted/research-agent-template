"""`fetch`: bring what the project's resource manifest lists into `resources/`.

It retrieves each document of `references.bib` without a PDF in `resources/papers/`
(see `retrieve`), clones each code resource of `resources.yaml` into
`resources/code/<name>/` at its commit, checks each dataset in `resources/data/`
against its sha256, and ends with the list of what is still missing.
"""

import argparse
import hashlib
import os
import shutil
import subprocess
from pathlib import Path

from fetch import manifest, retrieve

RESOURCES = "resources"

# An HTTPS remote that refuses us (a private project) would otherwise make git wait
# for a password on the terminal instead of failing.
_GIT_ENV = {**os.environ, "GIT_TERMINAL_PROMPT": "0"}


class GitError(Exception):
    """A git command failed; the message is git's reason."""


def git(*args: str, cwd: Path) -> str:
    """Run git in `cwd` and return its output; raise `GitError` with git's reason if it fails."""
    process = subprocess.run(
        ["git", *args],
        cwd=cwd,
        env=_GIT_ENV,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if process.returncode != 0:
        lines = [line.strip() for line in process.stderr.splitlines() if line.strip()]
        fatal = [line for line in lines if line.startswith("fatal:")]
        raise GitError((fatal or lines or [f"git exited with {process.returncode}"])[0])
    return process.stdout


def _commit(clone: Path, commit: str) -> str | None:
    """The full hash of `commit` in `clone`, or None if the clone does not have it."""
    try:
        return git(
            "rev-parse", "--verify", "--quiet", f"{commit}^{{commit}}", cwd=clone
        ).strip()
    except GitError:
        return None


def _clone(code: manifest.Code, resources: Path) -> str | None:
    """Bring `resources/code/<name>` to the commit `code` pins; returns what was done.

    Raises `GitError` if it cannot.
    """
    path = f"code/{code.name}"
    clone = resources / path
    # A new clone is made beside its place and moved in once at its commit, so an
    # interrupted or failed clone never looks like a finished one.
    partial = clone.with_name(f".{code.name}.partial")
    fresh = not clone.exists()
    work = partial if fresh else clone
    try:
        if fresh:
            shutil.rmtree(partial, ignore_errors=True)
            partial.parent.mkdir(parents=True, exist_ok=True)
            git(
                "clone",
                "--quiet",
                "--no-checkout",
                code.url,
                str(partial),
                cwd=partial.parent,
            )
        elif not (clone / ".git").exists():
            raise GitError(f"{clone} exists but is not a git repository")
        commit = _commit(work, code.commit)
        if commit is None and not fresh:
            git("fetch", "--quiet", cwd=work)
            commit = _commit(work, code.commit)
        if commit is None:
            raise GitError(f"commit {code.commit} is not in {code.url}")
        head = None if fresh else git("rev-parse", "HEAD", cwd=work).strip()
        if head == commit:
            return None
        if head is not None and git("status", "--porcelain", cwd=work).strip():
            raise GitError(f"uncommitted changes in the clone, left at {head[:12]}")
        git("-c", "advice.detachedHead=false", "checkout", "--quiet", commit, cwd=work)
        if fresh:
            partial.rename(clone)
    except GitError:
        shutil.rmtree(partial, ignore_errors=True)
        raise
    return f"{path} cloned" if fresh else f"{path} moved to {commit[:12]}"


def _check(data: manifest.Data, file: Path) -> None:
    """Raise `ValueError` if `file` is not the dataset listed."""
    if not file.is_file():
        raise ValueError(f"{file} is not a file")
    with file.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    if digest != data.sha256:
        raise ValueError(
            f"checksum {digest}, {manifest.FILENAME} expects {data.sha256}: "
            f"replace it with a good copy from {data.source}"
        )


def _save(pdf: bytes, paper: Path) -> None:
    """Write `pdf` at `paper`, beside its place first so a half-written PDF never looks whole."""
    partial = paper.with_name(f".{paper.name}.partial")
    try:
        paper.parent.mkdir(parents=True, exist_ok=True)
        partial.write_bytes(pdf)
        partial.rename(paper)
    except OSError:
        partial.unlink(missing_ok=True)
        raise


def fetch(
    project: Path, sources: list[retrieve.Retriever] | None = None
) -> tuple[list[str], bool]:
    """Bring what the resource manifest of the project at `project` lists into its `resources/`.

    A missing document is asked of `sources` in turn, by default those the user's
    configuration allows (see `retrieve`).

    Returns a line per thing done, a line per failure, and the list of what is still
    missing; and success. Something only missing is not a failure.
    """
    resources = project / RESOURCES
    notes: list[str] = []
    failures: list[str] = []
    missing: list[str] = []
    documents = manifest.bibliography(project)
    for key, entry in documents.items():
        if not manifest.is_plain(key):
            failures.append(
                f"{manifest.BIBLIOGRAPHY}: citekey {key!r} cannot name a file"
            )
            continue
        path = f"papers/{key}.pdf"
        if (resources / path).exists():
            continue
        # The user's configuration is read only once something is missing.
        if sources is None:
            sources, problems = retrieve.configured()
            failures += problems
        pdf, errors = retrieve.retrieve(entry, sources)
        notes += [f"{path}: {error}" for error in errors]
        if pdf is None:
            missing.append(path)
            continue
        try:
            _save(pdf, resources / path)
        except OSError as error:
            failures.append(f"{path}: retrieved but not saved: {error}")
            continue
        notes.append(f"{path} retrieved")
    try:
        listed = manifest.load(project)
    except manifest.ManifestError as error:
        failures.append(str(error))
        listed = manifest.Resources([], [])
    for code in listed.code:
        if code.source_of is not None and code.source_of not in documents:
            failures.append(
                f"{manifest.FILENAME}: code resource {code.name} is the source form "
                f"of {code.source_of}, which {manifest.BIBLIOGRAPHY} does not list"
            )
        try:
            done = _clone(code, resources)
        except GitError as error:
            failures.append(f"code/{code.name}: {error}")
            continue
        if done:
            notes.append(done)
    for data in listed.data:
        path = f"data/{data.name}"
        if not (resources / path).exists():
            missing.append(f"{path} (from {data.source})")
            continue
        try:
            _check(data, resources / path)
        except ValueError as error:
            failures.append(f"{path}: {error}")
    lines = notes + [f"FAILED: {failure}" for failure in failures]
    if missing:
        lines += [
            f"{len(missing)} missing: copy into {RESOURCES}/",
            *(f"  {path}" for path in missing),
        ]
    return lines or ["ok"], not failures


def _project(start: Path) -> Path:
    """The project folder holding `start`: the nearest one with a `pyproject.toml`."""
    for folder in [start, *start.parents]:
        if (folder / "pyproject.toml").is_file():
            return folder
    return start


def main(argv: list[str] | None = None) -> int:
    """Run `fetch` on the project holding the current folder; returns the exit code."""
    argparse.ArgumentParser(
        prog="fetch",
        description="Retrieve missing PDFs, clone code resources at their commit, check "
        "data checksums, and list what is missing.",
    ).parse_args(argv)
    lines, ok = fetch(_project(Path.cwd()))
    print("\n".join(lines))
    return 0 if ok else 1
