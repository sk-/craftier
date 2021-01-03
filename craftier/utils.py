import dataclasses
from typing import Sequence

import libcst

_SKIP_TO_STRING = frozenset(
    (
        "lbrace",
        "rbrace",
        "lpar",
        "rpar",
        "comma",
        "semicolon",
        "header",
        "footer",
    )
)


def to_string(node: libcst.CSTNode) -> str:
    """Yaml-like representation of a node."""
    fields = [
        f
        for f in dataclasses.fields(node)
        if f.name not in _SKIP_TO_STRING
        and "whitespace" not in f.name
        and not f.name.startswith("_")
    ]

    if not fields:
        return f"{type(node).__name__}"

    lines = [f"{type(node).__name__}:"]
    for f in fields:
        key = f.name
        value = getattr(node, key)
        if value == []:
            value = ()
        if f.default != value:
            value_repr = _pretty_repr(value)
            if not value_repr.startswith("\n"):
                value_repr = f" {value_repr}"
            lines.append(_indent(f"{key}:{value_repr}"))
    return "\n".join(lines)


def _indent(value: str) -> str:
    return "\n".join(f"  {l}" for l in value.split("\n"))


def _pretty_repr(value: object) -> str:
    if isinstance(value, libcst.CSTNode):
        return to_string(value)

    if not isinstance(value, str) and isinstance(value, Sequence):
        return _pretty_repr_sequence(value)

    return repr(value)


def _pretty_repr_sequence(seq: Sequence[object]) -> str:
    if len(seq) == 0:
        return "[]"

    return "\n".join(["", *[f"- {_pretty_repr(el)}" for el in seq]])
