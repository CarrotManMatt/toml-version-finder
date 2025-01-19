"""File fetchers which can retrieve a selected file from a known location."""

import abc
import base64
from typing import TYPE_CHECKING, TypedDict, override

import aiohttp
from gidgethub.aiohttp import GitHubAPI

import config
from exceptions import InvalidVersionFileContentError, InvalidVersionFileEncodingError
from validators import validate_owner, validate_repo

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import PurePosixPath
    from typing import Final


__all__: "Sequence[str]" = (
    "BaseFileFetcher",
    "GitHubFileFetcher",
)


class BaseFileFetcher(abc.ABC):
    """Fetcher callable to fetch a chosen file from a known location."""

    @abc.abstractmethod
    async def __call__(self, content_file: "PurePosixPath") -> str:
        """Fetch the selected file using a subclass's fetching implementation."""


class GitHubFileFetcher(BaseFileFetcher):
    """Fetcher callable to download a chosen file from an owner's GitHub repository."""

    if TYPE_CHECKING:

        class _GitHubAPIResponse(TypedDict):
            encoding: str
            content: object

    @override
    def __init__(self, *, owner: str, repo: str) -> None:
        validate_owner(owner)
        self._owner: str = owner

        validate_repo(repo)
        self._repo: str = repo

    @override
    async def __call__(self, content_file: "PurePosixPath") -> str:
        if not content_file.is_absolute():
            NON_ABSOLUTE_PATH_MESSAGE: Final[str] = (
                "Given 'content_file' must be an absolute path."
            )
            raise ValueError(NON_ABSOLUTE_PATH_MESSAGE)

        session: object
        async with aiohttp.ClientSession() as session:
            github_client: GitHubAPI = GitHubAPI(
                session, f"{self.owner}/{self.repo}", oauth_token=str(config.GITHUB_API_KEY)
            )
            response: GitHubFileFetcher._GitHubAPIResponse = await github_client.getitem(
                f"/repos/{self.owner}/{self.repo}/contents/{str(content_file).removeprefix('/')}"
            )

        if response["encoding"] != "base64":
            raise InvalidVersionFileEncodingError(encoding=response["encoding"])

        if not isinstance(response["content"], str | bytes):
            raise InvalidVersionFileContentError

        return base64.b64decode(response["content"]).decode()

    @property
    def owner(self) -> str:
        """Associated GitHub owner of the repository where the file will be fetched from."""
        return self._owner

    @property
    def repo(self) -> str:
        """Associated GitHub repository name where the file will be fetched from."""
        return self._repo
