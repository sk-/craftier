import libcst
import libcst.codemod
import libcst.matchers
from typing_extensions import Annotated

from craftier import codemod, transformer


# pylint: disable=pointless-statement,no-self-use
class ConstantMultiplicationTransformer(transformer.CraftierTransformer):
    def expression_before(
        self, x, constant: Annotated[int, libcst.matchers.Integer()]
    ):
        x * constant

    def expression_after(self, x, constant):
        constant * x


class TwoXAddTransformer(transformer.CraftierTransformer):
    def expression_before(self, x):
        x + x

    def expression_after(self, x):
        x * 2


class ReorderAddTransformer(transformer.CraftierTransformer):
    def expression_after(self, x, y):
        x + y

    def expression_before(self, x, y):
        y + x


# pylint: enable=pointless-statement,no-self-use


class CodemodTest(libcst.codemod.CodemodTest):
    TRANSFORM = codemod.BatchedCodemod

    def test_no_match(self) -> None:
        self.assertCodemod(
            "a - b",
            "a - b",
            transformers=[TwoXAddTransformer],
            expected_skip=True,
        )

    def test_match(self) -> None:
        self.assertCodemod("a + a", "a * 2", transformers=[TwoXAddTransformer])

    def test_multiple_executions(self) -> None:
        self.assertCodemod(
            "a + a",
            "2 * a",
            transformers=[
                ConstantMultiplicationTransformer,
                TwoXAddTransformer,
            ],
        )

    def test_multiple_executions_limit(self) -> None:
        self.assertCodemod(
            "a + b",
            "b + a",
            transformers=[ReorderAddTransformer],
            max_executions=1,
        )
        self.assertCodemod(
            "a + b",
            "a + b",
            transformers=[ReorderAddTransformer],
            max_executions=4,
        )
