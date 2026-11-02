"""The off-limits module: what keeps an agent away from material it must never read.

Configured by an inquiry's `.off-limits.yaml`, out of git and inherited by copy down the
tree: path globs, regular expressions on tool-call arguments, and connectors to deny.
It writes into the inquiry, where sessions start:

- `.claude/settings.local.json`: deny rules for `Read` on the paths and for the
  connectors, and a PreToolUse hook; merged into an existing file, whose other keys
  are kept; out of git, so no off-limits name is ever committed;
- `.claude/hooks/guard_off_limits.py`: the hook, and `.claude/hooks/off-limits.json`,
  the patterns it blocks;
- `.ignore`: the relative paths, which Claude Code's Grep and Glob skip.

In a git repository, a file it writes is kept out of git by `.git/info/exclude`."""

import json
import re
from pathlib import Path

from rkt import links
from rkt.inquiry import OffLimits

SETTINGS = ".claude/settings.local.json"
HOOKS = ".claude/hooks"
SCRIPT = f"{HOOKS}/guard_off_limits.py"
PATTERNS = f"{HOOKS}/off-limits.json"
IGNORE = ".ignore"
# Every file the module writes, for `.git/info/exclude`.
FILES = (SETTINGS, SCRIPT, PATTERNS, f"{HOOKS}/{links.COPIES}", IGNORE)
# The tools whose arguments the hook reads.
MATCHER = "Read|Grep|Glob|Bash|PowerShell"
COMMAND = (
    'uv run --no-project -q python -I "$CLAUDE_PROJECT_DIR/.claude/hooks/guard_off_limits.py" '
    '"$CLAUDE_PROJECT_DIR/.claude/hooks/off-limits.json"'
)
_WRITTEN = "Written by rkt from the inquiry's .off-limits.yaml: do not edit."
_BEGIN = f"# {_WRITTEN}"
_END = "# End of the off-limits paths."
# A name character: a path is matched where it is not part of a longer name.
_NAME = r"[\w.-]"
_DRIVE = re.compile(r"^([A-Za-z]):/")


def _tail(glob: str) -> str:
    """The glob without what anchors it (a drive, `~/`, `/`, leading `**/`), so that it
    matches however a call spells the path: `D:\\x`, `/mnt/d/x`, `~/x` or `$HOME/x`.
    """
    tail = _DRIVE.sub("", glob.replace("\\", "/"))
    tail = tail.removeprefix("~/").lstrip("/")
    while tail.startswith("**/"):
        tail = tail[3:]
    return tail.rstrip("/")


def path_pattern(glob: str) -> str:
    """The regular expression a tool call naming the path `glob` matches."""
    escaped = re.escape(_tail(glob).lower())
    body = escaped.replace(r"\*\*", ".*").replace(r"\*", "[^/]*")
    return rf"(?<!{_NAME}){body}(?!{_NAME})"


def blocked(off_limits: OffLimits) -> list[dict[str, str]]:
    """What the hook blocks: each path, then each pattern, with what it guards."""
    return [
        {"pattern": path_pattern(glob), "what": f"the off-limits path {glob}"}
        for glob in off_limits.paths
    ] + [
        {"pattern": entry.pattern, "what": entry.what}
        for entry in off_limits.patterns
    ]


def _is_relative(glob: str) -> bool:
    glob = glob.replace("\\", "/")
    return not (glob.startswith(("~", "/")) or _DRIVE.match(glob))


def deny_rules(off_limits: OffLimits) -> list[str]:
    """The `permissions.deny` rules of `.claude/settings.json`."""
    rules = []
    for glob in off_limits.paths:
        glob = glob.replace("\\", "/")
        folder = glob.endswith("/")
        body = glob.rstrip("/")
        if drive := _DRIVE.match(body):
            # Claude Code writes D:\x as //d/x; under WSL the drive is /mnt/d.
            rest = body[drive.end() :]
            letter = drive[1].lower()
            paths = [f"//{letter}/{rest}", f"//mnt/{letter}/{rest}"]
        elif body.startswith("~/"):
            paths = [body]
        elif body.startswith("/"):
            paths = [f"/{body}"]
        else:
            paths = [body if body.startswith("**/") else f"**/{body}"]
        rules += [f"Read({path}{'/**' if folder else ''})" for path in paths]
    return rules + list(off_limits.deny_connectors)


def ignore_lines(off_limits: OffLimits) -> list[str]:
    """The paths of `.ignore`: the relative ones."""
    return [glob for glob in off_limits.paths if _is_relative(glob)]


def _hook_entry() -> dict:
    return {
        "matcher": MATCHER,
        "hooks": [
            {
                "type": "command",
                "command": COMMAND,
                "timeout": 30,
                "statusMessage": "Checking for off-limits paths",
            }
        ],
    }


def _is_ours(entry: object) -> bool:
    return isinstance(entry, dict) and any(
        isinstance(hook, dict) and "guard_off_limits.py" in str(hook.get("command"))
        for hook in entry.get("hooks") or []
    )


def merged_settings(text: str | None, deny: list[str], previous: list[str]) -> str:
    """The settings file `text` with the module's deny rules and hook, other keys kept.

    `previous` are the deny rules `ws` wrote last time: those no longer configured go.
    Raises `ValueError` or `TypeError` if the file cannot be merged safely.
    """
    settings = json.loads(text) if text and text.strip() else {}
    if not isinstance(settings, dict):
        raise TypeError("it is not a JSON object")
    permissions = settings.setdefault("permissions", {})
    if not isinstance(permissions, dict):
        raise TypeError("its permissions are not an object")
    rules = permissions.setdefault("deny", [])
    if not isinstance(rules, list):
        raise TypeError("its permissions.deny is not a list")
    stale = set(previous) - set(deny)
    rules[:] = [rule for rule in rules if rule not in stale]
    rules += [rule for rule in deny if rule not in rules]
    hooks = settings.setdefault("hooks", {})
    if not isinstance(hooks, dict):
        raise TypeError("its hooks are not an object")
    entries = hooks.setdefault("PreToolUse", [])
    if not isinstance(entries, list):
        raise TypeError("its hooks.PreToolUse is not a list")
    ours = [index for index, entry in enumerate(entries) if _is_ours(entry)]
    entry = _hook_entry()
    if ours:
        entries[ours[0]] = entry
        for index in reversed(ours[1:]):
            del entries[index]
    else:
        entries.append(entry)
    return json.dumps(settings, indent=2, ensure_ascii=False) + "\n"


def _with_block(text: str | None, lines: list[str]) -> str:
    """`.ignore` with the module's block of paths, written in place of any earlier one."""
    block = "\n".join([_BEGIN, *lines, _END]) + "\n"
    if not text:
        return block
    if _BEGIN in text and _END in text:
        start = text.index(_BEGIN)
        end = text.index(_END, start) + len(_END)
        return text[:start] + block.rstrip("\n") + text[end:]
    return text + ("" if text.endswith("\n") else "\n") + block


def _read(path: Path) -> str | None:
    return path.read_text(encoding="utf-8") if path.is_file() else None


def _patterns_text(off_limits: OffLimits) -> str:
    return (
        json.dumps(
            {
                "_": _WRITTEN,
                "blocked": blocked(off_limits),
                "deny": deny_rules(off_limits),
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n"
    )


def _previous_deny(base: Path) -> list[str]:
    try:
        deny = json.loads(_read(base / PATTERNS) or "{}").get("deny", [])
    except (ValueError, AttributeError):
        return []
    return [rule for rule in deny if isinstance(rule, str)] if isinstance(deny, list) else []


def write(base: Path, off_limits: OffLimits, hook: Path) -> list[str]:
    """Write the module's files into the folder `base`, the hook linked to `hook`.

    Returns what needs attention: a settings file that cannot be merged, or a hook copy
    edited by hand, is kept.
    """
    if not off_limits:
        return []
    notes = []
    deny = deny_rules(off_limits)
    settings = base / SETTINGS
    current = _read(settings)
    try:
        text = merged_settings(current, deny, _previous_deny(base))
    except (ValueError, TypeError) as error:
        notes.append(
            f"{SETTINGS} not merged ({error}): add the off-limits deny rules and hook by hand"
        )
    else:
        if text != current:
            settings.parent.mkdir(parents=True, exist_ok=True)
            settings.write_text(text, encoding="utf-8")
    patterns = base / PATTERNS
    text = _patterns_text(off_limits)
    if _read(patterns) != text:
        patterns.parent.mkdir(parents=True, exist_ok=True)
        patterns.write_text(text, encoding="utf-8")
    notes += links.file(base / SCRIPT, hook)
    lines = ignore_lines(off_limits)
    ignore = base / IGNORE
    current = _read(ignore)
    if lines and (text := _with_block(current, lines)) != current:
        ignore.write_text(text, encoding="utf-8")
    return notes


def drift(base: Path, off_limits: OffLimits, hook: Path) -> list[str]:
    """What is missing or out of date among the module's files in `base`."""
    if not off_limits:
        return []
    problems = []
    current = _read(base / SETTINGS)
    try:
        expected = merged_settings(current, deny_rules(off_limits), [])
    except (ValueError, TypeError) as error:
        problems.append(f"{SETTINGS} cannot be merged: {error}")
    else:
        if current is None:
            problems.append(f"{SETTINGS} missing")
        elif json.loads(expected) != json.loads(current):
            problems.append(f"{SETTINGS} lacks off-limits deny rules or the hook")
    if _read(base / PATTERNS) != _patterns_text(off_limits):
        problems.append(f"{PATTERNS} missing or out of date")
    if problem := links.file_drift(base / SCRIPT, hook):
        problems.append(f"{HOOKS}/{problem}")
    lines = ignore_lines(off_limits)
    current = _read(base / IGNORE)
    if lines and _with_block(current, lines) != current:
        problems.append(f"{IGNORE} missing or out of date")
    return problems
