"""The off-limits module: the hook fed tool calls as Claude Code feeds them, the settings
merge, and `ws sync` writing it all into every repository and the workspace root.
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest
from conftest import Workspace, git, make_remote
from ws import offlimits
from ws.manifest import Blocked, OffLimits
from ws.manifest import Workspace as Manifest

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
    "repo": "demo-confidential",
}


def patterns(tmp_path: Path, off_limits: dict = OFF_LIMITS) -> Path:
    """The patterns file `ws sync` writes for `off_limits`."""
    manifest = Manifest(
        "demo",
        [],
        off_limits=OffLimits(
            tuple(off_limits["paths"]),
            tuple(
                Blocked(entry["pattern"], entry["what"])
                if isinstance(entry, dict)
                else Blocked(entry, "off-limits material")
                for entry in off_limits["patterns"]
            ),
        ),
    )
    file = tmp_path / "off-limits.json"
    file.write_text(offlimits._patterns_text(manifest))
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
    assert "ws sync" in result.stderr


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


@pytest.fixture
def guarded(workspace: Workspace) -> Workspace:
    """The workspace with off-limits material and an off-limits repository, synced."""
    workspace.settings["off_limits"] = OFF_LIMITS
    workspace.roles["demo-confidential"] = "off-limits"
    workspace.urls["demo-confidential"] = make_remote(
        workspace.remotes, "demo-confidential", {"docs/minutes.md": "# Secret\n"}
    )
    workspace.write_manifest()
    result = workspace.sync()
    assert result.returncode == 0, result.stdout + result.stderr
    return workspace


@pytest.mark.parametrize("name", ["demo", "demo-hub", "demo-framework", None])
def test_sync_writes_the_module_into_every_repository_and_the_root(
    guarded: Workspace, name: str | None
) -> None:
    folder = guarded.root / name if name else guarded.root
    settings = json.loads((folder / ".claude/settings.json").read_text())
    assert "Read(**/confidential/**)" in settings["permissions"]["deny"]
    assert "mcp__claude_ai_Gmail" in settings["permissions"]["deny"]
    [entry] = settings["hooks"]["PreToolUse"]
    assert "guard_off_limits.py" in entry["hooks"][0]["command"]
    script = folder / ".claude/hooks/guard_off_limits.py"
    assert script.resolve() == (guarded.hub / "tools/ws/guard_off_limits.py").resolve()
    assert "confidential/" in (folder / ".ignore").read_text().splitlines()
    result = hook(folder / ".claude/hooks/off-limits.json", "Bash", command="ls confidential/")
    assert result.returncode == 2
    if name:
        assert git("status", "--porcelain", "--", ".claude", ".ignore", cwd=folder) == ""


def test_the_off_limits_repository_is_cloned_but_never_linked_or_written(
    guarded: Workspace,
) -> None:
    secret = guarded.root / "demo-confidential"
    assert (secret / "docs/minutes.md").is_file()
    assert sorted(path.name for path in secret.iterdir()) == [".git", "README.md", "docs"]
    assert not (guarded.hub / "docs/studies/demo-confidential").exists()
    assert "demo-confidential" not in (guarded.hub / "docs/studies/index.md").read_text()


def test_second_sync_reports_nothing_new(guarded: Workspace) -> None:
    result = guarded.sync()

    assert result.returncode == 0, result.stdout + result.stderr
    assert "workspace root: ok" in result.stdout
    assert "demo-confidential: no upstream" not in result.stdout


def test_a_settings_file_of_the_repository_is_merged_and_reported(
    workspace: Workspace,
) -> None:
    workspace.settings["off_limits"] = OFF_LIMITS
    own = {"permissions": {"allow": ["Bash(make:*)"]}}
    workspace.urls["demo-framework"] = make_remote(
        workspace.remotes / "own-settings",
        "demo-framework",
        {".claude/settings.json": json.dumps(own), "docs/wiki/index.md": "# Wiki\n"},
    )
    workspace.write_manifest()

    result = workspace.sync()

    line = next(
        line for line in result.stdout.splitlines() if line.startswith("demo-framework:")
    )
    assert ".claude/settings.json changed by ws, commit it" in line
    settings = json.loads(
        (workspace.root / "demo-framework/.claude/settings.json").read_text()
    )
    assert settings["permissions"]["allow"] == ["Bash(make:*)"]
    assert "Read(**/confidential/**)" in settings["permissions"]["deny"]


def test_a_settings_file_that_cannot_be_merged_is_kept_and_reported(
    guarded: Workspace,
) -> None:
    settings = guarded.root / "demo-framework/.claude/settings.json"
    settings.write_text("{ broken")

    result = guarded.sync()

    assert settings.read_text() == "{ broken"
    assert ".claude/settings.json not merged" in result.stdout


def test_ws_check_reports_missing_off_limits_files(guarded: Workspace) -> None:
    (guarded.root / "demo-framework/.ignore").unlink()
    (guarded.root / ".claude/hooks/off-limits.json").unlink()

    result = guarded.run("check", "--all")

    assert result.returncode == 1
    assert "demo-framework: FAILED: .ignore missing or out of date" in result.stdout
    assert (
        "workspace root: FAILED: .claude/hooks/off-limits.json missing or out of date"
        in result.stdout
    )
    assert "demo-confidential: skipped" in result.stdout
