"""Typo suggestion for unknown CLI commands.

Pure-Python Levenshtein distance and closest-match suggestion.
"""


def levenshtein_distance(a: str, b: str) -> int:
    """Compute Levenshtein edit distance between two strings."""
    if len(a) < len(b):
        return levenshtein_distance(b, a)
    if len(b) == 0:
        return len(a)

    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a):
        curr = [i + 1]
        for j, cb in enumerate(b):
            cost = 0 if ca == cb else 1
            curr.append(
                min(
                    prev[j + 1] + 1,  # deletion
                    curr[j] + 1,  # insertion
                    prev[j] + cost,  # substitution
                )
            )
        prev = curr
    return prev[-1]


def suggest_command(
    unknown: str,
    valid_commands: list[str],
    max_distance: int = 2,
) -> str | None:
    """Return the closest valid command within max_distance.

    Returns None if no command is close enough.
    """
    best: str | None = None
    best_dist = max_distance + 1
    for cmd in valid_commands:
        dist = levenshtein_distance(unknown, cmd)
        if dist < best_dist:
            best_dist = dist
            best = cmd
    if best_dist <= max_distance:
        return best
    return None
