import dataclasses
import itertools
import time
import types
from typing import Any, Callable, Dict, Optional, cast

import libcst
import libcst.codemod
import libcst.matchers
import libcst.metadata
from loguru import logger

import craftier.matcher
from craftier import codemod, function_parser, parenthesize, performance


@dataclasses.dataclass
class ExpressionTransform:
    """Represent all the aspects of a code transform."""

    before: libcst.matchers.BaseMatcherNode
    after: libcst.CSTNode
    wrapper: libcst.metadata.MetadataWrapper

    def visitor_method_name(self) -> str:
        """Return the name of the vistior method that could match the matcher.

        For example if the before matcher was a `x + 2`, then the name returned
        would be `leave_BinaryOperation`.
        """
        node_type = type(self.before).__name__
        return f"leave_{node_type}"


def _get_expression_transform(
    before: Callable[..., Any], after: Callable[..., Any]
) -> ExpressionTransform:
    expression = function_parser.parse(before)[0]
    matchers = function_parser.args_to_matchers(before)
    matcher = craftier.matcher.from_node(expression, matchers)
    inner_matcher = getattr(matcher, "matcher", None)
    if isinstance(matcher, libcst.matchers.DoNotCareSentinel) or isinstance(
        inner_matcher, libcst.matchers.DoNotCareSentinel
    ):
        raise Exception(
            f"DoNotCare matcher is forbidden at top level in `{before.__name__}`"
        )

    after_expression = function_parser.parse(after)[0]
    # Technically this is not correct as some expressions,like function calls,
    # binary operations, name, etc, are wrapped in an `Expr` node.
    module = libcst.Module(
        body=[
            libcst.SimpleStatementLine(
                body=[cast(libcst.BaseSmallStatement, after_expression)]
            )
        ]
    )
    wrapper = libcst.metadata.MetadataWrapper(module)
    body = cast(libcst.SimpleStatementLine, wrapper.module.body[0])
    replacement = body.body[0]

    return ExpressionTransform(
        before=matcher, after=replacement, wrapper=wrapper
    )


def check_matches(
    matches: Dict[str, libcst.CSTNode]
) -> Optional[Dict[str, libcst.CSTNode]]:
    """Check all the placeholders matches are sound between them.

    When using placeholders in a node matcher, those are replaced by a special
    name of the form <name>/<occurrence>. They can match any nodes, but at the
    end we need to make sure matches for placeholders with the same name are
    equivalent.

    TODO: instead of calling this method directly, we should incorporate it
    directly into the returned global matcher.
    """
    result = {}
    for key, grouped_matches in itertools.groupby(
        sorted(matches.items()), lambda x: x[0].split("/", 1)[0]
    ):
        first_match, *remaining_matches = grouped_matches
        result[key] = first_match[1]
        if not remaining_matches:
            continue
        matcher = craftier.matcher.from_node(first_match[1], {})
        if not all(
            craftier.matcher.matches(match[1], matcher)
            for match in remaining_matches
        ):
            return None
    return result


class _ReplaceTransformer(libcst.CSTTransformer):
    METADATA_DEPENDENCIES = (libcst.metadata.ParentNodeProvider,)

    def __init__(self, replacements: Dict[str, libcst.CSTNode]) -> None:
        super().__init__()
        self.replacements = replacements

    def leave_Name(
        self, original_node: libcst.Name, updated_node: libcst.Name
    ) -> libcst.BaseExpression:
        new_node = self.replacements.get(updated_node.value)
        if not new_node:
            return updated_node
        parent = self.get_metadata(
            libcst.metadata.ParentNodeProvider, original_node
        )
        if not parent:
            raise Exception("cannot find parent for node")
        # TODO: check if we need to clone the node before returning it. It may
        # have some implications for the MetadataWrapper, as we are forcing to
        # not copy the tree.
        return parenthesize.parenthesize_using_parent(
            cast(libcst.BaseExpression, new_node), parent
        )


def _replace_names(
    node: libcst.CSTNode,
    wrapper: libcst.metadata.MetadataWrapper,
    replacements: Dict[str, libcst.CSTNode],
) -> libcst.CSTNode:
    replacer = _ReplaceTransformer(replacements)
    with replacer.resolve(wrapper):
        # The result of node.visit can never be a RemovalSentinel.
        return cast(libcst.CSTNode, node.visit(replacer))


class CraftierTransformer(codemod.ContextAwareTransformer):
    """Base class for all Craftier based transformers.

    This will correctly generate the appropiate leave methods based on the code
    inside the methods `{check}_before` and `{check}_after`. Note that you must
    specify a pair of such methods.

    For example, if you wanted to replace `None` equality checks with `is`
    checks, you could write something like::

        class NoneEqualityTransformer(CraftierTransformer):
            def equality_before(self, x):
                x == None

            def equality_after(self, x):
                x is None

    The methods `_before` and `_after` need to specify as arguments the
    parametric replacements and will match anything by default. If you want to
    restrict what a given parameter can match, you can use a type annotation as
    follows::

        x: Annotated[Any, matcher]

    where `matcher` is any instance of a valid `libcst.matcher`.

    There are also some predefined types aliases in `craftier.matchers`, for
    example `BooleanLiteral`, which would only match nodes `True` and `False`.

    At the moment, the actual type annoation (first argument of `Annotated`) is
    not used at all, but in the future we plan to leverage `libcst`'s typing
    metadata.
    """

    def __init__(self, context: libcst.codemod.CodemodContext):
        super().__init__(context)
        method_names = set()
        for name in type(self).__dict__:
            if name.endswith("_before") or name.endswith("_after"):
                method_names.add(name.rsplit("_", 1)[0])
        if len(method_names) != 1:
            raise Exception(
                f"Only 1 method is supported at the moment. Found: {method_names}"
            )
        # TODO: handle more method definitions
        name = list(method_names)[0]
        before = getattr(self, f"{name}_before", None)
        after = getattr(self, f"{name}_after", None)
        if not before or not after:
            raise Exception(
                f"Expected `{name}_before` and `{name}_after` to be defined"
            )
        transform = _get_expression_transform(before, after)

        perf_name = f"{self.__class__.__name__}/{name}"
        # pylint: disable=unused-argument
        def custom_on_leave(
            self: CraftierTransformer,
            original_node: libcst.CSTNode,
            updated_node: libcst.CSTNode,
        ) -> libcst.CSTNode:
            new_node = updated_node
            status = "unchanged"
            start = time.perf_counter_ns()
            # We don't support wildcard patterns yet, so we can safely cast the
            # results to single nodes.
            matches = cast(
                Dict[str, libcst.CSTNode],
                libcst.matchers.extract(updated_node, transform.before),
            )
            if matches is not None:
                actual_matches = check_matches(matches)
                if actual_matches is not None:
                    # TODO: make sure all new nodes have a different id
                    new_node = _replace_names(
                        transform.after, transform.wrapper, actual_matches
                    )
                    logger.debug(
                        "{} changed file {}",
                        perf_name,
                        self.context.filename,
                    )
                    new_node = parenthesize.parenthesize_using_previous(
                        new_node, updated_node
                    )
                    status = "modified"
                    self._mark_as_modified()
            end = time.perf_counter_ns()
            performance.write(
                {
                    "name": perf_name,
                    "time": (end - start) / 1e6,
                    "status": status,
                }
            )
            return new_node

        # pylint: enable=unused-argument

        custom_on_leave.__name__ = transform.visitor_method_name()
        bound_leave = types.MethodType(custom_on_leave, self)
        setattr(self, transform.visitor_method_name(), bound_leave)

    def _mark_as_modified(self) -> None:
        context = self.context.scratch.setdefault(codemod.CONTEXT_KEY, {})
        context[self.context.filename] = True
