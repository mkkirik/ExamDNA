"""Minimal SI unit algebra for dimension checks.

Parses unit strings such as ``m/s^2``, ``kg m s^-2``, ``N·m``, ``km/h``,
``kJ`` into (scale, dimension-vector). Dimensions: M, L, T, I, Θ, N.
Unknown symbols raise ``UnitError`` so the caller can report "not verified"
rather than guessing.
"""

from __future__ import annotations

import re
from typing import Dict, Tuple

DIMS = ("M", "L", "T", "I", "K", "N")


def _d(**kw) -> Tuple[int, ...]:
    return tuple(kw.get(k, 0) for k in DIMS)


BASE: Dict[str, Tuple[float, Tuple[int, ...]]] = {
    "1": (1.0, _d()),
    "kg": (1.0, _d(M=1)),
    "g": (1e-3, _d(M=1)),
    "t": (1e3, _d(M=1)),
    "m": (1.0, _d(L=1)),
    "s": (1.0, _d(T=1)),
    "min": (60.0, _d(T=1)),
    "h": (3600.0, _d(T=1)),
    "A": (1.0, _d(I=1)),
    "K": (1.0, _d(K=1)),
    "mol": (1.0, _d(N=1)),
    "N": (1.0, _d(M=1, L=1, T=-2)),
    "J": (1.0, _d(M=1, L=2, T=-2)),
    "eV": (1.602176634e-19, _d(M=1, L=2, T=-2)),
    "W": (1.0, _d(M=1, L=2, T=-3)),
    "Pa": (1.0, _d(M=1, L=-1, T=-2)),
    "Hz": (1.0, _d(T=-1)),
    "C": (1.0, _d(T=1, I=1)),
    "V": (1.0, _d(M=1, L=2, T=-3, I=-1)),
    "ohm": (1.0, _d(M=1, L=2, T=-3, I=-2)),
    "Ω": (1.0, _d(M=1, L=2, T=-3, I=-2)),
    "F": (1.0, _d(M=-1, L=-2, T=4, I=2)),
    "T": (1.0, _d(M=1, T=-2, I=-1)),
    "L": (1e-3, _d(L=3)),
    "rad": (1.0, _d()),
    "deg": (0.017453292519943295, _d()),
    "°": (0.017453292519943295, _d()),
    "%": (0.01, _d()),
}
PREFIXES = {"G": 1e9, "M": 1e6, "k": 1e3, "c": 1e-2, "m": 1e-3, "u": 1e-6, "µ": 1e-6, "μ": 1e-6, "n": 1e-9}
_TOKEN = re.compile(r"([A-Za-zµμΩ°%]+)(?:\^?(-?\d+))?")


class UnitError(ValueError):
    pass


def _symbol(sym: str) -> Tuple[float, Tuple[int, ...]]:
    if sym in BASE:
        return BASE[sym]
    if len(sym) > 1 and sym[0] in PREFIXES and sym[1:] in BASE and sym[1:] not in ("1", "%", "°"):
        scale, dims = BASE[sym[1:]]
        return PREFIXES[sym[0]] * scale, dims
    raise UnitError(f"unknown unit symbol '{sym}'")


def parse_unit(text: str) -> Tuple[float, Tuple[int, ...]]:
    if text is None:
        raise UnitError("no unit")
    s = text.strip().replace("**", "^").replace("·", " ").replace("*", " ").replace("²", "^2").replace("³", "^3")
    if s in ("", "1", "-", "dimensionless", "none"):
        return 1.0, _d()
    scale = 1.0
    dims = [0] * len(DIMS)
    sign = 1
    pos = 0
    for chunk in re.split(r"(/)", s):
        if chunk == "/":
            sign = -1
            continue
        for tok in chunk.split():
            m = _TOKEN.fullmatch(tok)
            if not m:
                raise UnitError(f"cannot parse unit token '{tok}'")
            sym, exp = m.group(1), int(m.group(2) or 1)
            sc, dv = _symbol(sym)
            power = exp * sign
            scale *= sc ** power
            for i in range(len(DIMS)):
                dims[i] += dv[i] * power
            pos += 1
    if pos == 0:
        raise UnitError(f"empty unit '{text}'")
    return scale, tuple(dims)


_DIMLESS_FUNCS = {"sin", "cos", "tan", "asin", "acos", "atan", "exp", "log", "log10", "ln", "radians", "degrees"}


def expression_dimensions(expression: str, var_units: Dict[str, str]) -> Tuple[int, ...]:
    """Dimensional analysis of an arithmetic expression.

    Raises ``UnitError`` on inconsistent dimensions (e.g. adding m to s) or
    when a variable's unit is unknown.
    """
    import ast

    expr = expression.replace("^", "**").replace("×", "*").replace("÷", "/").replace("−", "-")
    tree = ast.parse(expr, mode="eval")
    zero = _d()

    def numeric_value(node):
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return float(node.value)
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
            v = numeric_value(node.operand)
            return None if v is None else -v
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div):
            a, b = numeric_value(node.left), numeric_value(node.right)
            return None if a is None or b in (None, 0) else a / b
        return None

    def walk(node) -> Tuple[int, ...]:
        if isinstance(node, ast.Expression):
            return walk(node.body)
        if isinstance(node, ast.Constant):
            return zero
        if isinstance(node, ast.Name):
            if node.id == "pi":
                return zero
            if node.id not in var_units or var_units[node.id] is None:
                raise UnitError(f"unit of '{node.id}' is unknown")
            return parse_unit(var_units[node.id])[1]
        if isinstance(node, ast.UnaryOp):
            return walk(node.operand)
        if isinstance(node, ast.BinOp):
            left = walk(node.left)
            if isinstance(node.op, ast.Pow):
                exp = numeric_value(node.right)
                if exp is None:
                    if left != zero:
                        raise UnitError("non-numeric exponent on a dimensional quantity")
                    return zero
                dims = [d * exp for d in left]
                if any(abs(d - round(d)) > 1e-9 for d in dims):
                    raise UnitError("fractional dimension")
                return tuple(int(round(d)) for d in dims)
            right = walk(node.right)
            if isinstance(node.op, (ast.Add, ast.Sub, ast.Mod)):
                if left != right:
                    raise UnitError("adding or subtracting quantities with different dimensions")
                return left
            if isinstance(node.op, ast.Mult):
                return tuple(a + b for a, b in zip(left, right))
            if isinstance(node.op, ast.Div):
                return tuple(a - b for a, b in zip(left, right))
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            name = node.func.id
            args = [walk(a) for a in node.args]
            if name == "sqrt":
                if any(d % 2 for d in args[0]):
                    raise UnitError("square root of a quantity with odd dimension")
                return tuple(d // 2 for d in args[0])
            if name in _DIMLESS_FUNCS:
                if any(a != zero for a in args):
                    raise UnitError(f"{name}() of a dimensional quantity")
                return zero
            if name in ("abs",):
                return args[0]
            if name in ("min", "max", "atan2"):
                if len(set(args)) > 1:
                    raise UnitError(f"{name}() of mixed dimensions")
                return zero if name == "atan2" else args[0]
        raise UnitError(f"cannot analyse dimensions of {type(node).__name__}")

    return walk(tree)


def compatible(a: str, b: str) -> bool:
    return parse_unit(a)[1] == parse_unit(b)[1]


def convert(value: float, from_unit: str, to_unit: str) -> float:
    fs, fd = parse_unit(from_unit)
    ts, td = parse_unit(to_unit)
    if fd != td:
        raise UnitError(f"incompatible units {from_unit} and {to_unit}")
    return value * fs / ts
