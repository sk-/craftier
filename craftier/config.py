import configparser
import dataclasses
import pathlib
from typing import List, Optional, Sequence, Tuple

# The maximum number of directories to be searched for the config file
_MAX_SEARCH_DEPTH: int = 25
_STOP_SEARCH_ON_DIRS: Tuple[str, ...] = (".git", ".hg")
CONFIG_FILENAME = ".craftier.ini"


class InvalidConfigError(Exception):
    """Error raised when the configuration file is invalid."""


@dataclasses.dataclass
class Config:
    """Craftier's config data.

    It will be typically read from a config file, a .craftier.ini file.
    """

    path: Optional[pathlib.Path]
    packages: Sequence[str] = ("craftier.refactors",)
    excluded: Sequence[str] = ()


def find_path(
    start_path: pathlib.Path = pathlib.Path("."),
) -> Optional[pathlib.Path]:
    """Traverse the file system looking for the config file .craftier.ini.

    It will stop earlier at the user's home directory, if it encounters a Git or
    Mercurial directory, or if it traversed too deep.
    """
    home = pathlib.Path.home()
    path = start_path.resolve()
    for path in [path, *path.parents][:_MAX_SEARCH_DEPTH]:
        config_file = path / CONFIG_FILENAME
        if config_file.is_file():
            return config_file

        for stop_dir in _STOP_SEARCH_ON_DIRS:
            if (path / stop_dir).is_dir():
                return None

        if path == home:
            return None

    return None


def load(path: Optional[pathlib.Path]) -> Config:
    """Load craftier's config.

    It will use the given path or try to detects the config otherwise.
    """
    if not path:
        path = find_path()

    if not path:
        return Config(path=None)

    config = configparser.ConfigParser()
    try:
        config.read(path)
    except configparser.Error as e:
        raise InvalidConfigError(f"{path} is not a valid config file") from e
    try:
        craftier_config = config["craftier"]
    except KeyError as e:
        raise InvalidConfigError("missing [craftier] section") from e

    return Config(
        path=path,
        packages=_parse_list(craftier_config.get("packages", "")),
        excluded=_parse_list(craftier_config.get("excluded", "")),
    )


def _parse_list(value: str) -> List[str]:
    return [part.strip() for part in value.split(",") if part.strip()]
