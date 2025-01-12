""""""

import abc
import base64
from typing import TYPE_CHECKING, override

import aiohttp
from gidgethub.aiohttp import GitHubAPI
from starlette.exceptions import HTTPException

import config
from exceptions import InvalidVersionFileContentError
from validators import validate_owner, validate_repo

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence
    from pathlib import PurePosixPath
    from typing import Final


__all__: "Sequence[str]" = (
    "BaseFileFetcher",
    "GitHubFileFetcher",
)


class BaseFileFetcher(abc.ABC):
    """"""

    @abc.abstractmethod
    async def __call__(self, content_file: "PurePosixPath") -> str:
        """"""


class GitHubFileFetcher(BaseFileFetcher):
    """"""

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
            response: Mapping[str, object] = await github_client.getitem(
                f"/repos/{self.owner}/{self.repo}/contents/{str(content_file).removeprefix('/')}"
            )

        if response["encoding"] != "base64":
            raise HTTPException(
                status_code=502,
                detail=f"Unknown version file encoding: `{response['encoding']}`.",
            )

        if not isinstance(response["content"], str | bytes):
            raise InvalidVersionFileContentError

        # noinspection PyTypeChecker
        return base64.b64decode(response["content"]).decode()

    @property
    def owner(self) -> str:
        """"""
        return self._owner

    @property
    def repo(self) -> str:
        """"""
        return self._repo
