import dataclasses
from typing import Sequence

from libcst.matchers import BaseMatcherNode


def matcher_deep_equals(first: object, second: object) -> bool:
    """Check whether two matchers are equivalent."""
    if isinstance(first, BaseMatcherNode) and isinstance(
        second, BaseMatcherNode
    ):
        return _deep_equals_matcher_node(first, second)

    if (
        isinstance(first, Sequence)
        and not isinstance(first, (str, bytes))
        and isinstance(second, Sequence)
        and not isinstance(second, (str, bytes))
    ):
        return _deep_equals_matcher_sequence(first, second)

    return first == second


def _deep_equals_matcher_sequence(
    first: Sequence[object], second: Sequence[object]
) -> bool:
    if first is second:  # short-circuit
        return True
    if len(first) != len(second):
        return False
    return all(
        matcher_deep_equals(first_el, second_el)
        for (first_el, second_el) in zip(first, second)
    )


def _deep_equals_matcher_node(
    first: BaseMatcherNode, second: BaseMatcherNode
) -> bool:
    if type(first) is not type(second):
        return False
    if first is second:  # short-circuit
        return True
    # Ignore metadata and other hidden fields
    for field in dataclasses.fields(first):
        first_value = getattr(first, field.name)
        second_value = getattr(second, field.name)
        if not matcher_deep_equals(first_value, second_value):
            return False
    return True
