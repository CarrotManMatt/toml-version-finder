"""Environment configuration values."""

import warnings
from typing import TYPE_CHECKING

from starlette.config import Config
from starlette.datastructures import Secret

if TYPE_CHECKING:
    from collections.abc import Sequence
    from typing import Final

__all__: "Sequence[str]" = ("DEBUG", "GITHUB_API_KEY")


with warnings.catch_warnings(action="ignore", category=UserWarning):
    config: Config = Config(".env")

DEBUG: "Final[bool]" = config("DEBUG", cast=bool, default=False)
GITHUB_API_KEY: "Final[Secret]" = config("GITHUB_API_KEY", cast=Secret)
GITHUB_API_TIMEOUT: "Final[float]" = config("GITHUB_API_TIMEOUT", cast=float, default=15)
