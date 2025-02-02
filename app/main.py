"""Primary HTTP response generation functionality."""

import re
from typing import TYPE_CHECKING

import aiohttp
import gidgethub
from gidgethub.aiohttp import GitHubAPI
from starlette.applications import Starlette
from starlette.responses import JSONResponse, RedirectResponse
from starlette.routing import Route
from starlette.schemas import SchemaGenerator

import config
import version_finders
from exceptions import (
    BaseUnknownPathParameterError,
    BaseUnsupportedError,
    InvalidVersionFileContentError,
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


class _TOMLFindVersionEndpoint:
    def __init__(self, file_type: str) -> None:
        self.file_type: str = file_type

    async def __call__(self, request: "Request") -> "Response":
        """
        summary: Retrieve the specific version of a package in a project from a known TOML file
        parameters:
          - in: path
            name: owner
            required: true
            description: The owner of the repository where the version file is located
            schema:
              type: string
            example: CarrotManMatt
          - in: path
            name: repo
            required: true
            description: The name of the repository where the version file is located
            schema:
              type: string
            example: CCFT-Pymarkdown
          - in: path
            name: package_name
            required: true
            description: The name of the package to retrieve the version of
            schema:
              type: string
            example: PyMarkdownlnt
        responses:
          200:
            description: OK
            content:
              application/json:
                schema:
                  type: object
                  properties:
                    file_type:
                      type: string
                      enum: [lock, pep621]
                    package_version:
                      type: string
                      example: 1.2.3
                    package_name:
                      type: string
                      example: django
          404:
            description: One or more of the given path parameters were unknown
            content:
              application/json:
                schema:
                  type: object
                  required:
                    - error_message
                    - details
                  properties:
                    error_message:
                      description: The reason for the encountered problem
                      type: string
                    details:
                      oneOf:
                        - description: >-
                            Additional informational details arising from the problem
                          type: object
                          properties:
                            version_request_hash:
                              description: >-
                                The unique identifier of the requested package name,
                                repository owner & repository name
                                type: string
                        - description:
                            Additional informational details arising from the problem
                          type: object
                          properties:
                            file_type:
                              description: The unknown version file type that was requested
                              type: string
                        - description:
                            Additional informational details arising from the problem
                          type: object
                          properties:
                            version_finder_name:
                              description: >-
                                The name of the version finder that was expected to be used,
                                but is internally unsupported
                              type: string
                            version_finder_class:
                              description: >-
                                The Python class of the version finder
                                that was expected to be used, but is internally unsupported
                              type: string
                        - description:
                            Additional informational details arising from the problem
                          type: object
                          properties:
                            file_fetcher_name:
                              description: >-
                                The name of the file fetcher that was expected to be used,
                                but is internally unsupported
                              type: string
                            file_fetcher_class:
                              description: >-
                                The Python class of the file fetcher
                                that was expected to be used, but is internally unsupported
                              type: string
                        - description:
                            Additional informational details arising from the problem
                          type: object
                          properties:
                            encoding:
                              description: >-
                                The unknown encoding type of the file fetcher response,
                                containing the version file
                              type: string
                        - description:
                            Additional informational details arising from the problem
                          type: object
                          properties:
                            package_name:
                              description: >-
                                The name of the requested package
                                that could not be found in the fetched version file
                              type: string

          502:
            description: >-
              The connection to to the GitHub API is unavailable or incorrectly configured
            content:
              application/json:
                schema:
                  type: object
                  required:
                    - error_message
                  properties:
                    error_message:
                      description: The reason for the encountered problem
                      type: string
        """  # noqa: D205, D415
        if (
            _parse_value_from_path_params(request.path_params, "package_name").lower()
            == "pymarkdown"
        ):
            return RedirectResponse(
                f"{re.sub(request.url.path, r'(?<=\/)pymarkdown$', 'pymarkdownlnt')}"
                f"{f'?{request.url.query}' if request.url.query else ''}",
            )

        unknown_version_request_error: KeyError
        try:
            version_file: version_finders.VersionMap = _version_file_from_url(
                request.path_params
            )
        except KeyError as unknown_version_request_error:
            return JSONResponse(
                {
                    "error_message": "Unknown version file request.",
                    "details": {
                        "version_request_hash": str(unknown_version_request_error).strip("'")
                    },
                },
                status_code=404,
            )

        return JSONResponse(
            {
                "file_type": self.file_type,
                "package_version": await version_file.fetch_version(self.file_type),
                "package_name": version_file.value.package_name,
            }
        )


async def _healthcheck_endpoint(_request: "Request") -> "Response":
    """
    summary: Retrieve a simple response for whether the application is alive
    responses:
      200:
        description: OK
        content:
          application/json:
            schema:
              type: object
              required:
                - status
              properties:
                status:
                  type: string
                  enum: [OK]
      502:
        description: >-
          The connection to to the GitHub API is unavailable or incorrectly configured
        content:
          application/json:
            schema:
              type: object
              required:
                - error_message
              properties:
                error_message:
                  description: The reason for the encountered problem
                  type: string
    """  # noqa: D205,D415
    session: object
    async with aiohttp.ClientSession(conn_timeout=config.GITHUB_API_TIMEOUT) as session:
        github_client: GitHubAPI = GitHubAPI(
            session, requester="", oauth_token=str(config.GITHUB_API_KEY)
        )
        await github_client.getitem("/octocat")

    return JSONResponse({"status": "ok"})


schemas: SchemaGenerator = SchemaGenerator(
    {
        "openapi": "3.0.0",
        "info": {
            "title": "TOML Version Finder API",
            "version": "1.0.0",
            "contact": {"email": "matt@carrotmanmatt.com"},
            "license": {
                "name": "GPL-3.0-or-later",
                "url": "https://raw.githubusercontent.com/CarrotManMatt/toml-version-finder/refs/heads/main/LICENSE",
            },
        },
        "servers": [{"url": "https://toml-version-finder.carrotmanmatt.com"}],
    }
)

app: Starlette = Starlette(
    debug=config.DEBUG,
    routes=[
        Route(
            "/schema",
            endpoint=lambda request: schemas.OpenAPIResponse(request=request),
            include_in_schema=False,
        ),
        Route("/healthcheck", _healthcheck_endpoint),
        *[
            Route(
                f"/{file_type}/{{owner}}/{{repo}}/{{package_name}}",
                endpoint=_TOMLFindVersionEndpoint(file_type).__call__,
            )
            for file_type in ("lock", "pep621")
        ],
    ],
    exception_handlers={
        BaseUnsupportedError: BaseUnsupportedError.exception_handler,
        InvalidVersionFileContentError: InvalidVersionFileContentError.exception_handler,
        gidgethub.GitHubException: (
            lambda _request, exc: JSONResponse(
                {"error_message": f"Github: {exc}"}, status_code=502
            )
        ),
        **{
            exception: (
                lambda _request, exc: JSONResponse(
                    {"error_message": f"Proxy: {exc}"}, status_code=502
                )
            )
            for exception in (
                aiohttp.client_exceptions.ConnectionTimeoutError,
                aiohttp.client_exceptions.ClientConnectorDNSError,
            )
        },
        BaseUnknownPathParameterError: BaseUnknownPathParameterError.exception_handler,
    },
)
