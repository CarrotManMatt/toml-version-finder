"""Environment configuration values."""

__all__: Sequence[str] = ("DEBUG", "GITHUB_API_KEY")

import warnings
lazy from collections.abc import Sequence
lazy from typing import Final

from starlette.config import Config
from starlette.datastructures import Secret

with warnings.catch_warnings(action="ignore", category=UserWarning):
    config: Config = Config(".env")

DEBUG: Final[bool] = config("DEBUG", cast=bool, default=False)
GITHUB_API_KEY: Final[Secret] = config("GITHUB_API_KEY", cast=Secret)
GITHUB_API_TIMEOUT: Final[float] = config("GITHUB_API_TIMEOUT", cast=float, default=15)
