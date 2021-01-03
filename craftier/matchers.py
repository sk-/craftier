import ast
from typing import Any, Callable, cast

import libcst.matchers
from typing_extensions import Annotated

_BUILTINS = frozenset(
    (
        "abs",
        "all",
        "any",
        "ascii",
        "bin",
        "bool",
        "breakpoint",
        "bytearray",
        "bytes",
        "callable",
        "chr",
        "classmethod",
        "compile",
        "complex",
        "copyright",
        "credits",
        "delattr",
        "dict",
        "dir",
        "divmod",
        "enumerate",
        "eval",
        "exec",
        "exit",
        "filter",
        "float",
        "format",
        "frozenset",
        "getattr",
        "globals",
        "hasattr",
        "hash",
        "help",
        "hex",
        "id",
        "input",
        "int",
        "isinstance",
        "issubclass",
        "iter",
        "len",
        "license",
        "list",
        "locals",
        "map",
        "max",
        "memoryview",
        "min",
        "next",
        "object",
        "oct",
        "open",
        "ord",
        "pow",
        "print",
        "property",
        "quit",
        "range",
        "repr",
        "reversed",
        "round",
        "set",
        "setattr",
        "slice",
        "sorted",
        "staticmethod",
        "str",
        "sum",
        "super",
        "tuple",
        "type",
        "vars",
        "zip",
    )
)


def _is_builtin(value: str) -> bool:
    return value in _BUILTINS


_BOOLEAN_VALUES = frozenset(("True", "False"))


def _is_boolean(value: str) -> bool:
    return value in _BOOLEAN_VALUES


Builtin = Annotated[
    Any, libcst.matchers.Name(value=libcst.matchers.MatchIfTrue(_is_builtin))
]
StringLiteral = Annotated[str, libcst.matchers.SimpleString()]
IntegerLiteral = Annotated[int, libcst.matchers.Integer()]
FloatLiteral = Annotated[float, libcst.matchers.Float()]
BooleanLiteral = Annotated[
    bool, libcst.matchers.Name(value=libcst.matchers.MatchIfTrue(_is_boolean))
]
NoneLiteral = Annotated[None, libcst.matchers.Name(value="None")]

# TODO: export and test these matchers
def _match_if_equal(
    node_value: str,
) -> libcst.matchers.MatchIfTrue[Callable[[str], bool]]:
    expected_value = ast.literal_eval(node_value)

    def comparator(value: str) -> bool:
        return cast(bool, ast.literal_eval(value) == expected_value)

    return libcst.matchers.MatchIfTrue(comparator)


def _match_if_distinct(
    node_value: str,
) -> libcst.matchers.MatchIfTrue[Callable[[str], bool]]:
    expected_value = ast.literal_eval(node_value)

    def comparator(value: str) -> bool:
        return cast(bool, ast.literal_eval(value) != expected_value)

    return libcst.matchers.MatchIfTrue(comparator)


Falsey = Annotated[
    Any,
    libcst.matchers.OneOf(
        libcst.matchers.Name(value="False"),
        libcst.matchers.Integer(value=_match_if_equal("0")),
        libcst.matchers.Float(value=_match_if_equal("0.0")),
        libcst.matchers.SimpleString(value=_match_if_equal("''")),
        # TODO: get matchers for [], (,), {}, check what happens with bytes
    ),
]

Truthy = Annotated[
    Any,
    libcst.matchers.OneOf(
        libcst.matchers.Name(value="False"),
        libcst.matchers.Integer(value=_match_if_distinct("0")),
        libcst.matchers.Float(value=_match_if_distinct("0.0")),
        libcst.matchers.SimpleString(value=_match_if_distinct('""')),
    ),
]

# TODO: add literals for set, dict, tuple and list
# They will require to be itself Literal

# TODO: add HasCodeMatcher and DoesNotHaveCodeMatcher
