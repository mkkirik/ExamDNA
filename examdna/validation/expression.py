"""Safe arithmetic expression evaluation.

Expressions come from agent-written candidates and are untrusted. They are
parsed with ``ast`` and evaluated by walking a whitelist of node types —
``eval`` is never used. Only numbers, named variables, + − × ÷ ** %, unary
signs and a fixed set of math functions are allowed.

If an expression uses only rational operations on rational inputs, it is
evaluated exactly with ``fractions.Fraction``; otherwise with floats.
"""

from __future__ import annotations

import ast
import math
import operator
from fractions import Fraction
from typing import Dict, Tuple, Union

Number = Union[int, float, Fraction]
MAX_EXPRESSION_LENGTH = 500
MAX_EXPONENT = 64
MAX_MAGNITUDE = 1e300

FUNCTIONS = {
    "sqrt": math.sqrt,
    "sin": math.sin,
    "cos": math.cos,
    "tan": math.tan,
    "asin": math.asin,
    "acos": math.acos,
    "atan": math.atan,
    "atan2": math.atan2,
    "exp": math.exp,
    "log": math.log,
    "log10": math.log10,
    "ln": math.log,
    "abs": abs,
    "radians": math.radians,
    "degrees": math.degrees,
    "min": min,
    "max": max,
}
CONSTANTS = {"pi": math.pi}

_BINOPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}
_UNARY = {ast.UAdd: operator.pos, ast.USub: operator.neg}


class ExpressionError(ValueError):
    pass


class _Inexact(Exception):
    pass


def _to_fraction(v: Number) -> Fraction:
    if isinstance(v, Fraction):
        return v
    if isinstance(v, int):
        return Fraction(v)
    return Fraction(str(v))  # decimal literal → exact rational


def _eval(node: ast.AST, env: Dict[str, Number], exact: bool) -> Number:
    if isinstance(node, ast.Expression):
        return _eval(node.body, env, exact)
    if isinstance(node, ast.Constant):
        if isinstance(node.value, bool) or not isinstance(node.value, (int, float)):
            raise ExpressionError(f"unsupported literal {node.value!r}")
        return _to_fraction(node.value) if exact else float(node.value)
    if isinstance(node, ast.Name):
        if node.id in env:
            return _to_fraction(env[node.id]) if exact else float(env[node.id])
        if node.id in CONSTANTS:
            if exact:
                raise _Inexact()
            return CONSTANTS[node.id]
        raise ExpressionError(f"unknown variable '{node.id}'")
    if isinstance(node, ast.UnaryOp) and type(node.op) in _UNARY:
        return _UNARY[type(node.op)](_eval(node.operand, env, exact))
    if isinstance(node, ast.BinOp) and type(node.op) in _BINOPS:
        left = _eval(node.left, env, exact)
        right = _eval(node.right, env, exact)
        if isinstance(node.op, ast.Pow):
            if abs(right) > MAX_EXPONENT:
                raise ExpressionError("exponent too large")
            if exact and (not isinstance(right, Fraction) or right.denominator != 1):
                raise _Inexact()
            if exact and right < 0 and left == 0:
                raise ExpressionError("zero raised to a negative power")
        if isinstance(node.op, (ast.Div, ast.Mod)) and right == 0:
            raise ExpressionError("division by zero")
        try:
            result = _BINOPS[type(node.op)](left, right)
        except (OverflowError, ValueError, ZeroDivisionError) as exc:
            raise ExpressionError(str(exc)) from exc
        if isinstance(result, complex):
            raise ExpressionError("complex result")
        if not exact and abs(result) > MAX_MAGNITUDE:
            raise ExpressionError("result too large")
        return result
    if isinstance(node, ast.Call):
        if exact:
            raise _Inexact()
        if not isinstance(node.func, ast.Name) or node.func.id not in FUNCTIONS:
            raise ExpressionError("only whitelisted math functions may be called")
        if node.keywords:
            raise ExpressionError("keyword arguments are not allowed")
        args = [float(_eval(a, env, False)) for a in node.args]
        try:
            return float(FUNCTIONS[node.func.id](*args))
        except (ValueError, OverflowError, TypeError) as exc:
            raise ExpressionError(f"{node.func.id}: {exc}") from exc
    raise ExpressionError(f"unsupported syntax: {type(node).__name__}")


def evaluate(expression: str, variables: Dict[str, Number]) -> Tuple[float, bool]:
    """Evaluate ``expression``. Returns ``(value, exact)``."""
    if not isinstance(expression, str) or not expression.strip():
        raise ExpressionError("empty expression")
    if len(expression) > MAX_EXPRESSION_LENGTH:
        raise ExpressionError("expression too long")
    expr = expression.replace("^", "**").replace("×", "*").replace("÷", "/").replace("−", "-")
    try:
        tree = ast.parse(expr, mode="eval")
    except SyntaxError as exc:
        raise ExpressionError(f"syntax error: {exc.msg}") from exc
    for var, val in variables.items():
        if isinstance(val, bool) or not isinstance(val, (int, float)) or (isinstance(val, float) and not math.isfinite(val)):
            raise ExpressionError(f"variable {var} must be a finite number")
    try:
        value = _eval(tree, variables, exact=True)
        return float(value), True
    except _Inexact:
        value = _eval(tree, variables, exact=False)
        return float(value), False


def names_in(expression: str) -> set:
    expr = expression.replace("^", "**")
    try:
        tree = ast.parse(expr, mode="eval")
    except SyntaxError:
        return set()
    called = {n.func.id for n in ast.walk(tree) if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)}
    return {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)} - called - set(CONSTANTS)
