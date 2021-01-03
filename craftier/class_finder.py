import importlib
import inspect
import pkgutil
import types
from typing import Any, Iterator, Sequence, Set, Type, TypeVar


class InvalidName(Exception):
    """Exception raised when a package or module cannot be imported."""

    def __init__(self, package_name: str):
        super().__init__(f"{package_name} was not found")
        self.package_name = package_name


T = TypeVar("T", bound=Type[Any])


def from_qualified_names(
    base_class: T, qualified_names: Sequence[str]
) -> Sequence[T]:
    """Find all the subclasses from the target class in the given packages."""
    classes: Set[T] = set()
    for name in qualified_names:
        classes.update(_from_package_name(base_class, name))
    return sorted(classes, key=lambda class_: class_.__name__)


def _from_package_name(base_class: T, qualified_name: str) -> Iterator[T]:
    try:
        package = importlib.import_module(qualified_name)
    except ModuleNotFoundError:
        raise InvalidName(qualified_name) from None

    yield from _from_module(base_class, package)

    # Typeshed is missing __path__ for ModuleType. See
    # https://github.com/python/typeshed/issues/4812
    package_path = getattr(package, "__path__", None)
    if not package_path:
        return
    for module_info in pkgutil.iter_modules(
        package_path, prefix=f"{qualified_name}."
    ):
        try:
            submodule = importlib.import_module(module_info.name)
        except ModuleNotFoundError:
            continue
        yield from _from_module(base_class, submodule)


def _from_module(base_class: T, module: types.ModuleType) -> Iterator[T]:
    for _, class_ in inspect.getmembers(module, inspect.isclass):
        if issubclass(class_, base_class):
            yield class_
