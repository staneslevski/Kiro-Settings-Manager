"""Tests for ksm.converters.hook_converter module."""

from __future__ import annotations

import json
from pathlib import Path

from ksm.converters.hook_converter import (
    EVENT_TYPE_MAP,
    UNCONVERTIBLE_EVENTS,
    convert_hook,
)


def _write_hook(
    tmp_path: Path,
    filename: str = "test.kiro.hook",
    *,
    enabled: bool = True,
    when_type: str = "promptSubmit",
    then_type: str = "runCommand",
    command: str = "echo hello",
    tool_types: list[str] | None = None,
    raw: str | None = None,
) -> Path:
    """Helper to write a hook file."""
    hooks = tmp_path / "hooks"
    hooks.mkdir(exist_ok=True)
    p = hooks / filename
    if raw is not None:
        p.write_text(raw, encoding="utf-8")
        return p
    when: dict[str, object] = {"type": when_type}
    if tool_types is not None:
        when["toolTypes"] = tool_types
    data = {
        "version": "1.0.0",
        "enabled": enabled,
        "name": "test hook",
        "when": when,
        "then": {"type": then_type, "command": command},
    }
    p.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return p


# ==================================================================
# runCommand conversion
# ==================================================================


class TestRunCommandConversion:
    """Hooks with then.type=runCommand."""

    def test_prompt_submit_maps_to_user_prompt_submit(self, tmp_path: Path) -> None:
        p = _write_hook(tmp_path, when_type="promptSubmit")
        r = convert_hook(p)
        assert r.status == "converted"
        assert r.cli_event_type == "userPromptSubmit"
        assert len(r.cli_hook_entries) == 1
        assert r.cli_hook_entries[0]["command"] == "echo hello"

    def test_agent_stop_maps_to_stop(self, tmp_path: Path) -> None:
        p = _write_hook(tmp_path, when_type="agentStop")
        r = convert_hook(p)
        assert r.status == "converted"
        assert r.cli_event_type == "stop"

    def test_pre_tool_use_maps_correctly(self, tmp_path: Path) -> None:
        p = _write_hook(
            tmp_path,
            when_type="preToolUse",
            tool_types=["read"],
        )
        r = convert_hook(p)
        assert r.status == "converted"
        assert r.cli_event_type == "preToolUse"
        # read expands to fs_read, grep, glob, code
        matchers = [e["matcher"] for e in r.cli_hook_entries]
        assert "fs_read" in matchers
        assert "grep" in matchers
        assert "glob" in matchers
        assert "code" in matchers

    def test_post_tool_use_maps_correctly(self, tmp_path: Path) -> None:
        p = _write_hook(
            tmp_path,
            when_type="postToolUse",
            tool_types=["shell"],
        )
        r = convert_hook(p)
        assert r.status == "converted"
        assert r.cli_event_type == "postToolUse"
        assert r.cli_hook_entries[0]["matcher"] == "execute_bash"

    def test_pre_tool_use_no_tool_types(self, tmp_path: Path) -> None:
        p = _write_hook(tmp_path, when_type="preToolUse")
        r = convert_hook(p)
        assert r.status == "converted"
        assert "matcher" not in r.cli_hook_entries[0]

    def test_command_value_preserved(self, tmp_path: Path) -> None:
        p = _write_hook(tmp_path, command="npm run lint")
        r = convert_hook(p)
        assert r.cli_hook_entries[0]["command"] == "npm run lint"


# ==================================================================
# askAgent skip
# ==================================================================


class TestAskAgentSkip:
    """Hooks with then.type=askAgent are skipped with warning."""

    def test_ask_agent_skipped_with_warning(self, tmp_path: Path) -> None:
        p = _write_hook(tmp_path, then_type="askAgent")
        r = convert_hook(p)
        assert r.status == "skipped"
        assert len(r.warnings) == 1
        assert "askAgent" in r.warnings[0]


# ==================================================================
# Unconvertible event types
# ==================================================================


class TestUnconvertibleEvents:
    """IDE event types with no CLI equivalent."""

    def test_file_edited_skipped(self, tmp_path: Path) -> None:
        p = _write_hook(tmp_path, when_type="fileEdited")
        r = convert_hook(p)
        assert r.status == "skipped"
        assert len(r.warnings) == 1
        assert "fileEdited" in r.warnings[0]

    def test_file_created_skipped(self, tmp_path: Path) -> None:
        p = _write_hook(tmp_path, when_type="fileCreated")
        r = convert_hook(p)
        assert r.status == "skipped"
        assert "fileCreated" in r.warnings[0]

    def test_file_deleted_skipped(self, tmp_path: Path) -> None:
        p = _write_hook(tmp_path, when_type="fileDeleted")
        r = convert_hook(p)
        assert r.status == "skipped"

    def test_pre_task_execution_skipped(self, tmp_path: Path) -> None:
        p = _write_hook(tmp_path, when_type="preTaskExecution")
        r = convert_hook(p)
        assert r.status == "skipped"

    def test_post_task_execution_skipped(self, tmp_path: Path) -> None:
        p = _write_hook(tmp_path, when_type="postTaskExecution")
        r = convert_hook(p)
        assert r.status == "skipped"

    def test_all_unconvertible_events_covered(self) -> None:
        """Property 6: every UNCONVERTIBLE_EVENTS entry skips."""
        for event in UNCONVERTIBLE_EVENTS:
            # Can't use tmp_path in a loop; use manual tmpdir
            import tempfile

            with tempfile.TemporaryDirectory() as td:
                p = _write_hook(Path(td), when_type=event)
                r = convert_hook(p)
                assert r.status == "skipped", f"{event} should be skipped"

    def test_all_convertible_events_covered(self) -> None:
        """Property 6: every EVENT_TYPE_MAP entry converts."""
        import tempfile

        for ide_event, cli_event in EVENT_TYPE_MAP.items():
            with tempfile.TemporaryDirectory() as td:
                kw: dict[str, object] = {"when_type": ide_event}
                if ide_event in (
                    "preToolUse",
                    "postToolUse",
                ):
                    kw["tool_types"] = ["shell"]
                p = _write_hook(Path(td), **kw)  # type: ignore[arg-type]
                r = convert_hook(p)
                assert r.status == "converted", f"{ide_event} should convert"
                assert r.cli_event_type == cli_event


# ==================================================================
# Disabled hooks (Property 7)
# ==================================================================


class TestDisabledHooks:
    """Disabled hooks are skipped silently."""

    def test_disabled_hook_skipped_no_warnings(self, tmp_path: Path) -> None:
        p = _write_hook(tmp_path, enabled=False)
        r = convert_hook(p)
        assert r.status == "skipped"
        assert r.warnings == []
        assert r.error is None


# ==================================================================
# Invalid JSON
# ==================================================================


class TestInvalidJson:
    """Hook files with invalid JSON."""

    def test_invalid_json_fails(self, tmp_path: Path) -> None:
        p = _write_hook(tmp_path, raw="not json at all {{")
        r = convert_hook(p)
        assert r.status == "failed"
        assert r.error is not None
        assert "invalid JSON" in r.error

    def test_nonexistent_file_fails(self, tmp_path: Path) -> None:
        p = tmp_path / "ghost.kiro.hook"
        r = convert_hook(p)
        assert r.status == "failed"
        assert r.error is not None


# ==================================================================
# Edge-case coverage
# ==================================================================


class TestHookEdgeCases:
    """Cover remaining branches in hook_converter."""

    def test_unknown_event_type_fails(self, tmp_path: Path) -> None:
        """Event type not in any map produces failed."""
        p = _write_hook(tmp_path, when_type="totallyUnknown")
        r = convert_hook(p)
        assert r.status == "failed"
        assert r.error is not None
        assert "unknown event type" in r.error

    def test_unsupported_then_type_fails(self, tmp_path: Path) -> None:
        """then.type that is neither runCommand nor askAgent."""
        hooks = tmp_path / "hooks"
        hooks.mkdir(exist_ok=True)
        p = hooks / "weird.kiro.hook"
        data = {
            "version": "1.0.0",
            "enabled": True,
            "name": "weird",
            "when": {"type": "promptSubmit"},
            "then": {"type": "somethingElse"},
        }
        p.write_text(json.dumps(data), encoding="utf-8")
        r = convert_hook(p)
        assert r.status == "failed"
        assert "unsupported then.type" in (r.error or "")
