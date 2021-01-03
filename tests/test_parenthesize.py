import itertools
import unittest

import libcst
import parameterized

from craftier import parenthesize

EXAMPLES = (
    [
        libcst.ensure_type(
            libcst.parse_statement(
                "if a := 1:\n  pass",
                config=libcst.PartialParserConfig(python_version="3.8"),
            ),
            libcst.If,
        ).test,
    ],
    [
        libcst.parse_expression("lambda x: x + 1"),
    ],
    [
        libcst.parse_expression("x if x else y"),
    ],
    [
        libcst.parse_expression("x or y"),
    ],
    [
        libcst.parse_expression("x and y"),
    ],
    [
        libcst.parse_expression("not x"),
    ],
    [
        libcst.parse_expression("x in y"),
        libcst.parse_expression("x not in y"),
        libcst.parse_expression("x is y"),
        libcst.parse_expression("x is not y"),
        libcst.parse_expression("x < y"),
        libcst.parse_expression("x <= y"),
        libcst.parse_expression("x > y"),
        libcst.parse_expression("x >= y"),
        libcst.parse_expression("x != y"),
        libcst.parse_expression("x == y"),
    ],
    [
        libcst.parse_expression("x | y"),
        libcst.parse_expression("x ^ y"),
        libcst.parse_expression("x & y"),
    ],
    [
        libcst.parse_expression("x << y"),
        libcst.parse_expression("x >> y"),
    ],
    [
        libcst.parse_expression("x + y"),
        libcst.parse_expression("x - y"),
    ],
    [
        libcst.parse_expression("x * y"),
        libcst.parse_expression("x @ y"),
        libcst.parse_expression("x / y"),
        libcst.parse_expression("x // y"),
        libcst.parse_expression("x % y"),
    ],
    [
        libcst.parse_expression("+x"),
        libcst.parse_expression("-x"),
        libcst.parse_expression("~x"),
    ],
    [
        libcst.parse_expression("x ** y"),
    ],
    [
        libcst.parse_expression("await x"),
    ],
    [
        libcst.parse_expression("x[a]"),
        libcst.parse_expression("x[a:b]"),
        libcst.parse_expression("x[a:b:c]"),
        libcst.parse_expression("x(a, b, c)"),
        libcst.parse_expression("x.a"),
    ],
    [
        libcst.parse_expression("(x, y)"),
        libcst.parse_expression("[x, y]"),
        libcst.parse_expression("[x for x in y]"),
        libcst.parse_expression("{x: 1 for x in y}"),
        libcst.parse_expression("{x, y}"),
        libcst.parse_expression("{x for x in y}"),
    ],
)

SAME_PRECEDENCE = list(
    itertools.chain.from_iterable(
        [itertools.product(exps, repeat=2) for exps in EXAMPLES]
    )
)

LOWER_PRECEDENCE = list(
    itertools.chain.from_iterable(
        [
            itertools.product(exps, exps_lower)
            for exps, exps_lower in zip(EXAMPLES[1:], EXAMPLES)
        ]
    )
)

HIGHER_PRECEDENCE = list(
    itertools.chain.from_iterable(
        [
            itertools.product(exps, exps_higher)
            for exps, exps_higher in zip(EXAMPLES, EXAMPLES[1:])
        ]
    )
)


class ParenthesizeTestCase(unittest.TestCase):
    """Mixin for adding parentheses check assertions."""

    def assert_has_parentheses(self, node: libcst.CSTNode) -> None:
        """Check the node is properly parenthesized."""
        if not getattr(node, "lpar"):
            self.fail(f"Node {type(node).__name__} is not parenthesized")


class ParenthesizeUsingParentTest(ParenthesizeTestCase):
    def test_expression_already_parenthesized(self) -> None:
        node = libcst.parse_expression("(a + b)")
        new_node = parenthesize.parenthesize_using_parent(
            node, libcst.parse_expression("a * (a + b)")
        )
        self.assertIs(new_node, node)

    def test_not_parenthesizable(self) -> None:
        node = libcst.parse_statement("return foo")
        new_node = parenthesize.parenthesize_using_parent(
            node, libcst.parse_expression("a * (a + b)")
        )
        self.assertIs(new_node, node)

    def test_tuple_requires_paren(self) -> None:
        node = libcst.parse_expression("1, 2, 3")
        new_node = parenthesize.parenthesize_using_parent(
            node, libcst.Call(func=libcst.Name("func"))
        )
        self.assert_has_parentheses(new_node)

    def test_tuple_return(self) -> None:
        node = libcst.parse_expression("1, 2, 3")
        new_node = parenthesize.parenthesize_using_parent(node, libcst.Return())
        self.assertIs(new_node, node)

    def test_generator_only_argument_function_call(self) -> None:
        node = libcst.parse_expression("(x for x in foo)").with_changes(
            lpar=[], rpar=[]
        )
        new_node = parenthesize.parenthesize_using_parent(
            node, libcst.parse_expression("max(x for x in foo)")
        )
        self.assertIs(new_node, node)

    def test_generator_many_argument_function_call(self) -> None:
        node = libcst.parse_expression("(x for x in foo)").with_changes(
            lpar=[], rpar=[]
        )
        new_node = parenthesize.parenthesize_using_parent(
            node, libcst.parse_expression("max((x for x in foo), foo)")
        )
        self.assert_has_parentheses(new_node)

    def test_generator_return(self) -> None:
        node = libcst.parse_expression("(x for x in foo)").with_changes(
            lpar=[], rpar=[]
        )
        new_node = parenthesize.parenthesize_using_parent(
            node, libcst.parse_statement("return (x for x in foo)")
        )
        self.assert_has_parentheses(new_node)

    @parameterized.parameterized.expand(HIGHER_PRECEDENCE)
    def test_expression_higher_precedence(
        self, node: libcst.CSTNode, parent: libcst.CSTNode
    ) -> None:
        new_node = parenthesize.parenthesize_using_parent(node, parent)
        self.assert_has_parentheses(new_node)

    @parameterized.parameterized.expand(LOWER_PRECEDENCE)
    def test_expression_lower_precedence(
        self, node: libcst.CSTNode, parent: libcst.CSTNode
    ) -> None:
        new_node = parenthesize.parenthesize_using_parent(node, parent)
        self.assertIs(new_node, node)

    @parameterized.parameterized.expand(LOWER_PRECEDENCE)
    def test_expression_same_precedence(
        self, node: libcst.CSTNode, parent: libcst.CSTNode
    ) -> None:
        new_node = parenthesize.parenthesize_using_parent(node, parent)
        self.assertIs(new_node, node)


class ParenthesizeUsingPreviousTest(ParenthesizeTestCase):
    def test_expression_previous_parenthesized(self) -> None:
        node = libcst.parse_expression("a + b")
        new_node = parenthesize.parenthesize_using_previous(
            node, libcst.parse_expression("(a + b)")
        )
        self.assert_has_parentheses(new_node)

    def test_expression_already_parenthesized(self) -> None:
        node = libcst.parse_expression("(a + b)")
        new_node = parenthesize.parenthesize_using_previous(
            node, libcst.parse_expression("a * (a + b)")
        )
        self.assertIs(new_node, node)

    def test_not_parenthesizable(self) -> None:
        node = libcst.parse_statement("return foo")
        new_node = parenthesize.parenthesize_using_previous(
            node, libcst.parse_expression("a * (a + b)")
        )
        self.assertIs(new_node, node)

    def test_tuple_requires_paren(self) -> None:
        node = libcst.parse_expression("1, 2, 3")
        new_node = parenthesize.parenthesize_using_previous(
            node, libcst.Call(func=libcst.Name("func"))
        )
        self.assert_has_parentheses(new_node)

    def test_tuple_return(self) -> None:
        node = libcst.parse_expression("1, 2, 3")
        new_node = parenthesize.parenthesize_using_previous(
            node, libcst.Return()
        )
        self.assert_has_parentheses(new_node)

    def test_generator_only_argument_function_call(self) -> None:
        node = libcst.parse_expression("(x for x in foo)").with_changes(
            lpar=[], rpar=[]
        )
        new_node = parenthesize.parenthesize_using_previous(
            node, libcst.parse_expression("max(x for x in foo)")
        )
        self.assert_has_parentheses(new_node)

    def test_generator_many_argument_function_call(self) -> None:
        node = libcst.parse_expression("(x for x in foo)").with_changes(
            lpar=[], rpar=[]
        )
        new_node = parenthesize.parenthesize_using_previous(
            node, libcst.parse_expression("max((x for x in foo), foo)")
        )
        self.assert_has_parentheses(new_node)

    def test_generator_return(self) -> None:
        node = libcst.parse_expression("(x for x in foo)").with_changes(
            lpar=[], rpar=[]
        )
        new_node = parenthesize.parenthesize_using_previous(
            node, libcst.parse_statement("return (x for x in foo)")
        )
        self.assert_has_parentheses(new_node)

    @parameterized.parameterized.expand(HIGHER_PRECEDENCE)
    def test_expression_higher_precedence(
        self, node: libcst.CSTNode, parent: libcst.CSTNode
    ) -> None:
        new_node = parenthesize.parenthesize_using_previous(node, parent)
        self.assert_has_parentheses(new_node)

    @parameterized.parameterized.expand(LOWER_PRECEDENCE)
    def test_expression_lower_precedence(
        self, node: libcst.CSTNode, parent: libcst.CSTNode
    ) -> None:
        new_node = parenthesize.parenthesize_using_previous(node, parent)
        self.assertIs(new_node, node)

    @parameterized.parameterized.expand(LOWER_PRECEDENCE)
    def test_expression_same_precedence(
        self, node: libcst.CSTNode, parent: libcst.CSTNode
    ) -> None:
        new_node = parenthesize.parenthesize_using_previous(node, parent)
        self.assertIs(new_node, node)
