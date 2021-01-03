import pathlib
from typing import Iterable, Sequence


def get_modified_files(
    files: Iterable[pathlib.Path], *, since: float
) -> Sequence[pathlib.Path]:
    """Return the files that were modified since the given timestamp."""
    return [f for f in files if f.stat().st_mtime > since]
