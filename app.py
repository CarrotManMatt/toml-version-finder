"""Primary HTTP response generation functionality."""

from typing import TYPE_CHECKING

import aiohttp
import gidgethub
from gidgethub.aiohttp import GitHubAPI
from starlette.applications import Starlette
from starlette.exceptions import HTTPException
from starlette.responses import JSONResponse
from starlette.routing import Route

import config
import version_finders
from exceptions import (
    BaseUnknownPathParameterError,
    BaseUnsupportedError,
    InvalidVersionFileContentError,
    UnknowAPIVersionError,
)
from validators import (
    validate_owner,
    validate_package_name,
    validate_repo,
)

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence
    from typing import Final

    from starlette.requests import Request
    from starlette.responses import Response


__all__: "Sequence[str]" = ("app",)


def _version_file_from_url(
    request_path_params: "Mapping[str, object]",
) -> version_finders.VersionMap:
    owner: str = _parse_value_from_path_params(request_path_params, "owner")
    validate_owner(owner)

    repo: str = _parse_value_from_path_params(request_path_params, "repo")
    validate_repo(repo)

    package_name: str = _parse_value_from_path_params(request_path_params, "package_name")
    validate_package_name(package_name)

    return version_finders.VersionMap[
        (
            f"{owner.upper().replace('-', '_').replace('.', '_')}__"
            f"{repo.upper().replace('-', '_').replace('.', '_')}__"
            f"{package_name.upper().replace('-', '_').replace('.', '_')}"
        )
    ]


def _parse_value_from_path_params(
    request_path_params: "Mapping[str, object]", param_name: str
) -> str:
    value: object | None = request_path_params.get(param_name, None)
    if value is None or not isinstance(value, str):
        INVALID_PARAM_MESSAGE: Final[str] = (
            f"Path must contain a string parameter called '{param_name}'."
        )
        raise ValueError(INVALID_PARAM_MESSAGE)

    return value


async def _toml_find_version_endpoint(request: "Request") -> "Response":
    api_version: str = (
        _parse_value_from_path_params(request.path_params, "api_version").lower().strip()
    )
    if api_version != "v1":
        raise UnknowAPIVersionError(api_version)

    unknown_version_request_error: KeyError
    try:
        version_file: version_finders.VersionMap = _version_file_from_url(request.path_params)
    except KeyError as unknown_version_request_error:
        raise HTTPException(status_code=404) from unknown_version_request_error

    file_type: str = (
        _parse_value_from_path_params(request.path_params, "file_type").lower().strip()
    )

    return JSONResponse(
        {
            "api_version": api_version,
            "file_type": file_type,
            "package_version": await version_file.fetch_version(file_type),
            "package_name": version_file.value.package_name,
        }
    )


async def _healthcheck_endpoint(_request: "Request") -> "Response":
    session: object
    async with aiohttp.ClientSession() as session:
        github_client: GitHubAPI = GitHubAPI(
            session, requester="", oauth_token=str(config.GITHUB_API_KEY)
        )
        await github_client.getitem("/octocat")

    return JSONResponse({"status": "ok"})


app: Starlette = Starlette(
    debug=config.DEBUG,
    routes=[
        Route("/healthcheck", _healthcheck_endpoint),
        Route(
            "/{api_version}/{file_type}/{owner}/{repo}/{package_name}",
            _toml_find_version_endpoint,
        ),
    ],
    exception_handlers={
        BaseUnsupportedError: BaseUnsupportedError.exception_handler,
        InvalidVersionFileContentError: InvalidVersionFileContentError.exception_handler,
        gidgethub.GitHubException: (
            lambda _request, exc: JSONResponse(
                {"error_message": f"Github: {exc}"}, status_code=502
            )
        ),
        BaseUnknownPathParameterError: BaseUnknownPathParameterError.exception_handler,
    },
)
