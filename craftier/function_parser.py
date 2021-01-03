import inspect
import textwrap
from typing import Any, Callable, Dict, Sequence

import libcst
import libcst.matchers
import typing_extensions
from typing_extensions import Annotated

from craftier import libcst_typing


def args_to_matchers(
    function: Callable[..., Any],
) -> Dict[str, libcst_typing.Matcher]:
    """Extract node matchers from the function arguments.

    Untyped arguments will get a `DoNotCare` matcher, while arguments typed and
    annoated with a `BaseMatcherNode` will return that matcher.
    """
    matchers: Dict[str, libcst_typing.Matcher] = {}

    # Create default matchers for all arguments
    args = function.__code__.co_varnames[: function.__code__.co_argcount]
    if args:
        for name in args:
            if name == "self":
                continue
            matchers[name] = libcst.matchers.DoNotCare()

    # Check if any of the arguments was annotated with a Matcher
    for name, type_declaration in typing_extensions.get_type_hints(
        function, include_extras=True
    ).items():
        if typing_extensions.get_origin(type_declaration) is Annotated:
            # Check if there is a matcher
            arg = typing_extensions.get_args(type_declaration)[1]
            if isinstance(arg, libcst.matchers.BaseMatcherNode):
                matchers[name] = arg

    return matchers


class UnusedArgument(Exception):
    """Exception raised when an argument is unused.

    Attributes:
      name: the name of the unused argument.
      function_name: the name of the function where the argument is defined.
    """

    name: str
    function_name: str

    def __init__(self, name: str, fn_name: str, lineno: int) -> None:
        super().__init__(
            f'Unused argument "{name}" in function {fn_name}:{lineno}'
        )
        self.name = name
        self.fn_name = fn_name
        self.lineno = lineno


def _remove_expression(node: libcst.CSTNode) -> libcst.CSTNode:
    if isinstance(node, libcst.Expr):
        return node.value
    return node


def _from_body(body: Sequence[libcst.CSTNode]) -> Sequence[libcst.CSTNode]:
    if len(body) == 1:
        stmt = body[0]
        if isinstance(
            stmt, (libcst.SimpleStatementLine, libcst.SimpleStatementSuite)
        ):
            if len(stmt.body) == 1:
                return [_remove_expression(stmt.body[0])]
        if isinstance(stmt, libcst.Expr):
            return [_remove_expression(stmt)]
    return body


def _from_function_source(
    source: str, function: Callable[..., Any]
) -> Sequence[libcst.CSTNode]:
    source = textwrap.dedent(source)
    tree = libcst.parse_statement(source)
    function_node = libcst.ensure_type(tree, libcst.FunctionDef)
    body = function_node.body.body
    if function_node.get_docstring():
        body = body[1:]

    args = function.__code__.co_varnames[: function.__code__.co_argcount]
    if args:
        for name in args:
            if name == "self":
                continue
            if not libcst.matchers.findall(
                function_node.body, libcst.matchers.Name(value=name)
            ):
                raise UnusedArgument(
                    name, function.__name__, function.__code__.co_firstlineno
                )

    return _from_body(body)


def parse(function: Callable[..., Any]) -> Sequence[libcst.CSTNode]:
    """Extract a `CSTNode` from a function's source code."""
    return _from_function_source(inspect.getsource(function), function)
