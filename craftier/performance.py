"""
Module to keep track of performance statistics across multiple processes.

Note: because this uses a global state it will only work in forked
multi-process. Note that the default changed in Python 38 for MacOs.
"""

import dataclasses
import json
import multiprocessing
import tempfile
from typing import IO, Any, Dict, Mapping, Optional, Sequence


@dataclasses.dataclass
class _Config:
    file: Optional[IO[bytes]] = None


_config = _Config()


class PerformanceError(Exception):
    """Errors specific to the performance module."""


def enable() -> None:
    """Enable the performance sink."""
    if _config.file:
        raise PerformanceError("performance is already enabled")
    _config.file = tempfile.NamedTemporaryFile(
        prefix="craftier-stats-", buffering=0
    )


def write(data: Dict[str, Any]) -> None:
    """Write an entry to the performance file.

    Data must be a JSON serializable object.
    """
    if not _config.file:
        return
    with multiprocessing.Lock():
        _config.file.write(json.dumps(data).encode())
        _config.file.write(b"\n")


def read() -> Sequence[Mapping[str, Any]]:
    """Read the contents of the performance data."""
    if not _config.file:
        return []
    with multiprocessing.Lock():
        _config.file.seek(0)
        return [json.loads(line.strip().decode()) for line in _config.file]


def disable() -> None:
    """Disable the performance sink.

    Further writes and read will fail.
    """
    if not _config.file:
        raise PerformanceError("performance is not enabled")
    _config.file.close()
    _config.file = None
