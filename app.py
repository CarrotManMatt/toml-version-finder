"""Primary HTTP response generation functionality."""

from typing import TYPE_CHECKING

import gidgethub
from starlette.applications import Starlette
from starlette.exceptions import HTTPException
from starlette.responses import JSONResponse, PlainTextResponse
from starlette.routing import Route

import config
import version_finders
from exceptions import (
    BaseUnsupportedError,
    InvalidVersionFileContentError,
    UnknownFileTypeError,
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
    unknown_version_request_error: KeyError
    try:
        version_file: version_finders.VersionMap = _version_file_from_url(request.path_params)
    except KeyError as unknown_version_request_error:
        raise HTTPException(status_code=404) from unknown_version_request_error

    return JSONResponse(
        await version_file.fetch_version(
            _parse_value_from_path_params(request.path_params, "file_type").lower().strip()
        )
    )


def _gidgethub_exception_handler(_request: "Request", exc: Exception) -> "Response":
    return PlainTextResponse(f"GitHub: {exc}", status_code=502)


app: Starlette = Starlette(
    debug=config.DEBUG,
    routes=[Route("/{file_type}/{owner}/{repo}/{package_name}", _toml_find_version_endpoint)],
    exception_handlers={
        BaseUnsupportedError: BaseUnsupportedError.exception_handler,
        InvalidVersionFileContentError: InvalidVersionFileContentError.exception_handler,
        UnknownFileTypeError: UnknownFileTypeError.exception_handler,
        gidgethub.GitHubException: _gidgethub_exception_handler,
    },
)
