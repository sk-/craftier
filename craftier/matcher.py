import ast
import dataclasses
from typing import Any, Callable, Dict, List, Sequence, Tuple, Union, cast

import libcst
import libcst.matchers

from craftier import libcst_typing

# TODO: have a custom extension of OneOf and MatchIfTrue, so that we can know
# which classes to match on.
#
# Could be something like:
#
# class MatchIfTrue extends libcst.matchers.MatchIfTrue:
#     __init__(self, expected_types, condition):
#         self.expected_types
#         def new_condition(node):
#             if not isinstance(node, expected_types):
#                 return false
#             return condition(node)
#         super()(new_condition)
#
# class OneOf extends libcst.matchers.OneOf:
#     property to extract all expected types to listen to

# TODO: add special matcher for qualified names: for example math.log should
# match log or renames as well.
# TODO: preserve leading_lines, this is required to preserve previous comments.
# Comments inside replaced code are going to be removed
# TODO: assign should match annassign


@dataclasses.dataclass
class _Placeholder:
    """Helper class used to keep track how many matchers are in use.

    When we are building a matcher from sorce code, we don't know how many times
    we have seen that placeholder. So in order to track that we wrap the
    matchers in this counter class.

    In that way we can give the instances of pattern x the names x/0, x/1, x/2
    and so forth. Then after a match is found we will check that indeed all
    instances of x/0, x/1, etc. are equivalent.
    """

    matcher: libcst_typing.Matcher
    total: int = 0


_SKIP_FIELDS = frozenset(
    (
        "lbrace",
        "rbrace",
        "lpar",
        "rpar",
        "comma",
        "semicolon",
        "header",
        "footer",
        "first_colon",
        "second_colon",
    )
)


def _skip_field(name: str) -> bool:
    if name in _SKIP_FIELDS:
        return True
    return "whitespace" in name or name.startswith("_")


def _repr_single(string: str) -> str:
    # See https://stackoverflow.com/questions/27402168/force-repr-to-use-single-quotes
    return "'" + repr('"' + string)[2:]


def _make_literal_value_matcher(
    node_value: str,
) -> libcst.matchers.MatchIfTrue[Callable[[str], bool]]:
    expected_value = ast.literal_eval(node_value)

    def comparator(value: str) -> bool:
        return cast(bool, ast.literal_eval(value) == expected_value)

    return libcst.matchers.MatchIfTrue(comparator)


def _make_simple_string_matcher(
    original_node: libcst.SimpleString,
) -> libcst.matchers.BaseMatcherNode:
    original_value = original_node.evaluated_value

    def concatenated_condition(node: libcst.CSTNode) -> bool:
        if not isinstance(node, libcst.ConcatenatedString):
            return False
        flattened_node = _flatten_concatenated_string(node)
        return (
            isinstance(flattened_node, libcst.SimpleString)
            and flattened_node.evaluated_value == original_value
        )

    concatenated_matcher = libcst.matchers.MatchIfTrue(concatenated_condition)
    return libcst.matchers.OneOf(
        libcst.matchers.SimpleString(
            value=_make_literal_value_matcher(original_node.value)
        ),
        concatenated_matcher,
    )


def _formatted_string_parts(
    node: libcst.FormattedString,
) -> Tuple[Sequence[str], Sequence[libcst.FormattedStringExpression]]:
    texts = []
    expressions = []
    prefix = node.start.replace("f", "").replace("F", "")
    for part in node.parts:
        if isinstance(part, libcst.FormattedStringText):
            texts.append(
                cast(str, ast.literal_eval(f"{prefix}{part.value}{node.end}"))
            )
        elif isinstance(part, libcst.FormattedStringExpression):
            expressions.append(part)
    return texts, expressions


def _make_formatted_string_matcher(
    original_node: libcst.FormattedString, placeholders: Dict[str, _Placeholder]
) -> libcst.matchers.BaseMatcherNode:
    original_texts, original_expressions = _formatted_string_parts(
        original_node
    )
    original_expressions_matchers = [
        _to_matcher(e, placeholders) for e in original_expressions
    ]

    def formatted_condition(node: libcst.CSTNode) -> bool:
        if isinstance(node, libcst.ConcatenatedString):
            node = _flatten_concatenated_string(node)

        if not isinstance(node, libcst.FormattedString):
            return False

        texts, expressions = _formatted_string_parts(node)
        if texts != original_texts or len(expressions) != len(
            original_expressions_matchers
        ):
            return False
        return all(
            matches(e, matcher)
            for e, matcher in zip(expressions, original_expressions_matchers)
        )

    # We need to wrap it with OneOf, otherwise it won't match
    return libcst.matchers.OneOf(
        libcst.matchers.MatchIfTrue(formatted_condition)
    )


def _flatten_concatenated_string(
    node: libcst.ConcatenatedString,
) -> Union[libcst.SimpleString, libcst.FormattedString]:
    classes = {type(node.left)}
    parts = []
    rest: Union[
        libcst.ConcatenatedString, libcst.SimpleString, libcst.FormattedString
    ] = node
    while isinstance(rest, libcst.ConcatenatedString):
        parts.append(rest.left)
        classes.add(type(rest.left))
        rest = rest.right
    parts.append(rest)
    classes.add(type(rest))
    # print(parts)

    if all(isinstance(n, libcst.SimpleString) for n in parts):
        # There's no idiom other than casting to tell mypy the list only has one
        # of the union elements. See https://github.com/python/mypy/issues/3497
        string_parts = cast(List[libcst.SimpleString], parts)
        content = "".join(n.evaluated_value for n in string_parts)
        return libcst.SimpleString(value=repr(content))

    formatted_parts: List[libcst.BaseFormattedStringContent] = []
    for part in parts:
        if isinstance(part, libcst.SimpleString):
            value = _repr_single(part.evaluated_value)[1:-1]
            if formatted_parts and isinstance(
                formatted_parts[-1], libcst.FormattedStringText
            ):
                formatted_parts[-1] = libcst.FormattedStringText(
                    value=formatted_parts[-1].value + value
                )
            else:
                formatted_parts.append(libcst.FormattedStringText(value=value))
        else:
            for nested_part in part.parts:
                prefix = part.start.replace("f", "").replace("F", "")
                if isinstance(nested_part, libcst.FormattedStringText):
                    value = _repr_single(
                        ast.literal_eval(
                            f"{prefix}{nested_part.value}{part.end}"
                        )
                    )[1:-1]
                    if formatted_parts and isinstance(
                        formatted_parts[-1], libcst.FormattedStringText
                    ):
                        formatted_parts[-1] = libcst.FormattedStringText(
                            value=formatted_parts[-1].value + value
                        )
                    else:
                        formatted_parts.append(
                            libcst.FormattedStringText(value=value)
                        )
                else:
                    formatted_parts.append(nested_part)
    return libcst.FormattedString(parts=formatted_parts, start="f'", end="'")


def _to_matcher(
    node: libcst.CSTNode, placeholders: Dict[str, _Placeholder]
) -> libcst_typing.Matcher:
    if isinstance(node, libcst.Name) and node.value in placeholders:
        placeholder = placeholders[node.value]
        placeholder.total += 1
        return libcst.matchers.SaveMatchedNode(
            placeholder.matcher, f"{node.value}/{placeholder.total}"
        )

    if isinstance(node, (libcst.Integer, libcst.Float, libcst.Imaginary)):
        return cast(
            libcst.matchers.BaseMatcherNode,
            getattr(libcst.matchers, node.__class__.__name__)(
                value=_make_literal_value_matcher(node.value)
            ),
        )

    if isinstance(node, libcst.ConcatenatedString):
        node = _flatten_concatenated_string(node)

    if isinstance(node, libcst.SimpleString):
        return _make_simple_string_matcher(node)

    if isinstance(node, libcst.FormattedString):
        return _make_formatted_string_matcher(node, placeholders)

    fields = [f for f in dataclasses.fields(node) if not _skip_field(f.name)]

    data: Dict[str, Any] = {}
    matcher: Any
    for f in fields:
        key = f.name
        value = getattr(node, key)
        # print(key, value, type(value))
        # if value == []:
        #    value = ()
        # if f.default != value:
        #    lines.append(_indent(f"{key}: {_pretty_repr(value)}"))
        if isinstance(value, libcst.CSTNode):
            matcher = _to_matcher(value, placeholders)
        elif not isinstance(value, str) and isinstance(value, Sequence):
            if value and isinstance(value[0], libcst.CSTNode):
                matcher = [_to_matcher(n, placeholders) for n in value]
            else:
                matcher = value
        elif value == libcst.MaybeSentinel.DEFAULT:
            matcher = libcst.matchers.DoNotCare()
        else:
            matcher = value
        # if key == 'operator':
        #    print(matcher, type(matcher))
        data[key] = matcher
    # print('matcher class', getattr(m, node.__class__.__name__))
    return cast(
        libcst.matchers.BaseMatcherNode,
        getattr(libcst.matchers, node.__class__.__name__)(**data),
    )


def from_node(
    node: libcst.CSTNode, placeholders: Dict[str, libcst_typing.Matcher]
) -> libcst_typing.Matcher:
    """Return a matcher that matches the given node.

    The matcher will be semantic, meaning that equivalent nodes will be matched.
    For example: literal nodes are compared by value and strings are simplified.

    The placeholders mapping specifies how to match certain names. For example
    if you pass {'x': DoNotCare()}, then the node `x + 1`, will match any
    expression that's being added to 1.

    Args:
      node: the node to generate a matcher for
      placeholders: mapping of node name to matcher
    """
    wrapped_placeholders = {
        p: _Placeholder(matcher) for p, matcher in placeholders.items()
    }
    # TODO: return a compound matcher that checks that multiple instances of the
    # same placeholder matches.
    # Cool thing is that if there's no repeated placeholer, we will incur no
    # extra cost while checking.
    # This will be an AllOf matcher. We just need to make sure that we return
    # the right matcher type.
    return _to_matcher(node, wrapped_placeholders)


def matches(node: libcst.CSTNode, matcher: libcst_typing.Matcher) -> bool:
    """Return True if the node matches the shape defined by the matcher.

    This is a replacement for libcst.matchers.matches accepting a
    DoNotCareSentinel.
    """
    if isinstance(matcher, libcst.matchers.DoNotCareSentinel):
        return True
    return libcst.matchers.matches(node, matcher)
