from typing import Any, Callable, Optional, Sequence, TypeVar

TestFunc = Callable[[Callable[..., Any], int, Sequence[Any]], str]

_F = TypeVar("_F", bound=Callable[..., Any])

class parameterized:
    @classmethod
    def expand(
        cls,
        input: Sequence[Sequence[Any]],
        name_func: Optional[TestFunc] = ...,
        doc_func: Optional[TestFunc] = ...,
        skip_on_empty: bool = ...,
    ) -> Callable[[_F], _F]: ...
