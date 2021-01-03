import contextlib
import dataclasses
import io
import os
import pathlib
import platform
import sys
import time
from typing import Any, Sequence, Type

import libcst
import libcst.codemod
from loguru import logger

from craftier import class_finder, codemod
from craftier import config as craftier_config
from craftier import fs

_LIBCST_SINK = io.StringIO()


class Error(Exception):
    """Base class for refactoring errors."""


class EmptyTransformersError(Error):
    """Error signaling no transformers were applied."""

    def __init__(self) -> None:
        super().__init__("No tranformers were specified")


class InvalidPackageError(Error):
    """Error signaling one or more package names are invalid."""

    def __init__(self, package_name: str) -> None:
        super().__init__(
            f"Package {package_name} is not valid. Are you missing any dependencies?"
        )
        self.package_name = package_name


@dataclasses.dataclass(frozen=True)
class Result:
    """Summary data of a craftier run command."""

    refactored: Sequence[pathlib.Path]
    unchanged: Sequence[pathlib.Path]
    success: bool
    error_count: int


def run(
    config: craftier_config.Config, files: Sequence[pathlib.Path]
) -> Result:
    """Execute craftier for the given set of files.

    Raises:
      EmptyTransformersError: when no transformers are selected.
      InvalidPackageError: when packages are missing or invalid.
    """
    try:
        transformers = _get_transformers(config)
    except class_finder.InvalidName as e:
        raise InvalidPackageError(e.package_name) from None
    if not transformers:
        raise EmptyTransformersError()
    logger.opt(lazy=True).debug(
        "Transformers: {}",
        lambda: ", ".join(_full_name(t) for t in transformers),
    )

    transform = codemod.BatchedCodemod(
        libcst.codemod.CodemodContext(), transformers
    )
    python_files = [str(p) for p in files]
    now = time.time()
    result = _exec_transform(transform, python_files)

    modified = fs.get_modified_files(files, since=now)

    if result.failures:
        errors = _LIBCST_SINK.getvalue()
        if errors:
            print("\n\nLibCST raw logs", file=sys.stderr)
            print("-" * 80, file=sys.stderr)
            print(errors, file=sys.stderr)
            print("-" * 80, file=sys.stderr)

    return Result(
        refactored=modified,
        unchanged=[p for p in files if p not in modified],
        success=result.failures == 0,
        error_count=result.failures,
    )


def _full_name(class_: Type[Any]) -> str:
    return f"{class_.__module__}.{class_.__qualname__}"


def _get_transformers(
    config: craftier_config.Config,
) -> Sequence[Type[codemod.ContextAwareTransformer]]:
    excluded = set(config.excluded)
    transformers = class_finder.from_qualified_names(
        codemod.ContextAwareTransformer, config.packages
    )
    return [t for t in transformers if _full_name(t) not in excluded]


def _is_profiling() -> bool:
    """Detect whether the code is being profiled.

    Note: It only detects whther the code is being profiled under cProfile.
    """
    return "_lsprof" in sys.modules


def _is_windows() -> bool:
    # See https://stackoverflow.com/a/7637706/1413687
    system = platform.system()
    return system == "Windows" or system.startswith("CYGWIN_NT")


def _sequential_exec_transform_with_prettyprint(
    transform: libcst.codemod.Codemod,
    python_files: Sequence[str],
    *,
    include_generated: bool = True,
) -> libcst.codemod.ParallelTransformResult:
    """Run a transform sequentially in the same process.

    This wrapper is similar in API to parallel_exec_transform_with_prettyprint
    and it is used when running the code on Windows or under a profiler.
    """
    for file in python_files:
        transform.context = dataclasses.replace(
            transform.context, filename=file
        )
        with open(file) as f:
            libcst.codemod.exec_transform_with_prettyprint(
                transform, f.read(), include_generated=include_generated
            )

    return libcst.codemod.ParallelTransformResult(
        successes=0, failures=0, skips=0, warnings=0
    )


def _exec_transform(
    transform: libcst.codemod.Codemod, files: Sequence[str]
) -> libcst.codemod.ParallelTransformResult:
    if _is_profiling() or _is_windows():
        return _sequential_exec_transform_with_prettyprint(
            transform, files, include_generated=True
        )

    chunksize = 4
    jobs = min(
        os.cpu_count() or 1,
        (len(files) + chunksize - 1) // chunksize,
    )
    with contextlib.redirect_stderr(_LIBCST_SINK):
        return libcst.codemod.parallel_exec_transform_with_prettyprint(
            transform,
            files,
            include_generated=True,
            show_successes=False,
            jobs=jobs,
        )
