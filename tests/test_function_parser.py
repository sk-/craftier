import unittest
from typing import Any

import libcst
import libcst.matchers
from typing_extensions import Annotated

from craftier import function_parser, utils
from tests import helpers

LiteralInt = Annotated[Any, libcst.matchers.Integer()]


class FunctionParserTest(unittest.TestCase):
    def assert_node_equal(
        self, first: libcst.CSTNode, second: libcst.CSTNode
    ) -> None:
        """Check that two libcst nodes are equal."""
        if not first.deep_equals(second):
            self.fail(
                f"Nodes are not equal\nGot: {utils.to_string(first)}\nExpected: {utils.to_string(second)}"
            )

    def test_args_to_matchers(self) -> None:
        # pylint: disable=invalid-name,unused-argument
        def test_function(
            self,
            a,
            b: int,
            c: Annotated[int, "< 1"],
            d: Annotated[Any, libcst.matchers.Integer(value="3")],
            e: LiteralInt,
        ):
            pass

        # pylint: enable=invalid-name,unused-argument

        matchers = function_parser.args_to_matchers(test_function)
        expected = {
            "a": libcst.matchers.DoNotCare(),
            "b": libcst.matchers.DoNotCare(),
            "c": libcst.matchers.DoNotCare(),
            "d": libcst.matchers.Integer(value="3"),
            "e": libcst.matchers.Integer(),
        }
        for k in expected:
            self.assertTrue(
                helpers.matcher_deep_equals(matchers[k], expected[k]),
                f"Matcher '{k}' is not equal",
            )

    def test_empty_args_to_matchers(self) -> None:
        def test_function():
            pass

        matchers = function_parser.args_to_matchers(test_function)
        self.assertEqual(matchers, {})

    def test_parse_with_docstring(self) -> None:
        # pylint: disable=pointless-statement
        def test_function():
            """docstring"""
            1

        # pylint: disable=pointless-statement
        self.assert_node_equal(
            function_parser.parse(test_function)[0], libcst.Integer("1")
        )

    def test_parse_without_docstring(self) -> None:
        # pylint: disable=pointless-statement
        def test_function():
            1

        # pylint: enable=pointless-statement
        self.assert_node_equal(
            function_parser.parse(test_function)[0], libcst.Integer("1")
        )

    def test_parse_with_args(self) -> None:
        # pylint: disable=pointless-statement
        def test_function(x):
            x

        # pylint: enable=pointless-statement
        self.assert_node_equal(
            function_parser.parse(test_function)[0], libcst.Name("x")
        )

    def test_parse_single_line(self) -> None:
        # pylint: disable=pointless-statement
        def test_function(x):
            x

        # pylint: enable=pointless-statement
        self.assert_node_equal(
            function_parser.parse(test_function)[0], libcst.Name("x")
        )

    def test_parse_semicolon(self) -> None:
        # fmt: off
        # pylint: disable=pointless-statement,unnecessary-semicolon
        def test_function(x):
            x;
        # fmt: on
        # pylint: enable=pointless-statement,unnecessary-semicolon
        self.assert_node_equal(
            function_parser.parse(test_function)[0], libcst.Name("x")
        )

    def test_parse_multiple_statements(self) -> None:
        # pylint: disable=pointless-statement
        def test_function(x, y):
            x
            y

        # pylint: enable=pointless-statement
        self.assert_node_equal(
            function_parser.parse(test_function)[0],
            libcst.SimpleStatementLine(body=[libcst.Expr(libcst.Name("x"))]),
        )

    def test_parse_unused_args(self) -> None:
        # pylint: disable=pointless-statement,unused-argument
        def test_function(x):
            1

        # pylint: enable=pointless-statement,unused-argument
        with self.assertRaisesRegex(
            function_parser.UnusedArgument,
            r'Unused argument "x" in function test_function:\d+',
        ):
            function_parser.parse(test_function)
