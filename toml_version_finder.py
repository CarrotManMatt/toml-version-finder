""""""
import re
import tomllib
from collections.abc import Sequence

__all__: Sequence[str] = ("app", "DEBUG", "GITHUB_API_KEY")


import base64
import functools
from collections.abc import Iterable, Mapping
from enum import Enum
from tomllib import TOMLDecodeError
from typing import Final, Literal, Self

import aiohttp
from gidgethub.aiohttp import GitHubAPI
from starlette.applications import Starlette
from starlette.config import Config
from starlette.datastructures import Secret
from starlette.exceptions import HTTPException
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.routing import Route

INVALID_CONTENT_EXCEPTION: HTTPException = HTTPException(
    status_code=502,
    detail="Invalid version file content.",
)

_config: Config = Config(".env")

DEBUG: Final[bool] = _config("DEBUG", cast=bool, default=False)
GITHUB_API_KEY: Final[Secret] = _config("GITHUB_API_KEY", cast=Secret)

del _config

def validate_value(*, pattern: str, value: str, name: str) -> Literal[True]:
    """"""
    if not re.fullmatch(pattern, value):
        INVALID_VALUE_MESSAGE: Final[str] = f"Invalid '{name}'."
        raise ValueError(INVALID_VALUE_MESSAGE)

    return True


def validate_owner(owner: str) -> Literal[True]:
    """"""
    return validate_value(
        pattern=r"\A[a-zA-Z0-9\-._]+\Z",
        value=owner,
        name="owner",
    )


def validate_repo(repo: str) -> Literal[True]:
    """"""
    return validate_value(pattern=r"\A[a-zA-Z0-9\-._]+\Z", value=repo, name="repo")


def validate_package_name(package_name: str) -> Literal[True]:
    """"""
    return validate_value(
        pattern=r"\A[a-z0-9](?:[a-z0-9\-._]*[a-z0-9])?\Z",
        value=package_name.lower(),
        name="package_name",
    )


async def github_file_fetch(*, owner: str, repo: str) -> str:
    """"""
    validate_owner(owner)
    validate_repo(repo)

    async with aiohttp.ClientSession() as session:
        github_client: GitHubAPI = GitHubAPI(
            session,
            f"{owner}/{repo}",
            oauth_token=str(GITHUB_API_KEY),
        )
        response: Mapping[str, object] = await github_client.getitem(
            f"/repos/{owner}/{repo}/contents/poetry.lock",
        )

    if response["encoding"] != "base64":
        raise HTTPException(
            status_code=502,
            detail=f"Unknown version file encoding: `{response["encoding"]}`.",
        )

    if not isinstance(response["content"], str | bytes):
        raise INVALID_CONTENT_EXCEPTION

    # noinspection PyTypeChecker
    return base64.b64decode(response["content"]).decode()


async def uv_version_parse(uv_lock_contents: str, /, *, package_name: str) -> str:
    """"""
    validate_package_name(package_name)

    toml_decode_error: TOMLDecodeError
    try:
        poetry_lock_contents: object = tomllib.loads(uv_lock_contents)
    except TOMLDecodeError as toml_decode_error:
        raise INVALID_CONTENT_EXCEPTION from toml_decode_error

    if not isinstance(poetry_lock_contents, Mapping) or "package" not in poetry_lock_contents:
        raise INVALID_CONTENT_EXCEPTION

    if not isinstance(poetry_lock_contents["package"], Iterable):
        raise INVALID_CONTENT_EXCEPTION

    package: object
    for package in poetry_lock_contents["package"]:
        if not isinstance(package, Mapping) or "name" not in package:
            raise INVALID_CONTENT_EXCEPTION

        if package["name"] != package_name:
            continue

        if "version" not in package or not isinstance(package["version"], str):
            raise INVALID_CONTENT_EXCEPTION

        return package["version"]

    raise HTTPException(
        status_code=502,
        detail=f"Package `{package_name}` not found in version file.",
    )


async def poetry_version_parse(raw_poetry_lock_contents: str, /, *, package_name: str) -> str:
    """"""
    validate_package_name(package_name)

    toml_decode_error: TOMLDecodeError
    try:
        poetry_lock_contents: object = tomllib.loads(raw_poetry_lock_contents)
    except TOMLDecodeError as toml_decode_error:
        raise INVALID_CONTENT_EXCEPTION from toml_decode_error

    if not isinstance(poetry_lock_contents, Mapping) or "package" not in poetry_lock_contents:
        raise INVALID_CONTENT_EXCEPTION

    if not isinstance(poetry_lock_contents["package"], Iterable):
        raise INVALID_CONTENT_EXCEPTION

    package: object
    for package in poetry_lock_contents["package"]:
        if not isinstance(package, Mapping) or "name" not in package:
            raise INVALID_CONTENT_EXCEPTION

        if package["name"] != package_name:
            continue

        if "version" not in package or not isinstance(package["version"], str):
            raise INVALID_CONTENT_EXCEPTION

        return package["version"]

    raise HTTPException(
        status_code=502,
        detail=f"Package `{package_name}` not found in version file.",
    )


class VersionFiles(Enum):
    """"""

    CSSUOB__TEX_BOT_PY_V2__PY_CORD = (
        functools.partial(github_file_fetch, owner="CSSUoB", repo="TeX-Bot-Py-V2"),
        functools.partial(poetry_version_parse, package_name="py-cord"),
    )
    CARROTMANMATT__FLAKE8_CARROT__FLAKE8 = (
        functools.partial(
            github_file_fetch,
            owner="CarrotManMatt",
            repo="flake8-carrot",
        ),
        functools.partial(poetry_version_parse, package_name="flake8"),
    )
    CARROTMANMATT__SMART_SERVE__DJANGO = (
        functools.partial(github_file_fetch, owner="CarrotManMatt", repo="SmartServe"),
        functools.partial(poetry_version_parse, package_name="django"),
    )
    CARROTMANMATT__CCFT_PYMARKDOWN__PYMARKDOWN = (
        functools.partial(
            github_file_fetch,
            owner="CarrotManMatt",
            repo="ccft-pymarkdown",
        ),
        functools.partial(poetry_version_parse, package_name="pymarkdownlnt"),
    )

    @classmethod
    def _parse_from_path_params(cls, request_path_params: Mapping[str, object], param_name: str) -> str:  # noqa: E501
        value: object | None = request_path_params.get(param_name, None)
        if value is None or not isinstance(value, str):
            INVALID_PARAM_MESSAGE: Final[str] = (
                f"Path must contain a string parameter called '{param_name}'."
            )
            raise ValueError(INVALID_PARAM_MESSAGE)

        return value

    @classmethod
    def from_url(cls, request_path_params: Mapping[str, object]) -> Self:
        """"""
        owner: str = cls._parse_from_path_params(request_path_params, "owner")
        validate_owner(owner)

        repo: str = cls._parse_from_path_params(request_path_params, "repo")
        validate_repo(repo)

        package_name: str = cls._parse_from_path_params(request_path_params, "package_name")
        validate_package_name(package_name)

        return cls[
            (
                f"{owner.upper().replace("-", "_").replace(".", "_")}__"
                f"{repo.upper().replace("-", "_").replace(".", "_")}__"
                f"{package_name.upper().replace("-", "_").replace(".", "_")}"
            )
        ]

    async def fetch_version(self) -> str:
        return await self.value[1](await self.value[0]())


async def toml_find_version(request: Request) -> Response:
    """"""
    unknown_version_request_error: KeyError
    try:
        version_file: VersionFiles = VersionFiles.from_url(request.path_params)
    except KeyError as unknown_version_request_error:
        raise HTTPException(status_code=404) from unknown_version_request_error

    return JSONResponse(await version_file.fetch_version())


app: Starlette = Starlette(
    debug=DEBUG,
    routes=[
        Route("/{owner}/{repo}/{package_name}", toml_find_version),
    ],
)
