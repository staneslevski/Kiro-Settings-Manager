"""Ls command for ksm.

Handles `ksm ls` — lists all installed bundles from the manifest.
Supports grouped output by scope, verbose file listing, scope
filtering, JSON output, and relative timestamps.

Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6, 10.4, 32.1
"""

import argparse
import json
import sys
from datetime import datetime, timezone

from ksm.color import bold, dim
from ksm.manifest import Manifest, ManifestEntry


def _format_relative_time(iso_ts: str) -> str:
    """Format an ISO 8601 timestamp as a relative time string."""
    try:
        ts = datetime.fromisoformat(iso_ts)
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)
        delta = now - ts
        seconds = int(delta.total_seconds())
    except (ValueError, TypeError):
        return iso_ts

    if seconds < 60:
        return "just now"
    minutes = seconds // 60
    if minutes < 60:
        unit = "minute" if minutes == 1 else "minutes"
        return f"{minutes} {unit} ago"
    hours = minutes // 60
    if hours < 24:
        unit = "hour" if hours == 1 else "hours"
        return f"{hours} {unit} ago"
    days = hours // 24
    if days < 30:
        unit = "day" if days == 1 else "days"
        return f"{days} {unit} ago"
    months = days // 30
    if months < 12:
        unit = "month" if months == 1 else "months"
        return f"{months} {unit} ago"
    years = days // 365
    unit = "year" if years == 1 else "years"
    return f"{years} {unit} ago"


def _entry_to_dict(entry: ManifestEntry) -> dict[str, object]:
    """Serialize a ManifestEntry for JSON output."""
    return {
        "bundle_name": entry.bundle_name,
        "source_registry": entry.source_registry,
        "scope": entry.scope,
        "installed_files": entry.installed_files,
        "installed_at": entry.installed_at,
        "updated_at": entry.updated_at,
    }


def _format_json(entries: list[ManifestEntry]) -> str:
    """Format entries as JSON array."""
    data = [_entry_to_dict(e) for e in entries]
    return json.dumps(data, indent=2)


def _format_grouped(
    entries: list[ManifestEntry],
    verbose: bool,
) -> str:
    """Format entries grouped by scope with headers."""
    by_scope: dict[str, list[ManifestEntry]] = {}
    for entry in entries:
        by_scope.setdefault(entry.scope, []).append(entry)

    lines: list[str] = []
    # Show scopes in consistent order: local first, then global
    for scope in ["local", "global"]:
        group = by_scope.get(scope, [])
        if not group:
            continue

        header = bold(f"{scope.capitalize()} bundles:")
        lines.append(header)

        for entry in sorted(group, key=lambda e: e.bundle_name):
            rel_time = _format_relative_time(entry.updated_at)
            source = dim(f"({entry.source_registry})")
            line = f"  {entry.bundle_name}  {source}" f"  {dim(rel_time)}"
            lines.append(line)

            if verbose:
                for f in sorted(entry.installed_files):
                    lines.append(f"    {dim(f)}")

        lines.append("")  # blank line between groups

    # Remove trailing blank line
    if lines and lines[-1] == "":
        lines.pop()

    return "\n".join(lines)


def run_ls(
    args: argparse.Namespace,
    *,
    manifest: Manifest,
) -> int:
    """Read manifest and print installed bundles.

    Returns exit code.
    """
    scope_filter: str | None = getattr(args, "scope", None)
    output_format: str = getattr(args, "output_format", "text")
    verbose: bool = getattr(args, "verbose", False)

    # Apply scope filter
    entries = list(manifest.entries)
    if scope_filter is not None:
        entries = [e for e in entries if e.scope == scope_filter]

    # JSON format
    if output_format == "json":
        print(_format_json(entries))
        return 0

    # Text format
    if not entries:
        print(
            "No bundles currently installed.",
            file=sys.stderr,
        )
        return 0

    print(_format_grouped(entries, verbose))
    return 0
