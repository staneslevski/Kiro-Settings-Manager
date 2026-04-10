"""ksm ide2cli — convert IDE config files to CLI format."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path

from ksm.converters.agent_converter import convert_agent
from ksm.converters.hook_converter import convert_hook
from ksm.errors import format_error, format_warning


@dataclass
class ConversionSummary:
    """Aggregated conversion results."""

    converted: int = 0
    skipped: list[tuple[str, str]] = field(
        default_factory=list,
    )
    failed: list[tuple[str, str]] = field(
        default_factory=list,
    )


def _scan_agents(
    kiro_dir: Path,
    summary: ConversionSummary,
) -> None:
    """Convert all agent .md files in kiro_dir/agents/."""
    agents_dir = kiro_dir / "agents"
    if not agents_dir.is_dir():
        return
    for md in sorted(agents_dir.glob("*.md")):
        result = convert_agent(md)
        if result.status == "converted":
            summary.converted += 1
        elif result.status == "skipped":
            reason = result.error or "skipped"
            summary.skipped.append((str(md), reason))
        else:
            summary.failed.append((str(md), result.error or "unknown error"))
        for w in result.warnings:
            print(
                format_warning(md.name, w, stream=sys.stderr),
                file=sys.stderr,
            )


def _scan_hooks(
    kiro_dir: Path,
    summary: ConversionSummary,
) -> None:
    """Convert all .kiro.hook files in kiro_dir/hooks/."""
    hooks_dir = kiro_dir / "hooks"
    if not hooks_dir.is_dir():
        return
    grouped: dict[str, list[dict[str, str]]] = {}
    for hook_file in sorted(hooks_dir.glob("*.kiro.hook")):
        result = convert_hook(hook_file)
        if result.status == "converted":
            summary.converted += 1
            event = result.cli_event_type
            assert event is not None
            grouped.setdefault(event, []).extend(result.cli_hook_entries)
        elif result.status == "skipped":
            if result.warnings:
                reason = result.warnings[0]
            else:
                reason = "disabled"
            summary.skipped.append((str(hook_file), reason))
        else:
            summary.failed.append(
                (
                    str(hook_file),
                    result.error or "unknown error",
                )
            )
        for w in result.warnings:
            print(
                format_warning(
                    hook_file.name,
                    w,
                    stream=sys.stderr,
                ),
                file=sys.stderr,
            )

    if grouped:
        out = hooks_dir / "_cli_hooks.json"
        text = json.dumps(grouped, indent=2) + "\n"
        out.write_text(text, encoding="utf-8")


def auto_convert(
    target_dir: Path,
    installed_paths: list[str],
) -> None:
    """Run ide2cli conversion on only the installed files.

    *installed_paths* are relative to *target_dir* (e.g.
    ``agents/my-agent.md``, ``hooks/on-save.kiro.hook``).
    Only agent ``.md`` and hook ``.kiro.hook`` files are
    converted; everything else is silently ignored.

    For hooks the full ``hooks/`` directory is re-scanned so
    the grouped ``_cli_hooks.json`` stays complete.
    """
    agent_mds = [
        target_dir / p
        for p in installed_paths
        if p.startswith("agents/") and p.endswith(".md")
    ]
    has_hooks = any(
        p.startswith("hooks/") and p.endswith(".kiro.hook")
        for p in installed_paths
    )

    if not agent_mds and not has_hooks:
        return

    summary = ConversionSummary()

    for md in sorted(agent_mds):
        if md.is_file():
            result = convert_agent(md)
            if result.status == "converted":
                summary.converted += 1
            for w in result.warnings:
                print(
                    format_warning(md.name, w, stream=sys.stderr),
                    file=sys.stderr,
                )

    if has_hooks:
        _scan_hooks(target_dir, summary)

    if summary.converted:
        print(
            f"Auto-converted {summary.converted} file(s)"
            " to CLI format.",
            file=sys.stderr,
        )


def run_ide2cli(
    args: argparse.Namespace,
    *,
    target_dir: Path | None = None,
) -> int:
    """Run the ide2cli conversion. Returns exit code."""
    workspace_kiro = Path.cwd() / ".kiro"
    global_kiro = Path.home() / ".kiro"

    if target_dir is not None:
        dirs = [target_dir]
    else:
        dirs = [d for d in (workspace_kiro, global_kiro) if d.is_dir()]

    if not dirs:
        print(
            format_error(
                "No .kiro/ directory found.",
                "Neither workspace nor global " ".kiro/ exists.",
                "Run 'ksm init' to create one.",
                stream=sys.stderr,
            ),
            file=sys.stderr,
        )
        return 1

    summary = ConversionSummary()
    for kiro_dir in dirs:
        _scan_agents(kiro_dir, summary)
        _scan_hooks(kiro_dir, summary)

    total = summary.converted + len(summary.skipped) + len(summary.failed)
    if total == 0:
        print(
            "No convertible files found.",
            file=sys.stderr,
        )
        return 0

    print(
        f"Converted: {summary.converted} | "
        f"Skipped: {len(summary.skipped)} | "
        f"Failed: {len(summary.failed)}",
        file=sys.stderr,
    )

    for name, err in summary.failed:
        print(
            format_error(
                name,
                err,
                "Fix the file and re-run ksm ide2cli.",
                stream=sys.stderr,
            ),
            file=sys.stderr,
        )

    if summary.converted == 0 and summary.failed:
        return 1
    return 0
