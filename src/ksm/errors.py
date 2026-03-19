"""Custom exception classes for ksm."""


class BundleNotFoundError(Exception):
    """Raised when a bundle name cannot be found in any registry."""

    def __init__(self, bundle_name: str) -> None:
        self.bundle_name = bundle_name
        super().__init__(f"Bundle not found: {bundle_name}")


class GitError(Exception):
    """Raised when a git subprocess operation fails."""

    def __init__(self, message: str) -> None:
        super().__init__(message)


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
