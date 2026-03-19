"""Shared fixtures and Hypothesis profile configuration."""

import os

from hypothesis import Verbosity, settings

# Local development profile: fast feedback
settings.register_profile(
    "dev",
    max_examples=15,
    verbosity=Verbosity.normal,
    deadline=None,
)

# CI/CD profile: thorough validation
settings.register_profile(
    "ci",
    max_examples=100,
    verbosity=Verbosity.verbose,
    deadline=None,
)

# Load profile from environment or default to dev
settings.load_profile(os.getenv("HYPOTHESIS_PROFILE", "dev"))
