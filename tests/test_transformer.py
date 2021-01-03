import unittest

import libcst
import libcst.codemod

from craftier import transformer

old_api, new_api = None, None


# pylint: disable=pointless-statement,no-self-use
class SimpleExpressionTransformer(transformer.CraftierTransformer):
    def expression_before(self):
        old_api

    def expression_after(self):
        new_api


# pylint: enable=pointless-statement,no-self-use


class PreserveCommentsTest(libcst.codemod.CodemodTest):
    TRANSFORM = SimpleExpressionTransformer

    def test_keep_comments_top_level(self) -> None:
        self.assertCodemod(
            "# comment 1\nold_api()\n# comment 2",
            "# comment 1\nnew_api()\n# comment 2",
        )

    def test_keep_comments_function(self) -> None:
        self.assertCodemod(
            "def foo():\n  # comment 1\n  old_api()\n  # comment 2",
            "def foo():\n  # comment 1\n  new_api()\n  # comment 2",
        )


class SimpleExpressionTransformerTest(libcst.codemod.CodemodTest):
    TRANSFORM = SimpleExpressionTransformer

    def test_no_match(self) -> None:
        self.assertCodemod("foo + bar", "foo + bar")

    def test_match(self) -> None:
        self.assertCodemod("foo + old_api", "foo + new_api")


# pylint: disable=pointless-statement,no-self-use
class ParameterizedExpressionTransformer(transformer.CraftierTransformer):
    def expression_before(self, x):
        x + 2

    def expression_after(self, x):
        x + 3


# pylint: enable=pointless-statement,no-self-use


class ParameterizedExpressionTransformerTest(libcst.codemod.CodemodTest):
    TRANSFORM = ParameterizedExpressionTransformer

    def test_no_match(self) -> None:
        self.assertCodemod("length + 1", "length + 1")

    def test_match(self) -> None:
        self.assertCodemod("foo(bar + 2)", "foo(bar + 3)")


# pylint: disable=pointless-statement,no-self-use
class RepeatedParameterExpressionTransformer(transformer.CraftierTransformer):
    def expression_before(self, x):
        x + x

    def expression_after(self, x):
        2 * x


# pylint: enable=pointless-statement,no-self-use


class RepeatedParameterExpressionTransformerTest(libcst.codemod.CodemodTest):
    TRANSFORM = RepeatedParameterExpressionTransformer

    def test_no_match(self) -> None:
        self.assertCodemod("a + b", "a + b")

    def test_match(self) -> None:
        self.assertCodemod("a + a", "2 * a")


# pylint: disable=pointless-statement,no-self-use
class MultipleParametersExpressionTransformer(transformer.CraftierTransformer):
    def expression_before(self, x, y):
        x + y

    def expression_after(self, x, y):
        y / x


# pylint: enable=pointless-statement,no-self-use


class MultipleParametersExpressionTransformerTest(libcst.codemod.CodemodTest):
    TRANSFORM = MultipleParametersExpressionTransformer

    def test_no_match(self) -> None:
        self.assertCodemod("a - b", "a - b")

    def test_match(self) -> None:
        self.assertCodemod("a + b", "b / a")


# pylint: disable=pointless-statement,no-self-use,unused-argument
class UnusedArgExpressionTransformer(transformer.CraftierTransformer):
    def expression_before(self, x):
        2

    def expression_after(self):
        3


# pylint: enable=pointless-statement,no-self-use,unused-argument


class UnusedArgExpressionTransformerTest(unittest.TestCase):
    def test_raises_exception(self) -> None:
        with self.assertRaisesRegex(
            Exception, 'Unused argument "x" in function expression_before'
        ):
            UnusedArgExpressionTransformer(libcst.codemod.CodemodContext())


# pylint: disable=pointless-statement,no-self-use
class MissingAfterExpressionTransformer(transformer.CraftierTransformer):
    def expression_before(self):
        2


# pylint: enable=pointless-statement,no-self-use


class MissingAfterExpressionTransformerTest(unittest.TestCase):
    def test_raises_exception(self) -> None:
        with self.assertRaisesRegex(
            Exception,
            "Expected `expression_before` and `expression_after` to be defined",
        ):
            MissingAfterExpressionTransformer(libcst.codemod.CodemodContext())


# pylint: disable=pointless-statement,no-self-use
class MissingBeforeExpressionTransformer(transformer.CraftierTransformer):
    def expression_after(self):
        2


# pylint: enable=pointless-statement,no-self-use


class MissingBeforeExpressionTransformerTest(unittest.TestCase):
    def test_raises_exception(self) -> None:
        with self.assertRaisesRegex(
            Exception,
            "Expected `expression_before` and `expression_after` to be defined",
        ):
            MissingBeforeExpressionTransformer(libcst.codemod.CodemodContext())


# pylint: disable=pointless-statement,no-self-use
class AnyMatcherTopLevelTransformer(transformer.CraftierTransformer):
    def expression_before(self, x):
        x

    def expression_after(self):
        "should fail"


# pylint: enable=pointless-statement,no-self-use


class AnyMatcherTopLevelTransformerTest(libcst.codemod.CodemodTest):
    def test_raises_exception(self) -> None:
        with self.assertRaisesRegex(
            Exception,
            "DoNotCare matcher is forbidden at top level",
        ):
            AnyMatcherTopLevelTransformer(libcst.codemod.CodemodContext())


# pylint: disable=pointless-statement,no-self-use
class MultipleMatchersTransformer(transformer.CraftierTransformer):
    def expression1_before(self, x):
        x

    def expression1_after(self):
        "should fail"

    def expression2_before(self, x):
        x

    def expression2_after(self):
        "should fail"


# pylint: enable=pointless-statement,no-self-use


class MultipleMatcheresTransformerTest(libcst.codemod.CodemodTest):
    def test_raises_exception(self) -> None:
        with self.assertRaisesRegex(
            Exception,
            "Only 1 method is supported at the moment. Found: .*",
        ):
            MultipleMatchersTransformer(libcst.codemod.CodemodContext())
