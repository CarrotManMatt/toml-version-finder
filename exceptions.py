"""Custom exception classes used throughout this project."""

import abc
from typing import TYPE_CHECKING, override

from starlette.responses import PlainTextResponse
from typed_classproperties import classproperty

if TYPE_CHECKING:
    from collections.abc import Sequence

    from starlette.requests import Request
    from starlette.responses import Response

__all__: "Sequence[str]" = (
    "BaseUnsupportedError",
    "InvalidVersionFileContentError",
    "MissingPackageInVersionFileError",
    "UnknownFileTypeError",
    "UnsupportedFileFetcherError",
    "UnsupportedVersionFinderError",
)


class _BaseCustomException(Exception, abc.ABC):
    """Base custom exception class that can be converted to an HTTP response."""

    @override
    def __init__(self, message: str | None = None) -> None:
        self.message: str = message or self.DEFAULT_MESSAGE

        super().__init__(message or self.DEFAULT_MESSAGE)

    @classproperty
    @abc.abstractmethod
    def DEFAULT_MESSAGE(cls) -> str:
        """Default message to be used for this exception if no custom message is given."""

    @classproperty
    @abc.abstractmethod
    def STATUS_CODE(cls) -> int:
        """HTTP status code to use when returning this exception as an error response."""

    @override
    def __str__(self) -> str:
        return self.message

    @classmethod
    def exception_handler(cls, _request: "Request", exc: Exception) -> "Response":
        """Starlette exception handler to return a correct HTTP response for this exception."""
        if not isinstance(exc, cls):
            raise TypeError

        return PlainTextResponse(str(exc), status_code=cls.STATUS_CODE)


class UnknownFileTypeError(_BaseCustomException, ValueError):
    """The selected 'file_type' is not a valid value."""

    @override
    def __init__(self, message: str | None = None, file_type: str | None = None) -> None:
        if file_type is not None:
            file_type = file_type.strip()

        self.file_type: str | None = file_type

        super().__init__(
            message
            or (
                f"{self.DEFAULT_MESSAGE.removesuffix('.')}: '{self.file_type}'."
                if file_type
                else self.DEFAULT_MESSAGE
            )
        )

    @classproperty
    @override
    def DEFAULT_MESSAGE(cls) -> str:
        return "Unknown file type."

    @classproperty
    @override
    def STATUS_CODE(cls) -> int:
        return 404

    @classmethod
    @override
    def exception_handler(cls, _request: "Request", exc: Exception) -> "Response":
        if not isinstance(exc, cls):
            raise TypeError

        return PlainTextResponse(status_code=cls.STATUS_CODE)


class BaseUnsupportedError(_BaseCustomException, abc.ABC):
    """Base exception class for errors arising from an implementation being unsupported."""

    @classproperty
    @override
    def STATUS_CODE(cls) -> int:
        return 501


class UnsupportedVersionFinderError(BaseUnsupportedError):
    """The selected VersionFinder implementation is not supported."""

    @classproperty
    @override
    def DEFAULT_MESSAGE(cls) -> str:
        return "Unsupported version finder."


class UnsupportedFileFetcherError(BaseUnsupportedError):
    """The selected FileFetcher implementation is not supported."""

    @classproperty
    @override
    def DEFAULT_MESSAGE(cls) -> str:
        return "Unsupported file fetcher."


class InvalidVersionFileContentError(_BaseCustomException, ValueError):
    """The given version file's content was not valid."""

    @classproperty
    @override
    def DEFAULT_MESSAGE(cls) -> str:
        return "Invalid version file content."

    @classproperty
    @override
    def STATUS_CODE(cls) -> int:
        return 502


class MissingPackageInVersionFileError(InvalidVersionFileContentError):
    """The selected package could not be found in the given version file."""

    @override
    def __init__(self, message: str | None = None, package_name: str | None = None) -> None:
        if package_name is not None:
            package_name = package_name.strip()

        self.package_name: str | None = package_name

        super().__init__(
            message
            or (
                f"Package `{self.package_name}` not found in version file."
                if package_name
                else self.DEFAULT_MESSAGE
            )
        )

    @classproperty
    @override
    def DEFAULT_MESSAGE(cls) -> str:
        return "Package not found in version file."
