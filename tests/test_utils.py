import textwrap
import unittest

import libcst

from craftier import utils


class UtilsTest(unittest.TestCase):
    def test_to_string(self) -> None:
        self.maxDiff = None
        expected = textwrap.dedent(
            """
            SimpleStatementLine:
              body:
              - Return:
                value: BinaryOperation:
                  left: Name:
                    value: 'x'
                  operator: Add
                  right: Subscript:
                    value: Name:
                      value: 'a'
                    slice:
                    - SubscriptElement:
                      slice: Index:
                        value: Integer:
                          value: '1'
                    lbracket: LeftSquareBracket
                    rbracket: RightSquareBracket
            """
        ).strip()
        self.assertEqual(
            utils.to_string(libcst.parse_statement("return x + a[1]")).strip(),
            expected,
        )
