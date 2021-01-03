import textwrap
import unittest
from typing import Set

import libcst
import libcst.matchers
import parameterized

import craftier.matcher


class NodeTest(unittest.TestCase):
    @parameterized.parameterized.expand(
        (
            ("same base", "314", "314"),
            ("hexadecimal", "314", "0x13a"),
            ("octal", "314", "0o472"),
            ("binary", "314", "0b100111010"),
            ("with separators", "314", "3_14"),
        )
    )
    def test_integer(
        self, _name: str, expression1: str, expression2: str
    ) -> None:
        matcher = craftier.matcher.from_node(
            libcst.parse_expression(expression1), {}
        )
        self.assertTrue(
            craftier.matcher.matches(
                libcst.parse_expression(expression2), matcher
            )
        )

    @parameterized.parameterized.expand(
        (
            ("same string", "'some string'", "'some string'"),
            ("different quotes", "'some string'", '"some string"'),
            ("raw", "'some string'", "r'some string'"),
            ("unicode", "'some string'", "u'some string'"),
            ("concatenated", "'some string'", "'some' ' ' 'string'"),
        )
    )
    def test_string(
        self, _name: str, expression1: str, expression2: str
    ) -> None:
        matcher = craftier.matcher.from_node(
            libcst.parse_expression(expression1), {}
        )
        self.assertTrue(
            craftier.matcher.matches(
                libcst.parse_expression(expression2), matcher
            )
        )

    @parameterized.parameterized.expand(
        (
            ("same string", "'some' 'string'", "'some' 'string'"),
            ("different quotes", "'some' 'string'", '"some" "string"'),
            ("raw", "'some' 'string'", "r'some' 'string'"),
            ("unicode", "'some' 'string'", "u'some' 'string'"),
            ("plain", "'some' 'string'", "'somestring'"),
            ("f string", "'some' 'string' f'{x}'", "f'somestring{x}'"),
            ("f string", "'some' 'string' f' {x}'", "f'somestring {x}'"),
        )
    )
    def test_concatenated_string(
        self, _name: str, expression1: str, expression2: str
    ) -> None:
        matcher = craftier.matcher.from_node(
            libcst.parse_expression(expression1), {}
        )
        self.assertTrue(
            craftier.matcher.matches(
                libcst.parse_expression(expression2), matcher
            )
        )

    @parameterized.parameterized.expand(
        (
            ("same string", "f'{x} and {y}'", "f'{x} and {y}'"),
            ("different quotes", "f'{x} and {y}'", 'f"{x} and {y}"'),
            ("raw", "f'{x} and {y}'", "fr'{x} and {y}'"),
            ("concatenated", "f'{x} and {y}'", "f'{x} ' 'and' f' {y}'"),
        )
    )
    def test_fstring(
        self, _name: str, expression1: str, expression2: str
    ) -> None:
        matcher = craftier.matcher.from_node(
            libcst.parse_expression(expression1), {}
        )
        self.assertTrue(
            craftier.matcher.matches(
                libcst.parse_expression(expression2), matcher
            )
        )

    def test_fstring_with_placeholders(self) -> None:
        matcher = craftier.matcher.from_node(
            libcst.parse_expression("f'{x} and {y}'"),
            {"x": libcst.matchers.DoNotCare(), "y": libcst.matchers.Integer()},
        )
        self.assertTrue(
            craftier.matcher.matches(
                libcst.parse_expression("f'{a + b} and {32}'"), matcher
            )
        )
        self.assertFalse(
            craftier.matcher.matches(
                libcst.parse_expression("f'{a + b} and {z}'"), matcher
            )
        )

    @parameterized.parameterized.expand(
        (
            ("equal", "[1, 2, 3]", "[1, 2, 3]"),
            ("no spaces", "[1, 2, 3]", "[1,2,3]"),
            ("trailing comma", "[1, 2, 3]", "[1, 2, 3, ]"),
        )
    )
    def test_list(self, _name: str, expression1: str, expression2: str) -> None:
        matcher = craftier.matcher.from_node(
            libcst.parse_expression(expression1), {}
        )
        self.assertTrue(
            craftier.matcher.matches(
                libcst.parse_expression(expression2), matcher
            )
        )

    @parameterized.parameterized.expand(
        (
            ("equal", "{1, 2, 3}", "{1, 2, 3}"),
            ("no spaces", "{1, 2, 3}", "{1,2,3}"),
            ("trailing comma", "{1, 2, 3}", "{1, 2, 3, }"),
        )
    )
    def test_set(self, _name: str, expression1: str, expression2: str) -> None:
        matcher = craftier.matcher.from_node(
            libcst.parse_expression(expression1), {}
        )
        self.assertTrue(
            craftier.matcher.matches(
                libcst.parse_expression(expression2), matcher
            )
        )

    @parameterized.parameterized.expand(
        (
            ("equal", "{1: 2, 3: 4}", "{1: 2, 3: 4}"),
            ("no spaces", "{1: 2, 3: 4}", "{1:2,3:4}"),
            ("trailing comma", "{1: 2, 3: 4}", "{1: 2, 3: 4,}"),
        )
    )
    def test_dict(self, _name: str, expression1: str, expression2: str) -> None:
        matcher = craftier.matcher.from_node(
            libcst.parse_expression(expression1), {}
        )
        self.assertTrue(
            craftier.matcher.matches(
                libcst.parse_expression(expression2), matcher
            )
        )

    @parameterized.parameterized.expand(
        (
            ("equal", "(1, 2, 3)", "(1, 2, 3)"),
            ("no spaces", "(1, 2, 3)", "(1,2,3)"),
            ("no parens", "(1, 2, 3)", "1, 2, 3"),
            ("trailing comma", "(1, 2, 3)", "(1, 2, 3,)"),
            ("no parens", "(1, 2, 3)", "1, 2, 3"),
            ("no parens + trailing comma", "(1, 2, 3)", "1,2,3,"),
            ("one item + no parens + trailing comma", "(1,)", "1,"),
        )
    )
    def test_tuple(
        self, _name: str, expression1: str, expression2: str
    ) -> None:
        matcher = craftier.matcher.from_node(
            libcst.parse_expression(expression1), {}
        )
        self.assertTrue(
            craftier.matcher.matches(
                libcst.parse_expression(expression2), matcher
            )
        )

    @parameterized.parameterized.expand(
        (
            ("arithmetic", "x + y * z", "(x + (y * (z)))"),
            ("attributes", "x.y.z.w", "(((x).y).z).w"),
        )
    )
    def test_optional_parens(
        self, _name: str, expression1: str, expression2: str
    ) -> None:
        matcher = craftier.matcher.from_node(
            libcst.parse_expression(expression1), {}
        )
        self.assertTrue(
            craftier.matcher.matches(
                libcst.parse_expression(expression2), matcher
            )
        )

    def test_function(self) -> None:
        function_def = textwrap.dedent(
            """
            def test():
                name = "World"
                print(f"Hello {name}")
        """.strip()
        )
        matcher = craftier.matcher.from_node(
            libcst.parse_statement(function_def), {}
        )
        self.assertTrue(
            craftier.matcher.matches(
                libcst.parse_statement(function_def), matcher
            )
        )

    @parameterized.parameterized.expand(
        (
            ("literal", "x + y", "1 + y", {"x"}),
            ("string", "x + y", "'foo' + y", {"x"}),
            ("list", "x + y", "[1] + y", {"x"}),
            ("attribute", "x + y", "foo.bar + y", {"x"}),
            ("multiple placeholders", "x + y", "1 + 2", {"x", "y"}),
            ("function", "x(y)", "max([1, 2, 3])", {"x", "y"}),
            ("multiple repeated placeholders", "x + x", "1 + 1", {"x"}),
        )
    )
    def test_placeholders(
        self,
        _name: str,
        expression1: str,
        expression2: str,
        placeholders: Set[str],
    ) -> None:
        matcher = craftier.matcher.from_node(
            libcst.parse_expression(expression1),
            {p: libcst.matchers.DoNotCare() for p in placeholders},
        )
        self.assertTrue(
            craftier.matcher.matches(
                libcst.parse_expression(expression2), matcher
            )
        )
