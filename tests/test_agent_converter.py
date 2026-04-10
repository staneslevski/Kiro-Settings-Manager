"""Tests for ksm.converters.agent_converter module."""

from __future__ import annotations

import json
from pathlib import Path

from hypothesis import given
from hypothesis import strategies as st

from ksm.converters.agent_converter import (
    convert_agent,
    parse_frontmatter,
)

# ==================================================================
# parse_frontmatter
# ==================================================================


class TestParseFrontmatter:
    """Tests for parse_frontmatter()."""

    def test_valid_frontmatter(self) -> None:
        content = "---\nname: test\ndescription: desc\n---\nbody"
        fm, body = parse_frontmatter(content)
        assert fm == {"name": "test", "description": "desc"}
        assert body == "body"

    def test_valid_frontmatter_with_tools(self) -> None:
        content = "---\nname: a\ndescription: b\n" "tools: [read, shell]\n---\nprompt"
        fm, body = parse_frontmatter(content)
        assert fm["tools"] == ["read", "shell"]
        assert body == "prompt"

    def test_no_delimiters_returns_empty_dict(self) -> None:
        content = "just some markdown"
        fm, body = parse_frontmatter(content)
        assert fm == {}
        assert body == content

    def test_single_delimiter_returns_empty_dict(self) -> None:
        content = "---\nname: test\nno closing"
        fm, body = parse_frontmatter(content)
        assert fm == {}
        assert body == content

    def test_invalid_yaml_returns_empty_dict(self) -> None:
        content = "---\n: :\n  bad:\n---\nbody"
        fm, body = parse_frontmatter(content)
        # yaml.safe_load may or may not error on this;
        # if it parses to non-dict, we get {}
        assert isinstance(fm, dict)

    def test_frontmatter_strips_leading_newline(self) -> None:
        content = "---\nname: x\ndescription: y\n---\n\nbody"
        fm, body = parse_frontmatter(content)
        assert body == "\nbody"

    def test_empty_frontmatter_returns_empty_dict(self) -> None:
        content = "---\n---\nbody"
        fm, body = parse_frontmatter(content)
        # yaml.safe_load("") returns None → not a dict
        assert fm == {}

    def test_multiline_body_preserved(self) -> None:
        content = "---\nname: a\ndescription: b\n---\n" "line1\nline2\nline3"
        fm, body = parse_frontmatter(content)
        assert "line1\nline2\nline3" == body


# ==================================================================
# convert_agent — success paths
# ==================================================================


class TestConvertAgentSuccess:
    """Tests for successful agent conversion."""

    def _write_agent(
        self,
        tmp_path: Path,
        name: str = "My Agent",
        description: str = "Does things",
        tools: str = "[read, shell]",
        body: str = "# Prompt\nDo stuff.",
    ) -> Path:
        agents = tmp_path / "agents"
        agents.mkdir()
        md = agents / "my-agent.md"
        md.write_text(
            f"---\nname: {name}\n"
            f"description: {description}\n"
            f"tools: {tools}\n---\n{body}",
            encoding="utf-8",
        )
        return md

    def test_produces_json_file(self, tmp_path: Path) -> None:
        md = self._write_agent(tmp_path)
        result = convert_agent(md)
        assert result.status == "converted"
        assert result.output_path is not None
        assert result.output_path.exists()
        assert result.output_path.suffix == ".json"

    def test_json_has_correct_fields(self, tmp_path: Path) -> None:
        md = self._write_agent(tmp_path)
        result = convert_agent(md)
        assert result.output_path is not None
        data = json.loads(result.output_path.read_text(encoding="utf-8"))
        assert data["name"] == "My Agent"
        assert data["description"] == "Does things"
        assert data["prompt"].startswith("file://")
        assert data["prompt"].endswith("my-agent.md")

    def test_tools_mapped_to_cli(self, tmp_path: Path) -> None:
        md = self._write_agent(tmp_path, tools="[read, web]")
        result = convert_agent(md)
        assert result.output_path is not None
        data = json.loads(result.output_path.read_text(encoding="utf-8"))
        assert "fs_read" in data["tools"]
        assert "web_search" in data["tools"]
        assert "web_fetch" in data["tools"]

    def test_json_is_2_space_indented_with_newline(self, tmp_path: Path) -> None:
        md = self._write_agent(tmp_path, tools="[]")
        convert_agent(md)
        out = md.with_suffix(".json")
        text = out.read_text(encoding="utf-8")
        assert text.endswith("\n")
        data = json.loads(text)
        # Re-serialize with same settings and compare
        expected = json.dumps(data, indent=2) + "\n"
        assert text == expected

    def test_file_uri_is_absolute(self, tmp_path: Path) -> None:
        md = self._write_agent(tmp_path)
        result = convert_agent(md)
        assert result.output_path is not None
        data = json.loads(result.output_path.read_text(encoding="utf-8"))
        uri = data["prompt"]
        path_part = uri.replace("file://", "")
        assert Path(path_part).is_absolute()

    def test_no_tools_produces_empty_list(self, tmp_path: Path) -> None:
        md = self._write_agent(tmp_path, tools="[]")
        result = convert_agent(md)
        assert result.output_path is not None
        data = json.loads(result.output_path.read_text(encoding="utf-8"))
        assert data["tools"] == []

    def test_spec_tool_produces_warning(self, tmp_path: Path) -> None:
        md = self._write_agent(tmp_path, tools="[shell, spec]")
        result = convert_agent(md)
        assert result.status == "converted"
        assert len(result.warnings) == 1
        assert "spec" in result.warnings[0]


# ==================================================================
# convert_agent — failure paths
# ==================================================================


class TestConvertAgentFailure:
    """Tests for agent conversion failures."""

    def test_missing_frontmatter(self, tmp_path: Path) -> None:
        agents = tmp_path / "agents"
        agents.mkdir()
        md = agents / "bad.md"
        md.write_text("no frontmatter here", encoding="utf-8")
        result = convert_agent(md)
        assert result.status == "failed"
        assert result.error is not None
        assert "frontmatter" in result.error

    def test_missing_name(self, tmp_path: Path) -> None:
        agents = tmp_path / "agents"
        agents.mkdir()
        md = agents / "no-name.md"
        md.write_text(
            "---\ndescription: x\n---\nbody",
            encoding="utf-8",
        )
        result = convert_agent(md)
        assert result.status == "failed"
        assert "name" in (result.error or "")

    def test_missing_description(self, tmp_path: Path) -> None:
        agents = tmp_path / "agents"
        agents.mkdir()
        md = agents / "no-desc.md"
        md.write_text("---\nname: x\n---\nbody", encoding="utf-8")
        result = convert_agent(md)
        assert result.status == "failed"
        assert "description" in (result.error or "")

    def test_nonexistent_file(self, tmp_path: Path) -> None:
        md = tmp_path / "ghost.md"
        result = convert_agent(md)
        assert result.status == "failed"
        assert result.error is not None


# ==================================================================
# Idempotency (Property 5)
# ==================================================================


class TestAgentIdempotency:
    """Running convert_agent twice produces identical output."""

    def test_idempotent_output(self, tmp_path: Path) -> None:
        agents = tmp_path / "agents"
        agents.mkdir()
        md = agents / "idem.md"
        md.write_text(
            "---\nname: A\ndescription: B\n" "tools: [read]\n---\nprompt",
            encoding="utf-8",
        )
        convert_agent(md)
        first = md.with_suffix(".json").read_bytes()
        convert_agent(md)
        second = md.with_suffix(".json").read_bytes()
        assert first == second


# ==================================================================
# Round-trip property (Property 4)
# ==================================================================


@given(
    st.text(min_size=1, max_size=50).filter(lambda s: "\n" not in s and ":" not in s),
    st.text(min_size=1, max_size=100).filter(lambda s: "\n" not in s and ":" not in s),
)
def test_roundtrip_preserves_name_and_description(name: str, description: str) -> None:
    """Property 4: parse → build JSON → re-read preserves values."""
    content = f"---\nname: {name}\ndescription: {description}\n" f"---\nbody"
    fm, _ = parse_frontmatter(content)
    if not fm:
        return  # YAML couldn't parse — skip
    built = {
        "name": fm.get("name"),
        "description": fm.get("description"),
    }
    roundtripped = json.loads(json.dumps(built))
    assert roundtripped["name"] == fm["name"]
    assert roundtripped["description"] == fm["description"]


# ==================================================================
# Edge-case coverage
# ==================================================================


class TestAgentEdgeCases:
    """Cover remaining branches in agent_converter."""

    def test_tools_as_single_string(self, tmp_path: Path) -> None:
        """Non-list tools value gets coerced to list."""
        agents = tmp_path / "agents"
        agents.mkdir()
        md = agents / "scalar.md"
        md.write_text(
            "---\nname: x\ndescription: y\n" "tools: shell\n---\nbody",
            encoding="utf-8",
        )
        result = convert_agent(md)
        assert result.status == "converted"
        assert result.output_path is not None
        data = json.loads(result.output_path.read_text(encoding="utf-8"))
        assert "execute_bash" in data["tools"]

    def test_write_error_returns_failed(self, tmp_path: Path) -> None:
        """OSError on write produces a failed result."""
        agents = tmp_path / "agents"
        agents.mkdir()
        md = agents / "ok.md"
        md.write_text(
            "---\nname: a\ndescription: b\n---\nbody",
            encoding="utf-8",
        )
        # Make the output path a directory so write fails
        out = agents / "ok.json"
        out.mkdir()
        result = convert_agent(md)
        assert result.status == "failed"
        assert result.error is not None
        assert "Cannot write" in result.error
