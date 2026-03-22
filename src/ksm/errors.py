"""Custom exception classes for ksm."""

from typing import TextIO

from ksm.color import error_style, muted, subtle, warning_style


class BundleNotFoundError(Exception):
    """Raised when a bundle name cannot be found in any registry."""

    def __init__(
        self,
        bundle_name: str,
        searched_registries: list[str] | None = None,
    ) -> None:
        self.bundle_name = bundle_name
        self.searched_registries = searched_registries or []
        msg = f"Bundle '{bundle_name}' not found"
        if self.searched_registries:
            names = ", ".join(self.searched_registries)
            count = len(self.searched_registries)
            msg += (
                f" in any registered registry.\n"
                f"  Searched {count} "
                f"{'registry' if count == 1 else 'registries'}"
                f": {names}\n"
                f"  Run `ksm registry ls` to see"
                f" available registries.\n"
                f"  Run `ksm add {bundle_name} --from"
                f" <git-url>` to install from a"
                f" specific source."
            )
        else:
            msg += "."
        super().__init__(msg)


class GitError(Exception):
    """Raised when a git subprocess operation fails."""

    def __init__(
        self,
        message: str,
        url: str | None = None,
        stderr_output: str | None = None,
    ) -> None:
        self.url = url
        self.stderr_output = stderr_output
        self._base_message = message
        if url:
            super().__init__(f"{message}\n  URL: {url}")
        else:
            super().__init__(message)

    def formatted_message(self) -> str:
        """Return a cleaned, actionable error message."""
        parts = [self._base_message]
        if self.url:
            parts.append(f"  URL: {self.url}")
        if self.stderr_output:
            summary = _clean_stderr(self.stderr_output)
            if summary:
                parts.append(f"  Git said: {summary}")
        if self.url:
            parts.append("  Check that the URL is correct" " and you have access.")
        return "\n".join(parts)


def _clean_stderr(stderr: str) -> str:
    """Extract the meaningful line from git stderr output."""
    for line in stderr.strip().splitlines():
        stripped = line.strip()
        if stripped.lower().startswith("fatal:"):
            return stripped[len("fatal:") :].strip()
        if stripped.lower().startswith("error:"):
            return stripped[len("error:") :].strip()
    # Fall back to last non-empty line
    lines = [ln.strip() for ln in stderr.strip().splitlines() if ln.strip()]
    return lines[-1] if lines else ""


class InvalidSubdirectoryError(Exception):
    """Raised when a dot-notation subdirectory type is invalid."""

    def __init__(self, subdirectory: str, valid: list[str]) -> None:
        self.subdirectory = subdirectory
        self.valid = valid
        super().__init__(
            f"Invalid subdirectory type: {subdirectory}. "
            f"Valid types: {', '.join(valid)}"
        )


class MutualExclusionError(Exception):
    """Raised when mutually exclusive options are combined."""

    def __init__(self, option_a: str, option_b: str) -> None:
        self.option_a = option_a
        self.option_b = option_b
        super().__init__(f"{option_a} and {option_b} are mutually exclusive")


# ------------------------------------------------------------------
# Standardised message formatting helpers (Req 13)
# ------------------------------------------------------------------


def format_error(
    what: str,
    why: str,
    fix: str,
    stream: TextIO | None = None,
) -> str:
    """Format a three-line error message.

    Returns:
        error: {what}
          {why}       ← muted
          {fix}       ← subtle

    Bundle names in {what} are styled with accent.
    """
    prefix = error_style("error:", stream=stream)
    why_styled = muted(why, stream=stream)
    fix_styled = subtle(fix, stream=stream)
    return f"{prefix} {what}\n  {why_styled}\n  {fix_styled}"


def format_warning(
    what: str,
    detail: str,
    stream: TextIO | None = None,
) -> str:
    """Format a two-line warning message.

    Returns:
        warning: {what}
          {detail}    ← muted
    """
    prefix = warning_style("warning:", stream=stream)
    detail_styled = muted(detail, stream=stream)
    return f"{prefix} {what}\n  {detail_styled}"


def format_deprecation(
    old: str,
    new: str,
    since: str,
    removal: str,
    stream: TextIO | None = None,
) -> str:
    """Format a two-line deprecation message.

    Returns:
        deprecated: `{old}` is deprecated, use `{new}` instead.
          Deprecated in {since}, will be removed in {removal}.  ← subtle
    """
    prefix = warning_style("deprecated:", stream=stream)
    timeline = subtle(
        f"Deprecated in {since}, will be removed in {removal}.",
        stream=stream,
    )
    return f"{prefix} `{old}` is deprecated," f" use `{new}` instead.\n" f"  {timeline}"
