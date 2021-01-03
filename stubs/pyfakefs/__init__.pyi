import os
from typing import Any, Callable, Optional, Union

_PathLike = Union[str, bytes, "os.PathLike[Any]"]

class FakeFilesystem:
    def create_dir(
        self, directory_path: _PathLike, perm_bits: int = ...
    ) -> None: ...
    def create_file(
        self,
        file_path: _PathLike,
        st_mode: int = ...,
        contents: str = ...,
        st_size: Optional[int] = ...,
        create_missing_dirs: bool = ...,
        apply_umask: bool = ...,
        encoding: Optional[str] = ...,
        errors: Optional[str] = ...,
        side_effect: Optional[Callable[[Any], None]] = ...,
    ) -> None: ...
