"""`ws fetch`: fill the pool from every repository's resource manifest."""

import hashlib
import os
import shlex
import shutil
import socket
from pathlib import Path

from ws import pool, refs, resources, retrieve, zotero
from ws.git import GitError, git
from ws.manifest import Repository

# Set it to the name by which the machine that has a missing resource reaches this one
# over ssh, when that is not this machine's host name.
HOST_VARIABLE = "SPIMAT_SSH_HOST"


def _commit(clone: Path, commit: str) -> str | None:
    """The full hash of `commit` in `clone`, or None if the clone does not have it."""
    try:
        return git(
            "rev-parse", "--verify", "--quiet", f"{commit}^{{commit}}", cwd=clone
        ).strip()
    except GitError:
        return None


def _newest(clone: Path, commits: list[str]) -> str:
    """The newest of `commits`: the descendant of the others, or else the latest one."""

    def is_ancestor(older: str, newer: str) -> bool:
        try:
            git("merge-base", "--is-ancestor", older, newer, cwd=clone)
        except GitError:
            return False
        return True

    def date(commit: str) -> int:
        return int(git("show", "-s", "--format=%ct", commit, cwd=clone))

    newest = commits[0]
    for commit in commits[1:]:
        if is_ancestor(newest, commit) or (
            not is_ancestor(commit, newest) and date(commit) > date(newest)
        ):
            newest = commit
    return newest


def _settle(
    name: str,
    pins: dict[str, resources.Code],
    pool_path: Path,
    notes: dict[str, list[str]],
    failures: dict[str, list[str]],
) -> None:
    """Bring the pool's clone of a code resource to the newest commit its repositories pin.

    `pins` maps each repository listing it to its entry. Each outcome is reported on
    the repositories it concerns, in `notes` and `failures`.
    """
    path = pool.code(name)
    urls = sorted({code.url for code in pins.values()})
    if len(urls) > 1:
        for repository in pins:
            failures[repository].append(
                f"{path}: listed with different URLs: {', '.join(urls)}"
            )
        return
    clone = pool_path / path
    # A new clone is made beside its place and moved in once at its commit, so an
    # interrupted or failed clone never looks like a finished one.
    partial = clone.with_name(f".{name}.partial")
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
                urls[0],
                str(partial),
                cwd=partial.parent,
            )
        elif not (clone / ".git").exists():
            raise GitError(f"{clone} exists but is not a git repository")
        resolved = {
            repository: _commit(work, code.commit) for repository, code in pins.items()
        }
        if not fresh and None in resolved.values():
            git("fetch", "--quiet", cwd=work)
            resolved = {
                repository: _commit(work, code.commit)
                for repository, code in pins.items()
            }
        for repository, commit in resolved.items():
            if commit is None:
                failures[repository].append(
                    f"{path}: commit {pins[repository].commit} is not in {urls[0]}"
                )
        found = [commit for commit in resolved.values() if commit is not None]
        if not found:
            shutil.rmtree(partial, ignore_errors=True)
            return
        newest = _newest(work, found)
        followers = [
            repository for repository, commit in resolved.items() if commit == newest
        ]
        head = None if fresh else git("rev-parse", "HEAD", cwd=work).strip()
        if head != newest:
            if head is not None and git("status", "--porcelain", cwd=work).strip():
                for repository in followers:
                    failures[repository].append(
                        f"{path}: uncommitted changes in the pool's clone, left at {head[:12]}"
                    )
                return
            git(
                "-c",
                "advice.detachedHead=false",
                "checkout",
                "--quiet",
                newest,
                cwd=work,
            )
            if fresh:
                partial.rename(clone)
            notes[followers[0]].append(
                f"{path} cloned" if fresh else f"{path} moved to {newest[:12]}"
            )
    except GitError as error:
        shutil.rmtree(partial, ignore_errors=True)
        for repository in pins:
            failures[repository].append(f"{path}: {error}")
        return
    for repository, commit in resolved.items():
        if commit is not None and commit != newest:
            notes[repository].append(
                f"{path} is at newer {newest[:12]}, this repository pins {pins[repository].commit}"
            )


def _check(data: resources.Data, pool_path: Path) -> None:
    """Raise `ValueError` if the pool's copy of a data resource is not the one listed."""
    file = pool_path / pool.data(data.name)
    if not file.is_file():
        raise ValueError(f"{file} is not a file")
    with file.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    if digest != data.sha256:
        raise ValueError(
            f"checksum {digest}, the manifest expects {data.sha256}: "
            f"replace it with a good copy from {data.source}"
        )


def _attach(
    library: zotero.Library,
    citekey: str,
    pdf: bytes,
    warnings: list[str],
    failures: list[str],
) -> bool:
    """Attach a retrieved PDF to the Zotero item with the citekey; returns success."""
    path = pool.paper(citekey)
    try:
        library.attach_pdf(citekey, pdf)
    except zotero.QuotaFull:
        warnings.append(f"{path} not attached in Zotero: its file storage is full")
        return False
    except zotero.ZoteroError as error:
        failures.append(f"{path} not attached in Zotero: {error}")
        return False
    return True


def _retrieve(
    entry: retrieve.Entry,
    sources: list[retrieve.Retriever],
    paper: Path,
    library: zotero.Library | None,
    notes: list[str],
    warnings: list[str],
    failures: list[str],
) -> bool:
    """Save the PDF of `entry` at `paper` from the first source that has it, and attach
    it in Zotero if `library` asks for uploads; returns success.
    """
    path = pool.paper(entry.citekey)
    pdf, source, errors = retrieve.retrieve(entry, sources)
    notes += [f"{path}: {error}" for error in errors]
    if pdf is None:
        return False
    # Written beside its place and moved in, so a half-written PDF never looks whole.
    partial = paper.with_name(f".{paper.name}.partial")
    try:
        paper.parent.mkdir(parents=True, exist_ok=True)
        partial.write_bytes(pdf)
        partial.rename(paper)
    except OSError as error:
        partial.unlink(missing_ok=True)
        failures.append(f"{path}: retrieved but not saved: {error}")
        return False
    if (
        library is not None
        and library.upload_pdfs
        and source != retrieve.Zotero.name
        and _attach(library, entry.citekey, pdf, warnings, failures)
    ):
        notes.append(f"{path} retrieved, attached in Zotero")
    else:
        notes.append(f"{path} retrieved")
    return True


def _copy_command(pool_path: Path, missing: list[str]) -> list[str]:
    """A command that copies the missing resources into this pool from the pool of the
    machine it runs on, where they sit at the same place.
    """
    # That machine's pool is its own SPIMAT_RESOURCES, or else where this one is.
    home = Path.home()
    theirs = (
        f"$HOME/{pool_path.relative_to(home)}"
        if pool_path.is_relative_to(home)
        else str(pool_path)
    )
    host = os.environ.get(HOST_VARIABLE) or socket.gethostname()
    source = f'"${{{pool.VARIABLE}:-{theirs}}}/"'
    destination = f"{host}:{shlex.quote(f'{pool_path}/')}"
    return [
        "",
        f"{len(missing)} missing from the pool. On a machine whose pool has them, run:",
        "",
        f"rsync -av --files-from=- {source} {destination} <<'EOF'",
        *missing,
        "EOF",
    ]


def _pull(
    root: Path, repositories: list[Repository], library: zotero.Library | None
) -> tuple[list[str], bool, zotero.Library | None]:
    """Pull every cloned repository's bibliography from Zotero, or skip it with one line.

    Returns the report lines, success, and the library: the user's configured one if
    `library` is None, and None if it cannot be had.
    """
    if library is None:
        library, reason = zotero.configured()
        if library is None:
            return [f"zotero: skipped ({reason})"], True, None
    lines, ok = [], True
    for repository in repositories:
        if not (root / repository.name / ".git").exists():
            continue
        try:
            pulled, pulled_ok = refs.pull(
                root, repositories, repository.name, library, required=False
            )
        except zotero.Unreachable as error:
            # The committed bibliographies stay the source until Zotero answers.
            return lines + [f"zotero: skipped ({error})"], ok, None
        except zotero.ZoteroError as error:
            pulled, pulled_ok = [f"{repository.name}: FAILED: {error}"], False
        lines += pulled
        ok = ok and pulled_ok
    return lines, ok, library


def fetch(
    root: Path,
    repositories: list[Repository],
    sources: list[retrieve.Retriever] | None = None,
    library: zotero.Library | None = None,
) -> tuple[list[str], bool]:
    """Bring what each repository's resource manifest lists into the pool of the workspace at `root`.

    Each repository's bibliography is first pulled from its Zotero collection in
    `library`, by default the user's configured one (see `refs`); without one, or with
    Zotero unreachable, the committed bibliographies are read as they are. A missing
    document is then asked of `sources` in turn, by default those the user's
    configuration allows (see `retrieve`).

    Returns the pull's report, a report line per repository, a line per failure and the
    copy command for what is missing; and success.
    """
    pulled, pulled_ok, library = _pull(root, repositories, library)
    pool_path = pool.location(root)
    names = [repository.name for repository in repositories]
    notes: dict[str, list[str]] = {name: [] for name in names}
    warnings: dict[str, list[str]] = {name: [] for name in names}
    failures: dict[str, list[str]] = {name: [] for name in names}
    # Each missing path once, however many repositories list it.
    missing: dict[str, None] = {}
    # Every repository's entry for each code resource, which has one clone in the pool.
    pins: dict[str, dict[str, resources.Code]] = {}
    # Each document is asked for once, however many repositories list it.
    retrieved: dict[str, bool] = {}
    for name in names:
        path = root / name
        if not (path / ".git").exists():
            failures[name].append("not cloned: run ws sync first")
            continue
        wanted = []
        bibliography = path / resources.BIBLIOGRAPHY
        entries = (
            retrieve.entries(bibliography.read_text(encoding="utf-8"))
            if bibliography.is_file()
            else {}
        )
        for key, entry in entries.items():
            if not pool.is_plain(key):
                failures[name].append(
                    f"{resources.BIBLIOGRAPHY}: citekey {key!r} cannot name a file"
                )
                continue
            paper = pool_path / pool.paper(key)
            if paper.exists():
                continue
            if key not in retrieved:
                # The user's configuration is read only once something is missing.
                if sources is None:
                    sources, problems = retrieve.configured()
                    failures[name] += problems
                retrieved[key] = _retrieve(
                    entry,
                    sources,
                    paper,
                    library,
                    notes[name],
                    warnings[name],
                    failures[name],
                )
            if not retrieved[key]:
                wanted.append(pool.paper(key))
        try:
            listed = resources.load(path)
        except resources.ResourceError as error:
            failures[name].append(str(error))
            listed = resources.Resources([], [])
        for code in listed.code:
            pins.setdefault(code.name, {}).setdefault(name, code)
            if code.source_of is not None and code.source_of not in entries:
                failures[name].append(
                    f"{resources.FILENAME}: code resource {code.name} is the source form "
                    f"of {code.source_of}, which {resources.BIBLIOGRAPHY} does not list"
                )
            failures[name] += [
                f"{resources.FILENAME}: code resource {code.name} is the code of "
                f"{citekey}, which {resources.BIBLIOGRAPHY} does not list"
                for citekey in code.code_of
                if citekey not in entries
            ]
        for data in listed.data:
            if not (pool_path / pool.data(data.name)).exists():
                wanted.append(pool.data(data.name))
                continue
            try:
                _check(data, pool_path)
            except ValueError as error:
                failures[name].append(f"{pool.data(data.name)}: {error}")
        if wanted:
            notes[name].append(f"{len(wanted)} missing")
            missing.update(dict.fromkeys(wanted))
    for code_name, code_pins in pins.items():
        _settle(code_name, code_pins, pool_path, notes, failures)
    lines = pulled
    for name in names:
        if notes[name] or not failures[name]:
            lines.append(f"{name}: {', '.join(notes[name]) or 'ok'}")
        lines += [f"{name}: WARNING: {warning}" for warning in warnings[name]]
        lines += [f"{name}: FAILED: {failure}" for failure in failures[name]]
    if missing:
        lines += _copy_command(pool_path, list(missing))
    return lines, pulled_ok and not any(failures.values())
