from typing import TypeVar

import libcst


def _precedence(node: libcst.CSTNode) -> int:
    """
    Return the precedence of a given expression.

    Nodes which are not expression have the maximum precedence.

    See https://docs.python.org/3/reference/expressions.html for details.
    """
    if isinstance(node, libcst.BinaryOperation):
        binary_operation_precedence = {
            libcst.BitOr: 8,
            libcst.BitXor: 9,
            libcst.BitAnd: 10,
            libcst.LeftShift: 11,
            libcst.RightShift: 11,
            libcst.Add: 12,
            libcst.Subtract: 12,
            libcst.Multiply: 13,
            libcst.MatrixMultiply: 13,
            libcst.Divide: 13,
            libcst.FloorDivide: 13,
            libcst.Modulo: 13,
            libcst.Power: 15,
        }
        return binary_operation_precedence[type(node.operator)]

    if isinstance(node, libcst.BooleanOperation):
        boolean_operation_precedence = {
            libcst.Or: 4,
            libcst.And: 5,
        }
        return boolean_operation_precedence[type(node.operator)]

    if isinstance(node, libcst.UnaryOperation):
        unary_operation_precedence = {
            libcst.Not: 6,
            libcst.BitInvert: 14,
            libcst.Minus: 14,
            libcst.Plus: 14,
        }
        return unary_operation_precedence[type(node.operator)]

    precedence = {
        libcst.NamedExpr: 1,
        libcst.Lambda: 2,
        libcst.IfExp: 3,
        libcst.Comparison: 7,
        libcst.Await: 16,
        libcst.Subscript: 17,
        libcst.Call: 17,
        libcst.Attribute: 17,
        libcst.Tuple: 18,
        libcst.List: 18,
        libcst.ListComp: 18,
        libcst.Dict: 18,
        libcst.DictComp: 18,
        libcst.Set: 18,
        libcst.SetComp: 18,
        libcst.GeneratorExp: 100,
    }
    return precedence.get(type(node), 100)


def _needs_parentheses_parent(
    node: libcst.CSTNode, parent: libcst.CSTNode
) -> bool:
    # The node does not support parenthesis, there's nothing to do
    if not hasattr(node, "lpar"):
        return False

    # The node is already parenthesized, there's nothing to do
    if getattr(node, "lpar"):
        return False

    # A generator expression requires parenthesis, except when it is the sole
    # argument of a function call.
    if isinstance(node, libcst.GeneratorExp):
        if isinstance(parent, libcst.BaseExpression):
            if isinstance(parent, libcst.Call) and len(parent.args) <= 1:
                return False
            return True
        return True

    # Any tuple within an expression requires parenthesis
    if isinstance(node, libcst.Tuple):
        return isinstance(parent, libcst.BaseExpression)

    return _precedence(node) < _precedence(parent)


def _needs_parentheses_previous(
    node: libcst.CSTNode, previous: libcst.CSTNode
) -> bool:
    # The node does not support parenthesis, there's nothing to do
    if not hasattr(node, "lpar"):
        return False

    # The node is already parenthesized, there's nothing to do
    if getattr(node, "lpar"):
        return False

    # The previous node had parentheses, keep them
    if getattr(previous, "lpar", None):
        return True

    # We don't have information from the parent
    if isinstance(node, libcst.GeneratorExp):
        return True

    # We don't have information from the parent
    if isinstance(node, libcst.Tuple):
        return True

    return _precedence(node) < _precedence(previous)


T = TypeVar("T", bound=libcst.CSTNode)


def parenthesize_using_parent(node: T, parent: libcst.CSTNode) -> T:
    """Add parentheses to the given node if needed.

    It will use the parent of the node to decide whether parentheses are
    required.
    """
    if _needs_parentheses_parent(node, parent):
        return node.with_changes(
            lpar=[libcst.LeftParen()], rpar=[libcst.RightParen()]
        )
    return node


def parenthesize_using_previous(node: T, previous: libcst.CSTNode) -> T:
    """Add parentheses to the given node if needed.

    It will use the previous node this node is replacing to decide whether
    parentheses are required.

    Note: this function is not as precise as `parenthesize_using_parent`
    """
    if _needs_parentheses_previous(node, previous):
        return node.with_changes(
            lpar=[libcst.LeftParen()], rpar=[libcst.RightParen()]
        )
    return node
