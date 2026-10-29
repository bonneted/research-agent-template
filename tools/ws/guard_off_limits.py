"""PreToolUse hook: refuse a tool call whose arguments name off-limits material.

Claude Code sends the tool call as JSON on stdin; exit code 2 blocks it and shows stderr
to the model. The patterns are read from the file given as the first argument, which
`ws sync` writes from the `off_limits` block of the hub's `workspace.yaml`. Run with
`python -I`, so the standard library only. Without its patterns it blocks every call it
sees: a guard that cannot read its list fails closed.
"""

import json
import re
import sys
from pathlib import Path


def normalised(call: dict) -> str:
    """The tool call's arguments as one lowercase text, with `/` for every `\\`."""
    text = json.dumps(call.get("tool_input", {}), ensure_ascii=False)
    return text.replace("\\\\", "/").replace("\\", "/").lower()


def main(argv: list[str]) -> int:
    try:
        config = json.loads(Path(argv[1]).read_text(encoding="utf-8"))
        blocked = [
            (re.compile(entry["pattern"], re.IGNORECASE), entry["what"])
            for entry in config["blocked"]
        ]
    except (IndexError, OSError, ValueError, KeyError, TypeError, re.error) as error:
        print(
            f"Blocked: the off-limits patterns could not be read ({error}). "
            "Ask the user to run `uv run ws sync` in the hub.",
            file=sys.stderr,
        )
        return 2
    try:
        call = json.load(sys.stdin)
    except ValueError:
        print("Blocked: the tool call could not be read.", file=sys.stderr)
        return 2
    text = normalised(call if isinstance(call, dict) else {})
    for pattern, what in blocked:
        if pattern.search(text):
            print(
                f"Blocked: this call would touch {what}, which is off-limits in this "
                "workspace (see the off-limits rules in AGENTS.md). Do not try another "
                "way in; ask the user for the value you need instead.",
                file=sys.stderr,
            )
            return 2
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
