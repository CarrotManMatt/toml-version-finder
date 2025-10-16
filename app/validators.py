"""Utility validator functions to ensure a value adheres to a regex specification."""

import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence
    from typing import Final, Literal


__all__: Sequence[str] = (
    "validate_owner",
    "validate_package_name",
    "validate_repo",
)


def _validate_value(
    *, pattern: str, value: str, name: str, ignore_case: bool = False
) -> Literal[True]:
    if not pattern.startswith(r"\A"):
        pattern = rf"\A{pattern}"

    if not pattern.endswith(r"\Z"):
        pattern = rf"{pattern}\Z"

    if not re.fullmatch(pattern, value, flags=re.IGNORECASE if ignore_case else 0):
        INVALID_VALUE_MESSAGE: Final[str] = f"Invalid '{name}'."
        raise ValueError(INVALID_VALUE_MESSAGE)

    return True


def validate_owner(owner: str) -> Literal[True]:
    """Ensure the given string is a valid Git repository owner name."""
    return _validate_value(pattern=r"\A[a-zA-Z0-9\-._]+\Z", value=owner, name="owner")


def validate_repo(repo: str) -> Literal[True]:
    """Ensure the given string is a valid Git repository project name."""
    return _validate_value(pattern=r"\A[a-zA-Z0-9\-._]+\Z", value=repo, name="repo")


def validate_package_name(package_name: str) -> Literal[True]:
    """Ensure the given string is a valid package name."""
    return _validate_value(
        pattern=r"\A[A-Z0-9]|[A-Z0-9][A-Z0-9._-]*[A-Z0-9]\Z",
        value=package_name,
        name="package_name",
        ignore_case=True,
    )
