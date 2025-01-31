"""Custom exception classes used throughout this project."""

import abc
from typing import TYPE_CHECKING, override

from starlette.responses import JSONResponse
from typed_classproperties import classproperty

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from starlette.requests import Request

    from file_fetchers import BaseFileFetcher
    from version_finders import BaseVersionFinder

__all__: "Sequence[str]" = (
    "BaseUnknownPathParameterError",
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
        self.message: str = (
            message.strip() if message is not None else message
        ) or self.DEFAULT_MESSAGE
        del message

        super().__init__(self.message)

    @classproperty
    @abc.abstractmethod
    def DEFAULT_MESSAGE(cls) -> str:
        """Default message to be used for this exception if no custom message is given."""

    @classproperty
    @abc.abstractmethod
    def STATUS_CODE(cls) -> int:
        """HTTP status code to use when returning this exception as an error response."""

    def _get_additional_details(self) -> "Mapping[str, object]":
        """Create the content to be used when converting this exception to an HTTP response."""
        return {}

    @override
    def __str__(self) -> str:
        return self.message

    @classmethod
    def exception_handler(cls, _request: "Request", exc: Exception) -> "JSONResponse":
        """Starlette exception handler to return a correct HTTP response for this exception."""
        if not isinstance(exc, cls):
            raise TypeError

        return JSONResponse(
            {"error_message": exc.message, "details": cls._get_additional_details(exc)},
            status_code=cls.STATUS_CODE,
        )


class BaseUnknownPathParameterError(_BaseCustomException, ValueError, abc.ABC):
    """Base custom exception class for when a given URL path parameter is unknown."""

    @override
    def __init__(self, message: str | None = None, unknown_value: str | None = None) -> None:
        self._unknown_value: str | None = (
            unknown_value.strip() if unknown_value is not None else unknown_value
        )
        del unknown_value

        super().__init__(message=message)

    @override
    def __str__(self) -> str:
        return (
            f"{self.message.removesuffix('.')}: '{self._unknown_value}'."
            if self._unknown_value
            else self.message
        )

    @classproperty
    @override
    def STATUS_CODE(cls) -> int:
        return 404


class UnknownFileTypeError(BaseUnknownPathParameterError):
    """The selected 'file_type' is not a valid value."""

    @override
    def __init__(self, message: str | None = None, file_type: str | None = None) -> None:
        super().__init__(message=message, unknown_value=file_type)

    @classproperty
    @override
    def DEFAULT_MESSAGE(cls) -> str:
        return "Unknown file type."

    @property
    def file_type(self) -> str | None:
        """The unknown value that was used as a file type."""
        return self._unknown_value

    @file_type.setter
    def file_type(self, __value: str, /) -> None:
        self._unknown_value = __value

    @override
    def _get_additional_details(self) -> "Mapping[str, object]":
        return {"file_type": self.file_type}


class BaseUnsupportedError(_BaseCustomException, abc.ABC):
    """Base exception class for errors arising from an implementation being unsupported."""

    @classproperty
    @override
    def STATUS_CODE(cls) -> int:
        return 501


class _UnsupportedClassError[T](BaseUnsupportedError, abc.ABC):
    @override
    def __init__(
        self,
        message: str | None = None,
        unsupported_class: type[T] | None = None,
    ) -> None:
        self._unsupported_class: type[T] | None = unsupported_class
        del unsupported_class

        super().__init__(message=message)

    @override
    def __str__(self) -> str:
        return (
            f"{self.message.removesuffix('.')}: '{self._unsupported_class}'."
            if self._unsupported_class is not None
            else self.message
        )


class UnsupportedVersionFinderError(_UnsupportedClassError["BaseVersionFinder"]):
    """The selected VersionFinder implementation is not supported."""

    @override
    def __init__(
        self,
        message: str | None = None,
        version_finder: type["BaseVersionFinder"] | None = None,
    ) -> None:
        super().__init__(message=message, unsupported_class=version_finder)

    @property
    def version_finder(self) -> type["BaseVersionFinder"] | None:
        """The VersionFinder class that is unsupported."""
        return self._unsupported_class

    @version_finder.setter
    def version_finder(self, __value: type["BaseVersionFinder"], /) -> None:
        self._unsupported_class = __value

    @classproperty
    @override
    def DEFAULT_MESSAGE(cls) -> str:
        return "Unsupported version finder."

    @override
    def _get_additional_details(self) -> "Mapping[str, object]":
        return (
            {
                "version_finder_name": self.version_finder.__name__,
                "version_finder_class": str(self.version_finder),
            }
            if self.version_finder is not None
            else super()._get_additional_details()
        )


class UnsupportedFileFetcherError(_UnsupportedClassError["BaseFileFetcher"]):
    """The selected FileFetcher implementation is not supported."""

    @override
    def __init__(
        self,
        message: str | None = None,
        file_fetcher: type["BaseFileFetcher"] | None = None,
    ) -> None:
        super().__init__(message=message, unsupported_class=file_fetcher)

    @property
    def file_fetcher(self) -> type["BaseFileFetcher"] | None:
        """The FileFetcher class that is unsupported."""
        return self._unsupported_class

    @file_fetcher.setter
    def file_fetcher(self, __value: type["BaseFileFetcher"], /) -> None:
        self._unsupported_class = __value

    @classproperty
    @override
    def DEFAULT_MESSAGE(cls) -> str:
        return "Unsupported file fetcher."

    @override
    def _get_additional_details(self) -> "Mapping[str, object]":
        return (
            {
                "file_fetcher_name": self.file_fetcher.__name__,
                "file_fetcher_class": str(self.file_fetcher),
            }
            if self.file_fetcher is not None
            else super()._get_additional_details()
        )


class InvalidVersionFileContentError(_BaseCustomException, ValueError):
    """The retrieved version file's content was not valid."""

    @classproperty
    @override
    def DEFAULT_MESSAGE(cls) -> str:
        return "Invalid version file content."

    @classproperty
    @override
    def STATUS_CODE(cls) -> int:
        return 502


class InvalidVersionFileEncodingError(InvalidVersionFileContentError):
    """The retrieved version file's encoding was not valid."""

    @override
    def __init__(self, message: str | None = None, encoding: str | None = None) -> None:
        self.encoding: str | None = encoding.strip() if encoding is not None else encoding
        del encoding

        super().__init__(message=message)

    @classproperty
    @override
    def DEFAULT_MESSAGE(cls) -> str:
        return "Unknown version file encoding."

    @override
    def __str__(self) -> str:
        return (
            f"{self.message.removesuffix('.')}: '{self.encoding}'."
            if self.encoding
            else self.message
        )

    @override
    def _get_additional_details(self) -> "Mapping[str, object]":
        return (
            {"encoding": self.encoding} if self.encoding else super()._get_additional_details()
        )


class MissingPackageInVersionFileError(InvalidVersionFileContentError):
    """The selected package could not be found in the given version file."""

    @override
    def __init__(self, message: str | None = None, package_name: str | None = None) -> None:
        self.package_name: str | None = (
            package_name.strip() if package_name is not None else package_name
        )
        del package_name
        self._used_default_message: bool = not (
            message.strip() if message is not None else message
        )

        super().__init__(message=message)

    @classproperty
    @override
    def DEFAULT_MESSAGE(cls) -> str:
        return "Package not found in version file."

    @override
    def __str__(self) -> str:
        return (
            f"Package `{self.package_name}` not found in version file."
            if self._used_default_message and self.package_name
            else f"{self.message.removesuffix('.')}: '{self.package_name}'."
            if self.package_name
            else self.message
        )

    @override
    def _get_additional_details(self) -> "Mapping[str, object]":
        return (
            {"package_name": self.package_name}
            if self.package_name
            else super()._get_additional_details()
        )
