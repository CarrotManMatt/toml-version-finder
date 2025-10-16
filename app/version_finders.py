"""Package version finders which can parse from lock or PEP621 files."""

import abc
import re
import tomllib
from collections.abc import Iterable, Mapping
from enum import Enum
from pathlib import PurePosixPath
from tomllib import TOMLDecodeError
from typing import TYPE_CHECKING, final, override

from packaging.requirements import Requirement
from typed_classproperties import classproperty

from exceptions import (
    InvalidVersionFileContentError,
    MissingPackageInVersionFileError,
    UnknownFileTypeError,
    UnsupportedVersionFinderError,
)
from file_fetchers import GitHubFileFetcher
from validators import validate_package_name

if TYPE_CHECKING:
    from collections.abc import Sequence
    from typing import Final, Self

    from file_fetchers import BaseFileFetcher


__all__: Sequence[str] = (
    "BaseVersionFinder",
    "PEP751VersionFinder",
    "PoetryVersionFinder",
    "UVVersionFinder",
)


class BaseVersionFinder(abc.ABC):
    """Core functionality for version finder implementation classes."""

    @override
    def __init__(
        self,
        *,
        lock_file_fetcher: BaseFileFetcher,
        lock_subdirectory: PurePosixPath | None = None,
        pep621_file_fetcher: BaseFileFetcher,
        pep621_subdirectory: PurePosixPath | None = None,
        package_name: str,
    ) -> None:
        self._lock_file_fetcher: BaseFileFetcher = lock_file_fetcher
        self._lock_subdirectory: PurePosixPath | None = lock_subdirectory
        self._pep621_file_fetcher: BaseFileFetcher = pep621_file_fetcher
        self._pep621_subdirectory: PurePosixPath | None = pep621_subdirectory

        validate_package_name(package_name)
        self._package_name: str = re.sub(r"[-_.]+", "-", package_name).lower()

    @classmethod
    def _convert_toml(cls, raw_toml: str) -> Mapping[str, object]:
        toml_decode_error: TOMLDecodeError
        try:
            return tomllib.loads(raw_toml)
        except TOMLDecodeError as toml_decode_error:
            raise InvalidVersionFileContentError from toml_decode_error

    @classmethod
    def shortcut_factory(
        cls,
        *,
        file_fetcher: BaseFileFetcher,
        subdirectory: PurePosixPath | None = None,
        package_name: str,
    ) -> Self:
        """Retrieve a partially initialised version finder with the given arguments."""
        return cls(
            lock_file_fetcher=file_fetcher,
            lock_subdirectory=subdirectory,
            pep621_file_fetcher=file_fetcher,
            pep621_subdirectory=subdirectory,
            package_name=package_name,
        )

    @classmethod
    @abc.abstractmethod
    async def _parse_lock(cls, *, raw_lock_contents: str, package_name: str) -> str:
        pass

    @final
    async def parse_lock(self) -> str:
        """Retrieve the distinct version of the selected package in the selected lock file."""
        return await self._parse_lock(
            raw_lock_contents=await self._lock_file_fetcher(content_file=self.lock_file_path),
            package_name=self.package_name,
        )

    async def parse_pep621(self) -> str:
        """Retrieve the version limits of the selected package in the selected PEP621 file."""
        project_contents: object | None = self._convert_toml(
            await self._pep621_file_fetcher(content_file=self.pep621_file_path)
        ).get("project", None)

        if project_contents is None or not isinstance(project_contents, Mapping):
            raise InvalidVersionFileContentError

        dependencies: object | None = project_contents.get("dependencies", None)

        if dependencies is None or not isinstance(dependencies, Iterable):
            raise InvalidVersionFileContentError

        dependency: object
        for dependency in dependencies:
            if not isinstance(dependency, str):
                continue

            requirement: Requirement = Requirement(dependency)
            if requirement.name != self.package_name:
                continue

            return str(requirement.specifier)

        raise MissingPackageInVersionFileError(package_name=self.package_name)

    @classproperty
    @abc.abstractmethod
    def _LOCK_FILE_NAME(cls) -> str:
        """
        The fixed file name of this version finder's lock file.

        E.g. `uv.lock`, `poetry.lock` or `pylock.toml`.
        """

    @property
    def lock_file_path(self) -> PurePosixPath:
        """The location of this version finder's lock file."""
        return (
            PurePosixPath("/") if self._lock_subdirectory is None else self._lock_subdirectory
        ) / self._LOCK_FILE_NAME

    @property
    def pep621_file_path(self) -> PurePosixPath:
        """
        The location of this version finder's PEP621 pyproject.toml file.

        This file can be used as an alternative version identifier for a given package,
        in contrast to the associated lock file finder.
        """
        return (
            PurePosixPath("/") if self._lock_subdirectory is None else self._lock_subdirectory
        ) / "pyproject.toml"

    @property
    def package_name(self) -> str:
        """The name of the package that will be searched for using this finder callable."""
        return self._package_name


class PoetryVersionFinder(BaseVersionFinder):
    """Finder callable to retrieve a package's locked version from a poetry lock file."""

    @classproperty
    @override
    def _LOCK_FILE_NAME(cls) -> str:
        return "poetry.lock"

    @classmethod
    @override
    async def _parse_lock(cls, *, raw_lock_contents: str, package_name: str) -> str:
        current_packages: object | None = cls._convert_toml(raw_lock_contents).get(
            "package", None
        )

        if current_packages is None or not isinstance(current_packages, Iterable):
            raise InvalidVersionFileContentError

        current_package: object
        for current_package in current_packages:
            if not isinstance(current_package, Mapping):
                continue

            current_package_name: object | None = current_package.get("name", None)

            if (
                current_package_name is None
                or not isinstance(current_package_name, str)
                or current_package_name != package_name
            ):
                continue

            current_package_version: object | None = current_package.get("version", None)

            if current_package_version is None or not isinstance(current_package_version, str):
                raise InvalidVersionFileContentError

            return current_package_version

        raise MissingPackageInVersionFileError(package_name=package_name)


class UVVersionFinder(PoetryVersionFinder):
    """Finder callable to retrieve a package's locked version from a uv lock file."""

    @classproperty
    @override
    def _LOCK_FILE_NAME(cls) -> str:
        return "uv.lock"


class PEP751VersionFinder(BaseVersionFinder):
    """Finder callable to retrieve a package's locked version from a PEP751 lock file."""

    @classproperty
    @override
    def _LOCK_FILE_NAME(cls) -> str:
        return "pylock.toml"

    @classmethod
    @override
    async def _parse_lock(cls, *, raw_lock_contents: str, package_name: str) -> str:
        UNSUPPORTED_VERSION_FINDER_MESSAGE: Final[str] = "PEP751 is not yet supported."
        raise UnsupportedVersionFinderError(UNSUPPORTED_VERSION_FINDER_MESSAGE)


class VersionMap(Enum):
    """Known acceptable packages within known project locations."""

    CSSUOB__TEX_BOT_PY_V2__PY_CORD = UVVersionFinder.shortcut_factory(
        file_fetcher=GitHubFileFetcher(owner="CSSUoB", repo="TeX-Bot-Py-V2"),
        package_name="py-cord",
    )
    CARROTMANMATT__FLAKE8_CARROT__FLAKE8 = UVVersionFinder.shortcut_factory(
        file_fetcher=GitHubFileFetcher(owner="CarrotManMatt", repo="flake8-carrot"),
        package_name="flake8",
    )
    CARROTMANMATT__CCFT_PYMARKDOWN__PYMARKDOWNLNT = UVVersionFinder.shortcut_factory(
        file_fetcher=GitHubFileFetcher(owner="CarrotManMatt", repo="ccft-pymarkdown"),
        package_name="pymarkdownlnt",
    )

    async def fetch_version(self, file_type: str) -> str:
        """Retrieve the current version of the selected package inside the selected project."""
        version_finder: BaseVersionFinder = self.value

        match file_type:
            case "lock":
                return await version_finder.parse_lock()
            case "pep621":
                return await version_finder.parse_pep621()
            case _:
                raise UnknownFileTypeError(file_type=file_type)
