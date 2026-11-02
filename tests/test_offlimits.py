"""The off-limits module: the hook fed tool calls as Claude Code feeds them, the settings
merge.
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest
from rkt import offlimits
from rkt.inquiry import Blocked, OffLimits

HOOK = Path(offlimits.__file__).with_name("guard_off_limits.py")

OFF_LIMITS = {
    "paths": [
        "confidential/",
        "demo-confidential/",
        "~/VISIATIV/",
        "D:/u0150568.LUNA/Documents/PROJECT/WP*/",
        "**/resources/secret/",
    ],
    "patterns": [
        {"pattern": r"\.(xlsx|msg|eml)\b", "what": "an Office or e-mail file"},
        r"partner-inputs\.md",
    ],
    "deny_connectors": ["mcp__claude_ai_Gmail"],
}


def patterns(tmp_path: Path, off_limits: dict = OFF_LIMITS) -> Path:
    """The patterns file rkt writes for `off_limits`."""
    listed = OffLimits(
        tuple(off_limits["paths"]),
        tuple(
            Blocked(entry["pattern"], entry["what"])
            if isinstance(entry, dict)
            else Blocked(entry, "off-limits material")
            for entry in off_limits["patterns"]
        ),
    )
    file = tmp_path / "off-limits.json"
    file.write_text(offlimits._patterns_text(listed))
    return file


def hook(config: Path, tool: str, **tool_input: str) -> subprocess.CompletedProcess[str]:
    """Run the hook as Claude Code does: the tool call as JSON on stdin."""
    call = {"hook_event_name": "PreToolUse", "tool_name": tool, "tool_input": tool_input}
    return subprocess.run(
        [sys.executable, "-I", str(HOOK), str(config)],
        input=json.dumps(call),
        check=False,
        capture_output=True,
        text=True,
    )


@pytest.mark.parametrize(
    ("tool", "arguments"),
    [
        ("Read", {"file_path": "/home/me/ws/demo-study/confidential/notes.md"}),
        ("Bash", {"command": "ls confidential"}),
        ("Bash", {"command": "git log -p -- confidential/x.md | head"}),
        ("Grep", {"pattern": "burst", "path": "../demo-confidential"}),
        ("Glob", {"pattern": "**/*.md", "path": "/home/me/VISIATIV"}),
        ("Bash", {"command": "cat $HOME/visiativ/minutes.txt"}),
        ("PowerShell", {"command": r"Get-ChildItem D:\u0150568.LUNA\Documents\PROJECT\WP5\ "}),
        ("Bash", {"command": "ls /mnt/d/u0150568.LUNA/Documents/PROJECT/WP4/tracker"}),
        ("Read", {"file_path": "/data/pool/resources/secret/d5.pdf"}),
        ("Bash", {"command": "python -c 'open(\"minutes.MSG\")'"}),
        ("Read", {"file_path": "docs/partner-inputs.md"}),
    ],
)
def test_hook_blocks_a_call_naming_off_limits_material(
    tmp_path: Path, tool: str, arguments: dict
) -> None:
    result = hook(patterns(tmp_path), tool, **arguments)

    assert result.returncode == 2, arguments
    assert result.stderr.startswith("Blocked: this call would touch ")


@pytest.mark.parametrize(
    ("tool", "arguments"),
    [
        ("Read", {"file_path": "docs/agents/confidentiality.md"}),
        ("Bash", {"command": "uv run python -m pytest"}),
        ("Grep", {"pattern": "burst pressure", "path": "docs"}),
        ("Read", {"file_path": "resources/papers/smith2020.pdf"}),
        ("Bash", {"command": "ls resources/secretive"}),
    ],
)
def test_hook_lets_other_calls_through(tmp_path: Path, tool: str, arguments: dict) -> None:
    result = hook(patterns(tmp_path), tool, **arguments)

    assert result.returncode == 0, result.stderr


def test_hook_without_its_patterns_blocks_everything(tmp_path: Path) -> None:
    result = hook(tmp_path / "missing.json", "Bash", command="ls")

    assert result.returncode == 2
    assert "rkt guard" in result.stderr


def test_deny_rules_cover_each_spelling_of_a_path() -> None:
    rules = offlimits.deny_rules(
        OffLimits(
            ("confidential/", "~/VISIATIV/", "D:/x/WP*/", "/srv/secret/", "**/a/b/"),
            deny_connectors=("mcp__claude_ai_Gmail",),
        )
    )

    assert rules == [
        "Read(**/confidential/**)",
        "Read(~/VISIATIV/**)",
        "Read(//d/x/WP*/**)",
        "Read(//mnt/d/x/WP*/**)",
        "Read(//srv/secret/**)",
        "Read(**/a/b/**)",
        "mcp__claude_ai_Gmail",
    ]


def test_settings_merge_keeps_other_keys_and_replaces_stale_rules() -> None:
    existing = {
        "permissions": {"allow": ["Bash(ls:*)"], "deny": ["Read(./.env)", "Read(**/old/**)"]},
        "hooks": {
            "PreToolUse": [
                {"matcher": "Bash", "hooks": [{"type": "command", "command": "lint.sh"}]}
            ]
        },
        "model": "opus",
    }

    merged = json.loads(
        offlimits.merged_settings(
            json.dumps(existing), ["Read(**/new/**)"], ["Read(**/old/**)"]
        )
    )

    assert merged["model"] == "opus"
    assert merged["permissions"]["allow"] == ["Bash(ls:*)"]
    assert merged["permissions"]["deny"] == ["Read(./.env)", "Read(**/new/**)"]
    [own, ours] = merged["hooks"]["PreToolUse"]
    assert own["hooks"][0]["command"] == "lint.sh"
    assert ours["matcher"] == "Read|Grep|Glob|Bash|PowerShell"
    # Merging again changes nothing.
    again = offlimits.merged_settings(json.dumps(merged), ["Read(**/new/**)"], [])
    assert json.loads(again) == merged


@pytest.mark.parametrize("text", ["not json", "[1, 2]", '{"permissions": []}'])
def test_settings_that_cannot_be_merged_are_refused(text: str) -> None:
    with pytest.raises((ValueError, TypeError)):
        offlimits.merged_settings(text, [], [])
